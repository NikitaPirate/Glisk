---
description: "Task list for Mint Event Detection System implementation"
---

# Tasks: Mint Event Detection System

**Feature**: 003-003b-event-detection
**Input**: Design documents from `/specs/003-003b-event-detection/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/
**Estimated Time**: 16 hours total

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions
- Backend: `backend/src/glisk/`, `backend/tests/`
- All work is in backend domain (no contracts or frontend changes)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and dependency setup

- [X] T001 Install web3.py dependency: `cd backend && uv add web3`
- [X] T002 [P] Add Alchemy configuration to `backend/src/glisk/core/config.py`:
  - `alchemy_api_key: str`
  - `alchemy_webhook_secret: str`
  - `glisk_nft_contract_address: str`
  - `network: str` (BASE_SEPOLIA or BASE_MAINNET)
  - `glisk_default_author_wallet: str`
- [X] T003 [P] Update `.env.example` to document new Alchemy environment variables

**Checkpoint**: ✅ Dependencies installed, configuration ready

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core security and blockchain utilities needed by ALL user stories

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Create directory structure: `backend/src/glisk/services/blockchain/` and `backend/src/glisk/api/routes/`
- [X] T005 Implement HMAC signature validation in `backend/src/glisk/services/blockchain/alchemy_signature.py`:
  - Function: `validate_alchemy_signature(raw_body: bytes, signature: str, signing_key: str) -> bool`
  - Use `hmac.compare_digest()` for constant-time comparison
  - Security-critical component (~20 lines)

**Checkpoint**: ✅ Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 3 - Secure Webhook Authentication (Priority: P1) 🔒 SECURITY

**Goal**: Cryptographically verify all incoming webhook requests using HMAC SHA256 to prevent unauthorized event injection

**Independent Test**: Send webhook requests with valid/invalid signatures and verify only properly signed requests are accepted

**Why P1**: Security-critical - must be implemented before any webhook processing logic

### Implementation for User Story 3

- [X] T006 [US3] Create `backend/tests/test_webhook_signature.py` with unit tests:
  - Test valid signature acceptance
  - Test invalid signature rejection
  - Test missing signature header rejection
  - Test constant-time comparison behavior
- [X] T007 [US3] Implement FastAPI dependency in `backend/src/glisk/api/dependencies.py`:
  - `validate_webhook_signature()` dependency that reads raw body and X-Alchemy-Signature header
  - Returns 401 Unauthorized on validation failure
  - Integrates with alchemy_signature.py module

**Checkpoint**: ✅ Signature validation fully tested and ready to use in webhook endpoint

---

## Phase 4: User Story 1 - Real-Time Mint Detection (Priority: P1) 🎯 MVP

**Goal**: Automatically detect NFT mint events in real-time via Alchemy webhooks and store them in the database

**Independent Test**: Mint a test NFT on Base Sepolia testnet, verify webhook receives event, confirm MintEvent and Token records appear in database with 'detected' status

**Why P1**: Foundational capability - without event detection, no downstream processing can occur

### Implementation for User Story 1

- [X] T008 [US1] Create `backend/src/glisk/api/routes/webhooks.py` with POST /webhooks/alchemy endpoint:
  - Accept Alchemy webhook payload (JSON)
  - Use signature validation dependency from US3
  - Parse BatchMinted event from `event.data.block.logs[]`
  - Filter by contract address and event signature
  - Extract: minter, promptAuthor, startTokenId, quantity, totalPaid, txHash, blockNumber, logIndex
  - Manual event decoding (no ABI required - ~75 lines inline parsing)
- [X] T009 [US1] Implement author lookup and event storage in webhooks.py:
  - Query `AuthorRepository.get_by_wallet(author_wallet)` to get author_id
  - If not found, use default author from config `GLISK_DEFAULT_AUTHOR_WALLET`
  - Create MintEvent record (tx_hash, log_index, block_number, token_id, author_wallet, recipient, detected_at)
  - Create Token record (token_id, minter_address, author_id, status='detected', mint_timestamp)
  - Use UnitOfWork pattern for atomic transaction
- [X] T010 [US1] Implement error handling and HTTP responses in webhooks.py:
  - Return 200 OK with mint_event_id and token_id on success
  - Return 409 Conflict on duplicate event (via exists() check before insert)
  - Return 400 Bad Request on malformed payload
  - Return 500 Internal Server Error on database failures (triggers Alchemy retry)
  - Log all events with structlog (webhook.received, event.stored, webhook.duplicate)
- [X] T011 [US1] Register webhook route in `backend/src/glisk/app.py`:
  - Import webhooks router
  - Include router with `/webhooks` prefix
- [ ] T012 [US1] Create `backend/tests/test_webhook_integration.py` with integration tests:
  - Test complete webhook flow (signature → parse → store) using testcontainers
  - Test duplicate event handling (409 Conflict)
  - Test author lookup (registered vs unregistered)
  - Test database transaction rollback on errors
  - Test filtering by contract address and transaction status
  - Test filtering events from non-GliskNFT contracts (should ignore and return 200 OK with no storage)

**Checkpoint**: ✅ Real-time mint detection implemented - webhook endpoint can receive events, validate signatures, and store MintEvent + Token records (integration tests pending)

---

## Phase 5: User Story 2 - Event Recovery for Missed Events (Priority: P2)

**Goal**: Administrators can manually trigger event recovery to fetch and store any missed mint events from blockchain history via eth_getLogs

**Independent Test**: Start server at block X, mint NFTs, run recovery CLI from block X-10 to verify historical events are fetched and stored

**Why P2**: Resilience feature - handles edge cases (downtime, webhook failures) but not blocking for initial development

### Implementation for User Story 2

- [X] T013 [US2] Implement event recovery service in `backend/src/glisk/services/blockchain/event_recovery.py`:
  - Function: `fetch_mint_events(from_block: int, to_block: int | str, batch_size: int = 1000) -> list`
  - Initialize Web3 with Alchemy HTTP provider using `ALCHEMY_API_KEY`
  - Calculate BatchMinted event signature: `keccak256("BatchMinted(address,address,uint256,uint256,uint256)")`
  - Call `eth_getLogs` with contract address and event signature filters
  - Implement adaptive pagination (1000 blocks default, reduce on timeout, increase on empty results)
  - Return list of decoded event dictionaries (minter, author, token_id, tx_hash, block_number, log_index)
- [X] T014 [US2] Implement event storage logic in event_recovery.py:
  - Function: `store_recovered_events(events: list, uow: UnitOfWork) -> tuple[int, int]`
  - For each event: lookup author, create MintEvent + Token records
  - Handle UNIQUE constraint violations gracefully (skip duplicates)
  - Return tuple: (stored_count, skipped_count)
- [X] T015 [US2] Implement system state management in event_recovery.py:
  - Function: `update_last_processed_block(block_number: int, uow: UnitOfWork)`
  - Update `system_state` table: key='last_processed_block', value=str(block_number)
  - Function: `get_last_processed_block(uow: UnitOfWork) -> int | None`
  - Query `system_state` table for last processed block
- [X] T016 [US2] Create CLI command in `backend/src/glisk/cli/recover_events.py`:
  - Arguments: `--from-block` (optional), `--to-block` (optional, default='latest'), `--batch-size` (optional, default=1000), `--dry-run` (flag), `--verbose` (flag)
  - Load config from environment
  - Get starting block: use `--from-block` if provided, else load from `system_state`
  - Loop: fetch events in batches, store in database, update last_processed_block
  - Implement retry logic for rate limits (exponential backoff, 3 attempts)
  - Print progress: "Processing blocks X - Y (batch N/M)", "Found N events, stored M"
  - Support --dry-run mode (fetch and print events without database writes)
- [X] T017 [US2] Make CLI module executable by creating `backend/src/glisk/cli/__main__.py`:
  - Import and execute recover_events command
  - Enable `python -m glisk.cli.recover_events` syntax
- [X] T018 [US2] Create `backend/tests/test_event_recovery.py` with integration tests:
  - Test fetch_mint_events with mocked Web3 responses
  - Test recovery mechanism (eth_getLogs → storage → state update)
  - Test pagination and adaptive chunking
  - Test duplicate handling during recovery
  - Test --dry-run mode
  - Test last_processed_block persistence
  - Test CLI resume from last_processed_block after interruption (run CLI → stop → verify state saved → run again → verify resumes)

**Checkpoint**: ✅ Event recovery fully functional - CLI can fetch historical events, handle pagination, update system state

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T019 [P] Add structured logging for all webhook and recovery operations:
  - Use structlog (already configured in 003a)
  - Log levels: INFO for events, WARNING for duplicates, ERROR for failures
  - Include context: tx_hash, token_id, block_number, author_wallet
- [X] T020 [P] Create quickstart validation script in `backend/tests/test_quickstart.py`:
  - Verify all endpoints respond correctly
  - Test signature validation with sample payload
  - Verify database connectivity
  - Check configuration loading
- [X] T021 Code review and cleanup:
  - Review inline event parsing (ensure under 80 lines per constitution)
  - Verify all UTC timestamp enforcement (import glisk.core.timezone)
  - Check constant-time HMAC comparison implementation
  - Validate error messages are informative
- [X] T022 Documentation updates:
  - Add docstrings to all public functions
  - Document webhook payload structure in webhooks.py
  - Add CLI usage examples in recover_events.py
  - Update CLAUDE.md with feature completion status

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 3 - Webhook Auth (Phase 3)**: Depends on Foundational (signature validation module)
- **User Story 1 - Real-Time Detection (Phase 4)**: Depends on Foundational + US3 (needs signature validation)
- **User Story 2 - Event Recovery (Phase 5)**: Depends on Foundational (independent of US1/US3)
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **US3 (Webhook Auth)**: Independent - only needs signature validation module (T005)
- **US1 (Real-Time Detection)**: Depends on US3 completion (needs signature validation dependency)
- **US2 (Event Recovery)**: Independent of US1/US3 - can run in parallel with US1 after Foundational

### Within Each User Story

- US3: Tests → Signature validation → FastAPI dependency
- US1: Webhook endpoint → Author lookup → Error handling → Route registration → Integration tests
- US2: Recovery service → State management → CLI command → Integration tests

### Parallel Opportunities

- **Phase 1**: T002 and T003 can run in parallel (different files)
- **Phase 3**: T006 and T007 can run sequentially (tests first, then implementation)
- **Phase 4-5**: After Foundational + US3 complete, US1 and US2 can be developed in parallel by different developers
- **Phase 6**: T019, T020, T021, T022 can run in parallel (different concerns)

---

## Parallel Example: After Foundational Phase

```bash
# Developer A: User Story 3 (Webhook Auth)
Task: "Create test_webhook_signature.py with unit tests"
Task: "Implement validate_webhook_signature() dependency"

