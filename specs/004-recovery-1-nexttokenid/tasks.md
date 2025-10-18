# Tasks: Simplified Token Recovery via nextTokenId

**Feature Branch**: `004-recovery-1-nexttokenid`
**Input**: Design documents from `/specs/004-recovery-1-nexttokenid/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/internal-service-contracts.md

**Tests**: This feature does NOT explicitly request TDD approach. Test tasks are included for verification but are not required to be written first.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions
- **Contracts**: `contracts/src/GliskNFT.sol`
- **Backend**: `backend/src/glisk/`, `backend/tests/`, `backend/alembic/versions/`
- **Documentation**: `CLAUDE.md`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify prerequisites and prepare for implementation

- [x] T001 Verify all existing tests pass before starting: `cd backend && TZ=America/Los_Angeles uv run pytest tests/ -v`
- [x] T002 Verify smart contract deployed to testnet and CONTRACT_ADDRESS in backend/.env
- [x] T003 Verify GLISK_DEFAULT_AUTHOR_WALLET exists in authors table

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add smart contract interface that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 [Foundational] Add nextTokenId() public getter to contracts/src/GliskNFT.sol (after line 200, in Token ID Query section)
- [x] T005 [Foundational] Redeploy smart contract to Base Sepolia testnet: `cd contracts && forge build && forge script script/Deploy.s.sol:DeployScript --rpc-url base-sepolia --broadcast`
- [x] T006 [Foundational] Update GLISK_NFT_CONTRACT_ADDRESS in backend/.env with newly deployed contract address
- [x] T007 [Foundational] Verify contract deployment and nextTokenId() function via Basescan or cast: `cast call $CONTRACT_ADDRESS "nextTokenId()(uint256)" --rpc-url base-sepolia`

**Checkpoint**: Smart contract has nextTokenId() getter - user story implementation can now begin

---

## Phase 3: User Story 1 - Automatic Token Discovery (Priority: P1) 🎯 MVP

**Goal**: Implement core recovery mechanism that queries contract nextTokenId, identifies missing tokens in database, and creates records with accurate author attribution from on-chain data

**Independent Test**: Mint tokens directly on-chain (bypassing webhooks), run recovery CLI, verify all missing tokens appear in database with status='detected' and actual author addresses from contract

### Implementation for User Story 1

- [x] T008 [P] [US1] Create custom exception hierarchy in backend/src/glisk/services/exceptions.py: Add RecoveryError, BlockchainConnectionError, ContractNotFoundError, DefaultAuthorNotFoundError
- [x] T009 [P] [US1] Add get_missing_token_ids() method to backend/src/glisk/repositories/token.py: Use generate_series(1, max_token_id-1) LEFT JOIN to find gaps, return list[int]
- [x] T010 [US1] Create TokenRecoveryService in backend/src/glisk/services/blockchain/token_recovery.py: Implement get_next_token_id() with retry logic and recover_missing_tokens() with author lookup from contract
- [x] T011 [US1] Create CLI command in backend/src/glisk/cli/recover_tokens.py: Accept --limit and --dry-run flags, instantiate TokenRecoveryService, print RecoveryResult summary
- [x] T012 [US1] Add author lookup method to backend/src/glisk/repositories/author.py: get_by_wallet(wallet_address) if not already exists (integrated into T010)
- [x] T013 [US1] Update TokenRecoveryService to query tokenPromptAuthor(tokenId) from contract for each missing token and lookup/create author in database (integrated into T010)
- [x] T014 [US1] Add structured logging events to TokenRecoveryService: recovery.started, recovery.gaps_detected, recovery.token_created, recovery.duplicate_skipped, recovery.completed, recovery.failed (integrated into T010)

### Verification for User Story 1

- [x] T015 [P] [US1] Write unit test for get_missing_token_ids() in backend/tests/test_token_recovery.py: Test empty DB, partial gaps, no gaps, single missing, large gap (1000+ tokens)
- [x] T016 [P] [US1] Write unit test for TokenRecoveryService.get_next_token_id() in backend/tests/test_token_recovery.py: Mock web3 responses, test retry logic, test ContractNotFoundError
- [x] T017 [P] [US1] Write integration test for full recovery flow in backend/tests/test_token_recovery.py: Use testcontainer PostgreSQL, seed with gaps, run recovery, verify all tokens created with status='detected' and correct author_id
- [ ] T018 [US1] Manual testnet validation per quickstart.md Step 9: Mint tokens directly via Etherscan/cast, run recovery CLI, verify tokens in DB, verify image generation worker processes them

**Checkpoint**: User Story 1 is fully functional - recovery mechanism discovers missing tokens with accurate author attribution and creates database records

---

## Phase 4: User Story 2 - Remove Unused Metadata Fields (Priority: P2)

**Goal**: Clean up database schema by removing mint_timestamp and minter_address fields that cannot be populated during simplified recovery

**Independent Test**: Verify storage schema no longer contains timestamp and minter address fields, and all application processes (image generation, IPFS upload, reveal workers) function correctly without these fields

### Implementation for User Story 2

- [x] T019 [US2] Remove mint_timestamp and minter_address field definitions from backend/src/glisk/models/token.py (lines 38-40 and validator lines 54-64)
- [x] T020 [US2] Generate Alembic migration: `cd backend && uv run alembic revision --autogenerate -m "remove_unused_recovery_fields"`
- [x] T021 [US2] Manually verify migration file backend/alembic/versions/*_remove_unused_recovery_fields.py contains op.drop_column for both fields
- [x] T022 [US2] Add downgrade() implementation to migration: recreate columns with nullable=True for rollback safety
- [x] T023 [US2] Grep codebase for field references: `rg "mint_timestamp|minter_address" backend/` and document all files to update
- [x] T024 [US2] Update get_pending_for_generation() in backend/src/glisk/repositories/token.py: Change ORDER BY from mint_timestamp.asc() to created_at.asc()
- [x] T025 [US2] Apply migration: `cd backend && uv run alembic upgrade head`

### Verification for User Story 2

- [x] T026 [P] [US2] Verify schema changes via psql: `docker exec backend-postgres-1 psql -U glisk -d glisk -c "\d tokens_s0"` should NOT show mint_timestamp or minter_address columns
- [x] T027 [P] [US2] Run all tests to verify no breakage: `cd backend && TZ=America/Los_Angeles uv run pytest tests/ -v`
- [x] T028 [US2] Test migration idempotency: `cd backend && uv run alembic downgrade -1 && uv run alembic upgrade head` should succeed
- [x] T029 [US2] Manual verification: Start application, verify image generation worker still processes tokens correctly (check logs for no field reference errors)

**Checkpoint**: Database schema is simplified, all processes work without removed fields

---

## Phase 5: User Story 3 - Deprecate Event-Based Recovery (Priority: P3)

**Goal**: Remove obsolete web3 event-based recovery mechanism (eth_getLogs parsing) and associated tests to reduce code complexity by 200+ LOC

**Independent Test**: Verify event-based recovery modules and CLI commands are removed, their tests are deleted, and all remaining tests pass

### Implementation for User Story 3

- [x] T030 [P] [US3] Delete backend/src/glisk/services/blockchain/event_recovery.py
- [x] T031 [P] [US3] Delete backend/src/glisk/cli/recover_events.py
- [x] T032 [P] [US3] Delete backend/tests/unit/services/blockchain/test_event_recovery.py if exists
- [x] T033 [P] [US3] Delete backend/tests/unit/cli/test_recover_events.py if exists
- [x] T034 [US3] Grep codebase for imports of deleted modules: `rg "event_recovery|recover_events" backend/` and remove any remaining references
- [x] T035 [US3] Update CLAUDE.md to remove old "Event Recovery CLI" documentation (lines referring to recover_events.py command)
- [x] T036 [US3] Add new "Token Recovery CLI" documentation to CLAUDE.md with usage: `python -m glisk.cli.recover_tokens [--limit N] [--dry-run]`

### Verification for User Story 3

- [x] T037 [P] [US3] Run full test suite to verify nothing broke: `cd backend && TZ=America/Los_Angeles uv run pytest tests/ -v`
- [x] T038 [P] [US3] Count lines of code removed: `git diff --stat` should show ~200+ LOC deleted (actual: 1082 LOC deleted!)
- [x] T039 [US3] Verify attempting to run old CLI fails appropriately: `python -m glisk.cli.recover_events` should raise ModuleNotFoundError

**Checkpoint**: Old recovery code is completely removed, test suite passes, codebase is simpler

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Integration, documentation, and final validation

- [ ] T040 [P] Add recovery to application startup lifecycle in backend/src/glisk/main.py: Call recovery_service.recover_missing_tokens() in lifespan() before starting workers (per quickstart.md integration section)
- [ ] T041 [P] Add RECOVERY_BATCH_SIZE config to backend/src/glisk/core/config.py with default 1000
- [ ] T042 Update quickstart.md to mark all success criteria as verified
- [ ] T043 Run final validation: All tests pass, manual testnet recovery works, workers process recovered tokens
- [ ] T044 [P] Pre-commit hooks validation: Ensure no --no-verify commits were made
- [ ] T045 Code review: Verify constitution compliance (Simplicity First, Clear Over Clever)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - User stories can proceed in priority order (P1 → P2 → P3) sequentially
  - OR in parallel if team capacity allows (independent user stories)
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Independent, but logically follows US1 (don't want to migrate before new recovery exists)
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Independent, but should follow US1 (don't delete old recovery before new one works)

### Within Each User Story

**US1 (Token Discovery)**:
- T008 (exceptions) and T009 (repository method) can run in parallel [P]
- T010 (service) depends on T008, T009 completing
- T011 (CLI) depends on T010 completing
- T012 (author repository) can run anytime in parallel [P]
- T013 (author lookup integration) depends on T010, T012 completing
- T014 (logging) depends on T010 completing
- Tests T015, T016, T017 can run in parallel after implementation [P]
- T018 (manual validation) runs after all implementation complete

**US2 (Remove Fields)**:
- T019 (model changes) starts the story
- T020-T022 (migration) sequential after T019
- T023 (grep) can run in parallel with migration [P]
- T024 (repository update) after T023
- T025 (apply migration) after T024
- Tests T026-T029 can run in parallel after T025 [P]

**US3 (Deprecate Old Code)**:
- T030-T033 (deletions) can all run in parallel [P]
- T034 (grep cleanup) after deletions
- T035-T036 (docs) can run in parallel [P]
- Tests T037-T039 can run in parallel after cleanup [P]

### Parallel Opportunities

- **Phase 1**: T001, T002, T003 can run in parallel
- **Phase 2**: Sequential (contract changes required)
- **US1**: T008 + T009 parallel, T015 + T016 + T017 parallel
- **US2**: T026 + T027 + T028 parallel
- **US3**: T030 + T031 + T032 + T033 parallel, T035 + T036 parallel, T037 + T038 + T039 parallel
- **Phase 6**: T040 + T041 + T044 parallel

---

## Parallel Example: User Story 1 Implementation

```bash
# Launch exception hierarchy and repository method together:
Task T008: "Create custom exception hierarchy in backend/src/glisk/services/exceptions.py"
Task T009: "Add get_missing_token_ids() to backend/src/glisk/repositories/token.py"

