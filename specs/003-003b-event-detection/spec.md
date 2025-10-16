# Feature Specification: Mint Event Detection System

**Feature Branch**: `003-003b-event-detection`
**Created**: 2025-10-17
**Status**: Draft
**Input**: User description: "@.prompts read all files make 003b specification"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Real-Time Mint Detection (Priority: P1)

When users mint NFTs on the blockchain, the system automatically detects these mint events in real-time via Alchemy webhooks and stores them in the database for future processing.

**Why this priority**: This is the foundational capability for the entire event-driven architecture. Without event detection, no downstream processing (image generation, IPFS upload, reveal) can occur.

**Independent Test**: Can be fully tested by minting a test NFT on Base Sepolia testnet, verifying the webhook receives the event, and confirming a MintEvent and Token record appear in the database with 'detected' status. Delivers immediate value by proving the detection pipeline works.

**Acceptance Scenarios**:

1. **Given** a valid mint transaction occurs on-chain, **When** Alchemy sends a webhook notification with valid signature, **Then** system creates MintEvent and Token records in database
2. **Given** an existing event already stored, **When** Alchemy retries sending the same event, **Then** system returns 409 Conflict without creating duplicate records
3. **Given** a webhook request with invalid signature, **When** signature validation runs, **Then** system rejects with 401 Unauthorized
4. **Given** a mint from a registered author wallet, **When** event is processed, **Then** Token record links to correct author
5. **Given** a mint from an unregistered wallet, **When** event is processed, **Then** Token record uses default author as fallback

---

### User Story 2 - Event Recovery for Missed Events (Priority: P2)

System administrators can manually trigger event recovery to fetch and store any missed mint events from blockchain history via eth_getLogs.

**Why this priority**: While real-time detection handles 99% of cases, recovery provides resilience against webhook failures, server downtime, or network issues. Essential for production reliability but not blocking for initial development.

**Independent Test**: Can be fully tested by starting the server at block X, minting NFTs, then running recovery CLI from block X-10 to verify historical events are fetched and stored. Delivers value by ensuring zero data loss even during outages.

**Acceptance Scenarios**:

1. **Given** events occurred during server downtime, **When** administrator runs recovery CLI with start block, **Then** system fetches all missed events via eth_getLogs
2. **Given** recovery CLI processing historical blocks, **When** batch completes, **Then** system updates last_processed_block in system_state table
3. **Given** recovery finds events already in database, **When** attempting to store, **Then** system handles duplicates gracefully via UNIQUE constraint
4. **Given** large block range with many events, **When** recovery runs, **Then** system paginates requests to avoid RPC timeouts

---

### User Story 3 - Secure Webhook Authentication (Priority: P1)

All incoming webhook requests must be cryptographically verified using HMAC SHA256 to prevent unauthorized event injection.

**Why this priority**: Security-critical. Without signature validation, attackers could inject fake mint events, corrupting the system state and potentially triggering unauthorized token reveals or image generation.

**Independent Test**: Can be fully tested by sending webhook requests with valid/invalid signatures and verifying only properly signed requests are accepted. Delivers immediate value by protecting against malicious actors from day one.

**Acceptance Scenarios**:

1. **Given** a webhook request with valid HMAC signature, **When** signature validation runs, **Then** system accepts request and proceeds to event processing
2. **Given** a webhook request with invalid signature, **When** signature validation runs, **Then** system immediately rejects with 401 Unauthorized before any processing
3. **Given** a webhook request with missing signature header, **When** validation runs, **Then** system rejects with 401 Unauthorized
4. **Given** signature validation implementation, **When** tested, **Then** uses constant-time comparison to prevent timing attacks

---

### Edge Cases