# Developer B: User Story 2 (Event Recovery) - can start in parallel
Task: "Implement event recovery service in event_recovery.py"
Task: "Implement CLI command in recover_events.py"

# After US3 completes, Developer A continues with US1:
Task: "Create POST /webhooks/alchemy endpoint"
Task: "Implement author lookup and event storage"
```

---

## Implementation Strategy

### MVP First (US3 + US1 Only) - 8 hours

1. Complete Phase 1: Setup (30 min)
2. Complete Phase 2: Foundational (1 hour)
3. Complete Phase 3: User Story 3 - Webhook Auth (2 hours)
4. Complete Phase 4: User Story 1 - Real-Time Detection (4 hours)
5. **STOP and VALIDATE**: Test webhook flow on Base Sepolia testnet
6. Deploy MVP with real-time detection only

### Full Feature (US3 + US1 + US2) - 16 hours

1. Complete MVP (8 hours)
2. Complete Phase 5: User Story 2 - Event Recovery (4 hours)
3. Complete Phase 6: Polish (2 hours)
4. **VALIDATE**: Test recovery CLI, verify quickstart guide
5. Deploy complete feature

### Incremental Delivery

1. Setup + Foundational → Foundation ready (1.5 hours)
2. Add US3 → Signature validation tested (2 hours)
3. Add US1 → Real-time detection working → **Deploy MVP!** (4 hours)
4. Add US2 → Recovery mechanism working → **Deploy complete feature** (4 hours)
5. Polish → Production-ready (2 hours)

---

## Success Criteria Mapping

**From spec.md**:

- **SC-001** (500ms latency): Achieved by T010 (optimized event parsing and storage)
- **SC-002** (100% duplicate handling): Achieved by T010 (409 Conflict on UNIQUE constraint)
- **SC-003** (100% signature rejection): Achieved by T006-T007 (signature validation)
- **SC-004** (1000 events in 2 min): Achieved by T013-T016 (adaptive pagination)
- **SC-005** (all tests pass): Achieved by T006, T012, T018, T020
- **SC-006** (zero false positives): Achieved by T008 (contract address filter)
- **SC-007** (no processing logic): Enforced by T021 (code review)
- **SC-008** (5-min quickstart): Validated by T020

---

## Notes

- Tests are included per constitution (integration-first approach with testcontainers)
- No schema changes needed - all tables exist from 003a
- Detection only - NO event processing logic (image generation, IPFS upload)
- Inline event parsing kept under 80 lines per constitution trigger
- Uses existing UoW pattern, repositories, and database models from 003a
- Security-critical: HMAC constant-time comparison (T005, T006)
- Idempotency via database UNIQUE constraint (simpler than application-level)
- Commit after each task or logical group for clean git history