# After service is implemented, launch all unit tests together:
Task T015: "Unit test for get_missing_token_ids()"
Task T016: "Unit test for TokenRecoveryService.get_next_token_id()"
Task T017: "Integration test for full recovery flow"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only - Recommended)

1. Complete Phase 1: Setup (verify prerequisites)
2. Complete Phase 2: Foundational (add nextTokenId to contract, redeploy)
3. Complete Phase 3: User Story 1 (recovery mechanism)
4. **STOP and VALIDATE**: Test recovery independently on testnet
5. Deploy and use - you now have working recovery without old field dependencies

**Why stop at US1**: This delivers the core value (simplified, accurate recovery). US2 and US3 are cleanup tasks that can wait.

### Full Feature Delivery (All Stories)

1. Complete Setup + Foundational → Foundation ready
2. Complete User Story 1 → Test independently → Core recovery works ✓
3. Complete User Story 2 → Test independently → Schema cleaned ✓
4. Complete User Story 3 → Test independently → Old code removed ✓
5. Complete Polish → Integration ready → Production ready ✓

### Sequential vs Parallel

**Sequential (Single Developer)**:
- Work through phases 1 → 2 → 3 → 4 → 5 → 6 in order
- Complete all tasks in each phase before moving to next
- Safer, easier to debug, less context switching

