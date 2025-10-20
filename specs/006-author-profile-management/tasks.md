# Tasks: Author Profile Management

**Input**: Design documents from `/specs/006-author-profile-management/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api-contracts.md

**Tests**: Backend integration tests included per constitution. Frontend uses manual testing (per constitution v1.2.0).

**Organization**: Tasks are grouped by user story (US1, US3, US2) to enable independent implementation and testing. Note: US3 (Security) must be implemented with US1 since it's a foundational security requirement.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions
- **Backend**: `backend/src/glisk/`, `backend/tests/`
- **Frontend**: `frontend/src/`
- **No contract changes**: Feature uses existing smart contract

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify prerequisites and project structure

- [ ] T001 Verify PostgreSQL `authors` table schema has required fields (wallet_address UNIQUE, prompt_text TEXT, created_at)
- [ ] T002 Verify `eth-account` library is installed via web3.py (no new dependencies needed)
- [ ] T003 [P] Verify frontend has wagmi + viem + RainbowKit installed from previous features
- [ ] T004 [P] Verify backend has FastAPI + SQLModel + structlog from previous features

**Checkpoint**: All prerequisites verified, no new dependencies needed

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T005 Add `authorClaimable` mapping ABI entry to `frontend/src/lib/contract.ts` (read claimable balance from contract)
- [ ] T006 Add `claimAuthorRewards()` function ABI entry to `frontend/src/lib/contract.ts` (claim transaction)
- [ ] T007 Create wallet signature verification service in `backend/src/glisk/services/wallet_signature.py` (EIP-191 verification using eth-account)
- [ ] T008 Add `upsert_author_prompt()` method to `backend/src/glisk/repositories/author.py` (create or update author's prompt)

**Checkpoint**: Foundation ready - signature verification and repository methods available

---

## Phase 3: User Story 1 + User Story 3 - Set Prompt with Security (Priority: P1) 🎯 MVP

**Goal**: Creators can securely set/update their AI generation prompt with wallet signature verification

**Why combined**: US3 (Wallet Ownership Verification) is a foundational security requirement that MUST be implemented with US1. Cannot allow prompt updates without signature verification.

**Independent Test**: Connect wallet, enter prompt (e.g., "Surreal landscapes with neon lighting"), click save, approve signature, reload page to verify persistence. Then connect different wallet and verify first wallet's prompt cannot be modified.

### Backend Tests for US1+US3

**NOTE: Write these tests FIRST, ensure they FAIL before implementation (TDD)**

- [ ] T009 [P] [US1+US3] Create signature verification tests in `backend/tests/test_wallet_signature.py`:
  - Test valid signature verification succeeds
  - Test invalid signature (wrong wallet) fails
  - Test malformed signature raises ValueError
  - Test case-insensitive address comparison
- [ ] T010 [P] [US1+US3] Create author API integration tests in `backend/tests/test_author_routes.py`:
  - Test POST /api/authors/prompt with valid signature creates new author (verify `{"success": true, "has_prompt": true}` response)
  - Test POST /api/authors/prompt with valid signature updates existing author (verify no prompt_text in response)
  - Test POST /api/authors/prompt with invalid signature returns 400 error
  - Test POST /api/authors/prompt with empty prompt returns 400 validation error
  - Test POST /api/authors/prompt with prompt >1000 chars returns 400 error
  - Test GET /api/authors/{wallet_address} returns `{"has_prompt": true}` for existing author (case-insensitive)
  - Test GET /api/authors/{wallet_address} returns `{"has_prompt": false}` for non-existent author (200 OK, not 404)

### Backend Implementation for US1+US3

- [ ] T011 [US1+US3] Create API routes file `backend/src/glisk/api/routes/authors.py`:
  - Define `UpdatePromptRequest` Pydantic model (wallet_address, prompt_text, signature, message)
  - Define `UpdatePromptResponse` Pydantic model (success: bool, has_prompt: bool)
  - Define `AuthorStatusResponse` Pydantic model (has_prompt: bool)
  - Implement `POST /api/authors/prompt` endpoint with signature verification (returns UpdatePromptResponse, no prompt_text echo)
  - Implement `GET /api/authors/{wallet_address}` endpoint (returns AuthorStatusResponse, never 404)
  - Add structured error responses (400 for validation, 401 for auth)
- [ ] T012 [US1+US3] Register authors router in `backend/src/glisk/app.py` (add `app.include_router(authors.router)`)
- [ ] T013 [US1+US3] Add CORS configuration for frontend origin in `backend/src/glisk/app.py` if not already present

### Frontend Implementation for US1+US3

- [ ] T014 [P] [US1+US3] Create CreatorDashboard page in `frontend/src/pages/CreatorDashboard.tsx`:
  - Import wagmi hooks (useAccount, useSignMessage)
  - Add wallet connection check (redirect if not connected)
  - Query prompt status on mount (GET /api/authors/{address} → display status indicator)
  - Display "✓ Prompt configured" or "⚠ No prompt set" based on has_prompt boolean
  - Create prompt input textarea (1-1000 character validation, always empty - no pre-fill)
  - Add character counter display
  - Implement save button with signature flow
  - Display success/error messages (no prompt echo after save)
  - Handle signature rejection gracefully
- [ ] T015 [US1+US3] Add `/creator-dashboard` route to `frontend/src/App.tsx` (import CreatorDashboard component)
- [ ] T016 [P] [US1+US3] Add "Creator Dashboard" navigation link to `frontend/src/components/Header.tsx` (visible when wallet connected)

**Checkpoint**: At this point, creators can securely set/update prompts with signature verification. US1 + US3 fully functional and independently testable.

---

## Phase 4: User Story 2 - Claim Creator Rewards (Priority: P2)

**Goal**: Creators can claim accumulated ETH rewards from smart contract

**Independent Test**: Mint NFT using your wallet as prompt author (to accumulate balance), navigate to `/creator-dashboard`, verify balance displays, click "Claim Rewards", approve transaction, wait for confirmation, verify balance updates to 0 ETH and ETH received in wallet.

### Backend Implementation for US2

**No backend changes needed** - claim transaction happens directly between wallet and smart contract (no API intermediary)

### Frontend Implementation for US2

- [ ] T017 [US2] Add rewards claiming section to `frontend/src/pages/CreatorDashboard.tsx`:
  - Import wagmi hooks (useReadContract, useWriteContract, useWaitForTransactionReceipt)
  - Query `authorClaimable[address]` from contract (useReadContract)
  - Display claimable balance in ETH (convert wei to ETH using formatEther)
  - Add "Claim Rewards" button (disabled when balance is 0 or transaction pending)
  - Implement claim transaction flow (writeContract calling claimAuthorRewards())
  - Handle transaction states (pending, confirming, success, failure)
  - Display transaction status messages
  - Refetch balance after successful claim (update UI to show 0 ETH)
  - Handle wallet rejection and network errors with clear messages

**Checkpoint**: At this point, creators can claim rewards. All user stories (US1, US2, US3) independently functional.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Final touches, edge case handling, documentation

- [ ] T018 [P] Add wallet change detection to `frontend/src/pages/CreatorDashboard.tsx` (useEffect watching address, reload data on change)
- [ ] T019 [P] Add RPC error handling to `frontend/src/pages/CreatorDashboard.tsx` (graceful fallback when contract queries fail)
- [ ] T020 [P] Add structured logging to backend signature verification in `backend/src/glisk/services/wallet_signature.py` (log verification attempts, successes, failures)
- [ ] T021 [P] Add structured logging to backend API routes in `backend/src/glisk/api/routes/authors.py` (log prompt updates, author lookups)
- [ ] T022 [P] Test edge cases manually:
  - Prompt with emojis and special characters (should save successfully, verify backend logs)
  - Prompt with newlines and formatting (should save to database, verify via backend)
  - Status indicator updates after first prompt save ("⚠ No prompt" → "✓ Prompt configured")
  - Prompt input remains empty after save and page reload (no pre-fill behavior)
  - Concurrent prompt updates from same wallet (PostgreSQL handles via MVCC)
  - Wallet disconnection during save operation (should show reconnect prompt)
  - Network congestion during claim transaction (should show retry option)
  - Zero claimable balance (button disabled with "No rewards to claim")
  - GET request for non-existent author returns `{"has_prompt": false}` not 404

**Checkpoint**: Feature complete with robust error handling and edge case coverage

---

## Dependencies Graph

```
Phase 1 (Setup)
  ↓