- What happens when Alchemy sends a webhook for a contract other than GliskNFT? (Filter by contract address)
- How does system handle malformed JSON payloads? (Return 400 Bad Request with validation error)
- What if author lookup fails due to database connection issues? (Transaction rolls back, Alchemy retries webhook)
- How does recovery handle eth_getLogs pagination when block range is too large? (Batch requests in 1000-block chunks)
- What happens if last_processed_block is not initialized? (CLI provides --from-block argument override)
- How does system handle webhook timeout scenarios? (Return 200 OK if processing completes <3s. If longer, return 500 Internal Server Error to trigger Alchemy retry. No async processing in this phase.)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide POST /webhooks/alchemy endpoint accepting Alchemy webhook notifications
- **FR-002**: System MUST validate all webhook requests using HMAC SHA256 signature verification against X-Alchemy-Signature header
- **FR-003**: System MUST parse MintBatch event logs from webhook payload and extract token_id, recipient, author_wallet, tx_hash, block_number, log_index
- **FR-004**: System MUST create MintEvent record for each mint event with fields: tx_hash, log_index, block_number, token_id, author_wallet, recipient, detected_at
- **FR-005**: System MUST create corresponding Token record with fields: token_id, current_owner, author_id (via lookup), status='detected', minted_at, tx_hash
- **FR-006**: System MUST enforce idempotency via UNIQUE constraint on mint_events(tx_hash, log_index) to prevent duplicate event processing
- **FR-007**: System MUST return 409 Conflict status when duplicate event is received (already stored)
- **FR-008**: System MUST look up author_id from authors table using author_wallet from event
- **FR-009**: System MUST use configured default author when author_wallet is not found in authors table
- **FR-010**: System MUST store MintEvent and Token records atomically within single database transaction using UoW pattern
- **FR-011**: System MUST provide CLI command for manual event recovery: `python -m glisk.cli.recover_events --from-block X`
- **FR-012**: Recovery mechanism MUST fetch missed events using eth_getLogs via Web3 provider (Alchemy RPC)
- **FR-013**: Recovery mechanism MUST update last_processed_block in system_state table after successful batch processing
- **FR-014**: Recovery mechanism MUST paginate requests in batches to prevent RPC timeouts
- **FR-015**: System MUST load configuration from environment: ALCHEMY_API_KEY, ALCHEMY_WEBHOOK_SECRET, GLISK_NFT_CONTRACT_ADDRESS, NETWORK, GLISK_DEFAULT_AUTHOR_WALLET
- **FR-016**: System MUST filter events by configured contract address to ignore events from other contracts
- **FR-017**: System MUST return 401 Unauthorized for requests with invalid or missing signature
- **FR-018**: System MUST return 400 Bad Request for malformed payloads
- **FR-019**: System MUST return 200 OK for successfully processed events
- **FR-020**: System MUST NOT implement event processing logic (image generation, IPFS upload) - detection only

### Key Entities

- **MintEvent**: Represents a detected NFT mint event from blockchain. Attributes: tx_hash, log_index, block_number, token_id, author_wallet, recipient, detected_at. Provides audit trail and deduplication.
- **Token**: Represents an NFT token in the system. Attributes: token_id (PK), current_owner, author_id (FK to authors), status (enum), minted_at, tx_hash. Status='detected' after webhook/recovery, transitions to other states in future features.
- **SystemState**: Stores operational state. Attributes: key='last_processed_block', value=block_number. Used by recovery mechanism to resume from correct block.
- **Author**: Pre-existing entity representing NFT creators. Lookup via wallet address provides link between on-chain and off-chain author identity.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: System successfully processes valid Alchemy webhook requests within 500ms (excluding network latency)
- **SC-002**: 100% of duplicate event requests return 409 Conflict without database errors
- **SC-003**: 100% of requests with invalid signatures are rejected with 401 Unauthorized
- **SC-004**: Recovery CLI can fetch and store 1000 events from historical blocks within 2 minutes
- **SC-005**: All integration tests pass, including signature validation, event storage, duplicate handling, and recovery mechanism
- **SC-006**: Zero false positives in production - only legitimate mint events from configured contract address are stored
- **SC-007**: Zero event processing logic exists in codebase (scope adherence - detection only)
- **SC-008**: Developer can test complete webhook flow on testnet within 5 minutes using Alchemy dashboard and ngrok

## Assumptions *(if any)*

- Alchemy webhook payload structure is stable and documented (using current Alchemy v2 webhook format)
- Database foundation from 003a (mint_events, tokens_s0, authors, system_state tables) is complete and production-ready
- FastAPI application skeleton with UoW pattern is functional (from 003a)
- Testcontainers infrastructure for integration testing is configured
- Python 3.14 runtime with async/await support is available
- PostgreSQL 14+ with UNIQUE constraint support is database backend
- Base Sepolia testnet is available for testing before mainnet deployment
- Alchemy provides reliable webhook retry mechanism (no need for webhook tracking table)
- Single Alchemy RPC provider is sufficient initially (no multi-provider abstraction needed)
- Default author fallback is acceptable temporary solution for unregistered creators