**Parallel (Multiple Developers)**:
- Team completes Setup + Foundational together
- After Phase 2:
  - Developer A: User Story 1 (critical path)
  - Developer B: User Story 2 (after US1 implementation done)
  - Developer C: User Story 3 (after US1 implementation done)
- Faster delivery but requires coordination

---

## Task Count Summary

| Phase | Tasks | Parallel Opportunities |
|-------|-------|----------------------|
| Setup | 3 | 3 (all parallel) |
| Foundational | 4 | 0 (sequential contract work) |
| US1 - Token Discovery | 11 | 6 (2 at start, 3 tests, 1 in middle) |
| US2 - Remove Fields | 11 | 4 (tests after migration) |
| US3 - Deprecate Old | 10 | 9 (most deletions and tests) |
| Polish | 6 | 3 |
| **TOTAL** | **45** | **25 (55% parallelizable)** |

---

## Validation Checklist (Success Criteria from spec.md)

After completing all phases, verify:

**User Story 1 - Automatic Token Discovery**:
- [ ] SC-001: Recovery mechanism identifies all missing tokens (0% false negatives)
- [ ] SC-002: Recovery mechanism produces zero false positives (no duplicate tokens created)
- [ ] SC-003: Recovery completes in <5 seconds for gaps of up to 100 tokens
- [ ] SC-004: Database query for missing tokens <1 second for token counts up to 100k
- [ ] Recovery queries tokenPromptAuthor(tokenId) from contract for accurate author attribution
- [ ] If author wallet doesn't exist in DB, system creates new author record automatically