Phase 2 (Foundational - BLOCKING)
  ↓
  ├─→ Phase 3 (US1+US3 - MVP) ✅ Independent
  │   [Can ship to users at this checkpoint]
  │
  ├─→ Phase 4 (US2) ✅ Independent (no dependency on US1, but US1 enhances value)
  │
  └─→ Phase 5 (Polish) - Touches all user stories
```

**Independent Delivery Points**:
1. After Phase 3: Ship prompt management (creators can set prompts for image generation)
2. After Phase 4: Ship complete feature (creators can also claim rewards)

---

## Parallel Execution Examples

### Phase 2 - Foundational Setup (4 tasks, 2 parallel groups)
```bash
# Group 1: Frontend ABI updates (T005, T006) - can run in parallel
Terminal 1: Edit frontend/src/lib/contract.ts (add authorClaimable ABI)
Terminal 2: Edit frontend/src/lib/contract.ts (add claimAuthorRewards ABI)
# Actually same file, so run sequentially

# Group 2: Backend infrastructure (T007, T008) - can run in parallel
Terminal 1: Create backend/src/glisk/services/wallet_signature.py
Terminal 2: Edit backend/src/glisk/repositories/author.py (add upsert method)
```

### Phase 3 - US1+US3 Tests (2 parallel test files)
```bash
# Backend tests (T009, T010) - different files, can run in parallel
Terminal 1: Create backend/tests/test_wallet_signature.py
Terminal 2: Create backend/tests/test_author_routes.py
```

### Phase 3 - US1+US3 Implementation (3 parallel + 3 sequential)
```bash
# Parallel group (T014, T015, T016) - different files
Terminal 1: Create frontend/src/pages/CreatorDashboard.tsx
Terminal 2: Edit frontend/src/App.tsx (add route)
Terminal 3: Edit frontend/src/components/Header.tsx (add nav link)