## Out of Scope *(if any)*

- **Event processing workers**: Background jobs to process detected events (comes in 003c - Image Generation)
- **Image generation pipeline**: AI image generation from token metadata (003c)
- **IPFS upload mechanism**: Storing generated images and metadata on IPFS (003d)
- **Token reveal mechanism**: Updating token metadata after image upload (003d)
- **Admin API**: Administrative endpoints for managing events, authors, tokens (003e)
- **Generic event parser abstraction**: Inline parsing sufficient for single contract (defer until webhook > 80 lines)
- **Web3 client abstraction**: Direct web3.py usage sufficient (defer until multiple RPC providers needed)
- **Webhook retry tracking table**: Alchemy handles retries natively (defer unless reliability issues arise)
- **Event processing queue**: Direct storage sufficient for MVP volumes (defer until throughput issues)
- **Multi-contract support**: Only GliskNFT contract events detected (defer until additional contracts needed)
- **Event notification system**: No push notifications or webhooks for downstream consumers (defer based on need)

## Dependencies *(if any)*

- **003a Backend Foundation (COMPLETE)**: Database tables (mint_events, tokens_s0, authors, system_state), repositories, UoW pattern, FastAPI skeleton, test infrastructure
- **web3.py**: Required for eth_getLogs via Alchemy RPC and event parsing (add to dependencies)
- **Python hmac library**: Standard library module for HMAC SHA256 signature validation (already available)
- **Alchemy webhook configuration**: Requires Alchemy dashboard setup to point webhook to deployed endpoint
- **ngrok or public endpoint**: Required for local development testing with Alchemy webhooks

## Notes *(if any)*

### Architectural Decisions from DDD Debate

**Separated Components**:
- Signature validation extracted to `services/blockchain/alchemy_signature.py` - Security-critical, unit testable, reusable (DDD Architect win)
- Event recovery in `services/blockchain/event_recovery.py` - Different execution context from webhooks (Both agreed)

**Inline Components**:
- Event parsing kept inline in `api/routes/webhooks.py` - Only 25 lines, tightly coupled to payload (Indie Hacker win)
- Storage logic kept inline - Uses UoW transaction context specific to webhook flow (Indie Hacker win)

**Deferred with Triggers**:
- Event parser class → Trigger: webhook route exceeds 80 lines
- Web3 client abstraction → Trigger: need multiple RPC providers
- Webhook tracking table → Trigger: Alchemy reliability issues observed
- Processing queue → Trigger: direct storage throughput insufficient

### Implementation Phases (16 hours total)

**Phase 1 (4h)**: Signature validation + webhook skeleton
**Phase 2 (4h)**: Event parsing + storage (MintEvent + Token)
**Phase 3 (4h)**: Event recovery mechanism (eth_getLogs)
**Phase 4 (4h)**: Integration tests + documentation

### Testing Strategy

**Integration-first** per project constitution:
- Use testcontainers for all tests (real PostgreSQL)
- Test complete webhook flow (signature → parsing → storage)
- Test recovery mechanism (eth_getLogs → storage → state update)

**Skip testing**:
- Simple CRUD (AuthorRepository.get_by_wallet tested in 003a)
- web3.py internals (battle-tested library)
- FastAPI routing basics (framework responsibility)

### Configuration Additions

Add to `core/config.py`:
```python
alchemy_api_key: str
alchemy_webhook_secret: str
glisk_nft_contract_address: str
network: str  # BASE_MAINNET or BASE_SEPOLIA
glisk_default_author_wallet: str
```

### Files to Create (~400 LOC total)

**New files**:
- `backend/src/glisk/api/routes/webhooks.py` (120 lines)
- `backend/src/glisk/services/blockchain/alchemy_signature.py` (20 lines)
- `backend/src/glisk/services/blockchain/event_recovery.py` (80 lines)
- `backend/src/glisk/cli/recover_events.py` (30 lines)
- `backend/tests/test_webhook_signature.py`
- `backend/tests/test_webhook_integration.py`
- `backend/tests/test_event_recovery.py`

**Modified files**:
- `backend/src/glisk/core/config.py` (add Alchemy settings)
- `backend/.env.example` (document new environment variables)

### Philosophy

**Detection only** - Events are stored, NOT processed. Processing (image generation, IPFS upload) comes in 003c-003e. This maintains clean separation of concerns and enables independent testing/deployment of detection pipeline.