**User Story 2 - Remove Unused Fields**:
- [ ] SC-006: Zero application errors after removing fields (all processes and tests pass)
- [ ] Database schema no longer has mint_timestamp or minter_address columns
- [ ] Image generation worker uses created_at for ordering instead of mint_timestamp
- [ ] All workers function correctly without removed fields

**User Story 3 - Deprecate Old Recovery**:
- [ ] SC-005: At least 200 lines of code removed (event-based recovery logic and tests)
- [ ] event_recovery.py module deleted
- [ ] recover_events.py CLI deleted
- [ ] All tests for old recovery deleted
- [ ] No code references old recovery modules
- [ ] CLAUDE.md updated with new recovery documentation

**Cross-Story Integration**:
- [ ] All tests pass: `cd backend && TZ=America/Los_Angeles uv run pytest tests/ -v`
- [ ] Manual testnet validation: Mint directly, run recovery, verify tokens created
- [ ] Image generation worker processes recovered tokens normally
- [ ] Recovery runs automatically on application startup (optional integration)

---

## Notes

- Tests are included for verification but NOT required to be written first (no TDD mandate)
- Each user story should be independently completable and testable
- Stop at any checkpoint to validate story independently
- Commit after each task or logical group
- Follow Alembic autogenerate workflow per CLAUDE.md (T020-T022)
- Follow git commit rules per CLAUDE.md (never use --no-verify)
- Phase-based testing per CLAUDE.md: Run pytest before and after each phase
- Token IDs start at 1 (not 0) per contract implementation
- Author attribution queries tokenPromptAuthor(tokenId) from contract for accuracy