# Sequential (T011, T012, T013) - same file or dependencies
Step 1: Create backend/src/glisk/api/routes/authors.py
Step 2: Edit backend/src/glisk/app.py (register router)
Step 3: Edit backend/src/glisk/app.py (verify CORS config)
```

### Phase 4 - US2 Implementation (1 task, no parallelization)
```bash
# Single file modification
Terminal 1: Edit frontend/src/pages/CreatorDashboard.tsx (add rewards section)
```

### Phase 5 - Polish (5 parallel tasks)
```bash
# All different files or independent concerns
Terminal 1: Edit CreatorDashboard.tsx (wallet change detection)
Terminal 2: Edit CreatorDashboard.tsx (RPC error handling)
Terminal 3: Edit wallet_signature.py (add logging)
Terminal 4: Edit authors.py routes (add logging)
Terminal 5: Manual testing checklist (can run anytime)
```

---

## Testing Strategy

### Backend Testing (pytest + testcontainers)
- **T009**: Unit tests for signature verification (7 test cases)
- **T010**: Integration tests for API endpoints (7 test cases)
- **Run via**: `cd backend && TZ=America/Los_Angeles uv run pytest tests/`

### Frontend Testing (Manual - per constitution)
- **T022**: Manual edge case testing checklist
- **Goal**: Verify user flows work end-to-end in browser
- **Tools**: MetaMask + Base Sepolia testnet + local dev servers

### Pre-Deployment Checklist
- [ ] All backend pytest tests pass
- [ ] Manual testing checklist completed (T022)
- [ ] Prompt save works with signature verification
- [ ] Prompt update replaces existing in database (no duplicates)
- [ ] Status indicator shows correct prompt state (has_prompt boolean)
- [ ] Prompt text is never exposed via API responses
- [ ] Rewards claim transaction succeeds on testnet
- [ ] Error messages are clear and actionable
- [ ] Wallet disconnection handled gracefully

---

## Implementation Strategy

### MVP Scope (Minimum Viable Product)
**Ship after Phase 3**: Prompt management with security (US1 + US3)
- Value: Creators can set prompts immediately, enabling image generation for their mints
- Testable: Can verify prompts persist and signature verification works
- Delivers: Core creator identity feature

### Full Feature Scope
**Ship after Phase 4**: Add reward claiming (US2)
- Value: Creators can financially benefit from their contributions
- Testable: Can verify claim transaction succeeds and balance updates
- Delivers: Complete creator dashboard experience

### Incremental Delivery
1. **Week 1**: Phase 1-3 (MVP - prompt management)
2. **Week 2**: Phase 4-5 (rewards + polish)

---

## Task Summary

- **Total Tasks**: 22
- **Setup Phase**: 4 tasks
- **Foundational Phase**: 4 tasks (blocking for all user stories)
- **User Story 1+3 (MVP)**: 8 tasks (2 test files + 6 implementation tasks)
- **User Story 2**: 1 task (frontend only, no backend)
- **Polish Phase**: 5 tasks (cross-cutting improvements)

**Parallel Opportunities**:
- Phase 2: 2 parallel groups (frontend ABI + backend infrastructure)
- Phase 3 Tests: 2 parallel test files
- Phase 3 Implementation: 3 parallel frontend tasks
- Phase 5: 5 parallel polish tasks

**Estimated Timeline**: 2-3 days for full implementation
- Day 1: Setup + Foundational + US1+US3 (MVP)
- Day 2: US2 + Polish
- Day 3: Testing + bug fixes

---

## Notes

- **No database migrations**: Existing `authors` table fully supports requirements
- **No new dependencies**: Uses `eth-account` (already installed via web3.py)
- **Security**: All prompt updates require EIP-191 signature verification (US3)
- **Performance**: API responses <500ms p95, balance queries <5s (RPC latency)
- **Constitution compliance**: Simplicity First (reuses existing models), Seasonal MVP (manual testing), Clear Over Clever (explicit errors)
