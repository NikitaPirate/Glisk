# Tasks: Unified Profile Page with Author & Collector Tabs

**Input**: Design documents from `/specs/008-unified-profile-page/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api-endpoints.md, quickstart.md

**Tests**: No automated tests required per constitution frontend standards (manual testing only)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions (GLISK Monorepo)
- Frontend: `frontend/src/` (primary domain for this feature)
- Backend: `backend/src/glisk/api/routes/`, `backend/src/glisk/repositories/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Environment configuration for OnchainKit NFT components

- [ ] T001 Verify OnchainKit dependency installed in frontend/package.json (@coinbase/onchainkit@^1.1.1)
- [ ] T002 Add VITE_ONCHAINKIT_API_KEY to frontend/.env with Coinbase Developer Platform API key
- [ ] T003 Verify existing environment variables (VITE_CONTRACT_ADDRESS, VITE_API_BASE_URL, VITE_WALLETCONNECT_PROJECT_ID)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Backend API endpoint that MUST be complete before frontend tabs can fetch authored NFTs

**⚠️ CRITICAL**: User Story 2 (Prompt Author tab) cannot be implemented until this phase is complete

- [ ] T004 [P] Create TokenDTO Pydantic model in backend/src/glisk/api/routes/authors.py (token_id, status, image_cid, metadata_cid, image_url, generation_attempts, generation_error, reveal_tx_hash, created_at)
- [ ] T005 [P] Create TokensResponse Pydantic model in backend/src/glisk/api/routes/authors.py (tokens list, total int, offset int, limit int)
- [ ] T006 Add get_tokens_by_author_paginated method to TokenRepository in backend/src/glisk/repositories/token.py (author_id UUID, offset int, limit int) → (list[Token], total int)
- [ ] T007 Implement GET /api/authors/{wallet_address}/tokens endpoint in backend/src/glisk/api/routes/authors.py with offset/limit query params
- [ ] T008 Add validation for offset (>=0) and limit (1-100) in backend endpoint
- [ ] T009 Add error handling for invalid wallet address (return empty results, not 400) in backend endpoint
- [ ] T010 Add structured logging for tokens_retrieved, invalid_wallet_format, author_not_found events in backend endpoint
- [ ] T011 Test backend endpoint manually using curl (see contracts/api-endpoints.md examples)

**Checkpoint**: Backend API ready - frontend tabs can now be implemented

---

## Phase 3: User Story 1 - Navigate to Unified Profile Page (Priority: P1) 🎯 MVP

**Goal**: Users can navigate to /profile from header, see tab navigation working, and view consolidated prompt/X linking sections

**Independent Test**: Connect wallet, click Profile button, verify navigation to /profile?tab=author and Prompt Author tab displays

### Implementation for User Story 1

- [ ] T012 [P] [US1] Create ProfilePage.tsx component in frontend/src/pages/ with basic structure (tabs container, query param handling)
- [ ] T013 [P] [US1] Create PromptAuthor.tsx tab component in frontend/src/components/ (empty placeholder for now)
- [ ] T014 [P] [US1] Create Collector.tsx tab component in frontend/src/components/ (empty placeholder for now)
- [ ] T015 [US1] Implement tab state management in ProfilePage.tsx using useSearchParams hook from react-router
- [ ] T016 [US1] Add tab validation (VALID_TABS = ['author', 'collector']) with fallback to 'author' for invalid params
- [ ] T017 [US1] Add useEffect to set default tab=author when no query param (replace: true to prevent back button loop)
- [ ] T018 [US1] Create tab switching buttons in ProfilePage.tsx that call setSearchParams({ tab }) to update URL
- [ ] T019 [US1] Add conditional rendering in ProfilePage.tsx to show PromptAuthor or Collector component based on activeTab
- [ ] T020 [US1] Copy prompt management UI from CreatorDashboard.tsx (lines 247-350) into PromptAuthor.tsx component
- [ ] T021 [US1] Copy X account linking UI from ProfileSettings.tsx (lines 199-289) into PromptAuthor.tsx component
- [ ] T022 [US1] Verify prompt management functionality works identically in new location (save prompt, show status)
- [ ] T023 [US1] Verify X linking functionality works identically in new location (OAuth flow, link/unlink)
- [ ] T024 [US1] Add /profile route to frontend/src/App.tsx routing configuration
- [ ] T025 [US1] Update Header.tsx to replace "Creator Dashboard" and "Profile Settings" buttons with single "Profile" button linking to /profile?tab=author
- [ ] T026 [US1] Add wallet connection requirement check in ProfilePage.tsx (show "Connect wallet" message if not connected)

**Checkpoint**: At this point, users can navigate to /profile, switch tabs (empty Collector tab), and use prompt/X linking features in Prompt Author tab

---

## Phase 4: User Story 2 - View Authored NFTs in Prompt Author Tab (Priority: P1) 🎯 MVP

**Goal**: Users see paginated list of NFTs they authored in the Prompt Author tab, fetched from backend API

**Independent Test**: Connect wallet with authored NFTs, navigate to Prompt Author tab, verify authored NFTs display with pagination for >20 tokens

### Implementation for User Story 2

- [ ] T027 [P] [US2] Create TokensResponse TypeScript interface in PromptAuthor.tsx (tokens array, total, offset, limit)
- [ ] T028 [P] [US2] Create TokenDTO TypeScript interface in PromptAuthor.tsx (token_id, status, image_cid, metadata_cid, image_url, generation_attempts, generation_error, reveal_tx_hash, created_at)
- [ ] T029 [US2] Create fetchAuthoredTokens async function in PromptAuthor.tsx using fetch API (walletAddress, page params)
- [ ] T030 [US2] Add useQuery hook from @tanstack/react-query in PromptAuthor.tsx for authored NFTs data (queryKey: ['authored-nfts', address, page])
- [ ] T031 [US2] Add pagination state (authoredPage useState) in PromptAuthor.tsx (default: 1)
- [ ] T032 [US2] Calculate totalPages = Math.ceil(total / 20) for pagination controls in PromptAuthor.tsx
- [ ] T033 [US2] Create NFTGrid.tsx reusable component in frontend/src/components/ (accepts tokens array, renders grid with OnchainKit NFTCard)
- [ ] T034 [US2] Import NFTCard, NFTMedia, NFTTitle from @coinbase/onchainkit/nft in NFTGrid.tsx
- [ ] T035 [US2] Map over tokens array in NFTGrid.tsx and render NFTCard with contractAddress and tokenId props
- [ ] T036 [US2] Add loading state display in PromptAuthor.tsx ("Loading..." text while fetching)
- [ ] T037 [US2] Add error state display in PromptAuthor.tsx (error message with retry button)
- [ ] T038 [US2] Add empty state display in PromptAuthor.tsx (no error when 0 tokens)
- [ ] T039 [US2] Add pagination controls in PromptAuthor.tsx (Previous/Next buttons with page number display)
- [ ] T040 [US2] Disable pagination controls when isLoading=true in PromptAuthor.tsx
- [ ] T041 [US2] Hide pagination controls when total <= 20 in PromptAuthor.tsx
- [ ] T042 [US2] Add wallet change detection in PromptAuthor.tsx (useEffect on address) to reset authoredPage to 1
- [ ] T043 [US2] Render NFTGrid component below X linking section in PromptAuthor.tsx

**Checkpoint**: At this point, Prompt Author tab shows authored NFTs with pagination, all existing functionality preserved

---

## Phase 5: User Story 3 - View Owned NFTs in Collector Tab (Priority: P1) 🎯 MVP

**Goal**: Users see paginated list of NFTs they own, fetched from blockchain via ERC721Enumerable, using OnchainKit NFTCard components

**Independent Test**: Connect wallet with owned NFTs, switch to Collector tab, verify owned NFTs display with pagination for >20 tokens

### Implementation for User Story 3

- [ ] T044 [P] [US3] Import useAccount, useReadContract, useInfiniteReadContracts from wagmi in Collector.tsx
- [ ] T045 [P] [US3] Import GLISK NFT ABI (or minimal ABI with balanceOf, tokenOfOwnerByIndex) in Collector.tsx
- [ ] T046 [US3] Get CONTRACT_ADDRESS from import.meta.env.VITE_CONTRACT_ADDRESS in Collector.tsx
- [ ] T047 [US3] Call useAccount hook to get current wallet address in Collector.tsx
- [ ] T048 [US3] Call useReadContract for balanceOf(address) in Collector.tsx to get total owned NFTs count
- [ ] T049 [US3] Implement useInfiniteReadContracts hook in Collector.tsx with contracts function generating tokenOfOwnerByIndex calls
- [ ] T050 [US3] Configure pagination in useInfiniteReadContracts: TOKENS_PER_PAGE=20, initialPageParam=0, getNextPageParam logic
- [ ] T051 [US3] Calculate tokensInBatch = Math.min(TOKENS_PER_PAGE, balance - startIndex) to avoid over-fetching
- [ ] T052 [US3] Extract tokenIds from data.pages using flatMap in Collector.tsx (filter out failed results)
- [ ] T053 [US3] Add loading state display in Collector.tsx ("Loading your collection..." text while fetching)
- [ ] T054 [US3] Add error state display in Collector.tsx (network error message with retry button)
- [ ] T055 [US3] Add empty state display in Collector.tsx ("No NFTs owned" when balance=0)
- [ ] T056 [US3] Add pagination state (ownedPage useState) in Collector.tsx (default: 1)
- [ ] T057 [US3] Calculate totalPages = Math.ceil(tokenIds.length / 20) for pagination controls in Collector.tsx
- [ ] T058 [US3] Render NFTGrid component with tokenIds.slice((ownedPage - 1) * 20, ownedPage * 20) for current page in Collector.tsx
- [ ] T059 [US3] Add pagination controls in Collector.tsx (Previous/Next buttons with page number display)
- [ ] T060 [US3] Disable pagination controls when isLoading=true in Collector.tsx
- [ ] T061 [US3] Hide pagination controls when tokenIds.length <= 20 in Collector.tsx
- [ ] T062 [US3] Add wallet change detection in Collector.tsx (useEffect on address) to reset ownedPage to 1 and refetch

**Checkpoint**: At this point, Collector tab shows owned NFTs with Previous/Next pagination matching Author tab UX, blockchain reads working

---

## Phase 6: User Story 4 - Tab Switching Preserves State (Priority: P2)

**Goal**: Tab switching is smooth, data refetches only when wallet changes (Note: State preservation across tab switches is out of scope per constitution - components unmount/remount)

**Independent Test**: Navigate to page 2 on Prompt Author tab, switch to Collector tab, switch back, verify Prompt Author tab resets to page 1 (expected MVP behavior)

### Implementation for User Story 4

- [ ] T063 [US4] Verify useQuery caching in PromptAuthor.tsx has staleTime=30000 (30 seconds) for cache persistence
- [ ] T064 [US4] Verify useInfiniteReadContracts in Collector.tsx has enabled=!!address && !!balance to prevent unnecessary refetches
- [ ] T065 [US4] Add wallet change invalidation in ProfilePage.tsx: useEffect on address change to clear all query caches
- [ ] T066 [US4] Test rapid tab switching doesn't cause race conditions (latest tab selection wins, old requests cancelled)
- [ ] T067 [US4] Confirm pagination resets to page 1 when wallet changes in both tabs

**Checkpoint**: All user stories complete, tab switching works smoothly with appropriate data refetching

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Cleanup, documentation, and validation

- [ ] T068 [P] Remove old /creator-dashboard route from frontend/src/App.tsx
- [ ] T069 [P] Remove old /profile-settings route from frontend/src/App.tsx
- [ ] T070 [P] Delete CreatorDashboard.tsx file from frontend/src/pages/
- [ ] T071 [P] Delete ProfileSettings.tsx file from frontend/src/pages/
- [ ] T072 Verify all functional requirements FR-001 through FR-021 from spec.md (manual testing per quickstart.md)
- [ ] T073 Verify all success criteria SC-001 through SC-010 from spec.md (performance benchmarks per quickstart.md)
- [ ] T074 Test all edge cases from spec.md (invalid tab param, API errors, RPC errors, 0 NFTs, exactly 20 NFTs, rapid switching, wallet changes)
- [ ] T075 Run full quickstart.md validation (Tests 1-10)
- [ ] T076 [P] Add basic Tailwind utility classes for spacing/layout in ProfilePage.tsx, PromptAuthor.tsx, Collector.tsx, NFTGrid.tsx (minimal styling only)
- [ ] T077 Code review for constitution compliance (no state management libraries, direct wagmi hooks, minimal styling, copy-paste reuse)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS User Story 2 (authored NFTs)
- **User Story 1 (Phase 3)**: Depends on Setup only (no backend dependency for navigation/tabs)
- **User Story 2 (Phase 4)**: Depends on Foundational (Phase 2) completion - needs backend API
- **User Story 3 (Phase 5)**: Depends on Setup only (no backend dependency for blockchain reads)
- **User Story 4 (Phase 6)**: Depends on User Stories 1, 2, 3 completion
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Setup (Phase 1) - No dependencies on backend
- **User Story 2 (P1)**: Requires Foundational (Phase 2) backend API - BLOCKED until T011 complete
- **User Story 3 (P1)**: Can start after Setup (Phase 1) - No dependencies on backend (blockchain reads only)
- **User Story 4 (P2)**: Requires User Stories 1, 2, 3 complete - Refinement of existing functionality

### Within Each User Story

- **US1**: Tab navigation before content, route setup before header update
- **US2**: TypeScript interfaces → fetch function → useQuery hook → UI components → pagination
- **US3**: Wagmi hooks → balanceOf → tokenOfOwnerByIndex → UI components → pagination
- **US4**: Cache configuration → wallet change handling → testing

### Parallel Opportunities

**Phase 1 (Setup)**: All 3 tasks can run in parallel (env verification)

**Phase 2 (Foundational)**: T004, T005 (Pydantic models) can run in parallel before T006-T011

**User Story 1**:
- T012, T013, T014 (component files) can run in parallel
- T015-T019 (ProfilePage logic) sequential
- T020, T021 (copy UI) can run in parallel after T013 created

**User Story 2**:
- T027, T028 (TypeScript interfaces) can run in parallel
- T029-T032 (data fetching) sequential
- T033-T035 (NFTGrid component) can run in parallel with T027-T032
- T036-T043 (UI states) sequential after data fetching ready

**User Story 3**:
- T044, T045, T046 (imports) can run in parallel
- T047-T052 (wagmi hooks) sequential
- T053-T060 (UI states) sequential after hooks ready

**Phase 7 (Polish)**:
- T066, T067, T068, T069 (deletions) can run in parallel
- T070-T073 (validation) sequential
- T074 (styling) can run in parallel with T075 (code review)

---

## Parallel Example: User Story 2 - Authored NFTs

```bash
# Launch TypeScript interfaces together:
Task: "Create TokensResponse TypeScript interface in PromptAuthor.tsx"
Task: "Create TokenDTO TypeScript interface in PromptAuthor.tsx"

# After interfaces ready, create NFTGrid component in parallel with data fetching logic:
Task: "Create NFTGrid.tsx reusable component in frontend/src/components/"
Task: "Create fetchAuthoredTokens async function in PromptAuthor.tsx"
```

---

## Implementation Strategy

### MVP First (User Stories 1, 2, 3 Only - All P1)

1. Complete Phase 1: Setup (env configuration)
2. Complete Phase 2: Foundational (backend API endpoint - CRITICAL for US2)
3. Complete Phase 3: User Story 1 (navigation + tabs)
4. Complete Phase 4: User Story 2 (authored NFTs) OR Phase 5: User Story 3 (owned NFTs) - can run in parallel
5. **STOP and VALIDATE**: Test all P1 stories independently per quickstart.md
6. Deploy/demo MVP (P1 stories deliver all core value)

### Incremental Delivery

1. Setup + Foundational → Backend API ready
2. User Story 1 → Navigation working → Test independently
3. User Story 2 → Authored NFTs working → Test independently
4. User Story 3 → Owned NFTs working → Test independently (can run parallel with US2)
5. User Story 4 → Refinement of tab switching → Test independently
6. Polish → Code cleanup, validation, deployment

### Parallel Team Strategy

With 2 developers after Foundational phase complete:

1. Developer A: User Story 1 (T012-T026) + User Story 2 (T027-T043) - Prompt Author tab
2. Developer B: User Story 3 (T044-T060) - Collector tab
3. Both meet for User Story 4 (T061-T065) - Integration testing
4. Both complete Polish (T066-T075)

**Time estimate**: 2-3 days for MVP (all P1 stories)

---

## Notes

- [P] tasks = different files, no dependencies - safe to run in parallel
- [Story] label maps task to specific user story for traceability
- No automated tests required (constitution frontend standard - manual testing only)
- Each user story should be independently completable and testable
- Copy-paste from existing components is encouraged per constitution (no refactoring for MVP)
- Minimal styling only (basic Tailwind utilities, no decorative elements)
- OnchainKit handles NFT metadata fetching (no custom metadata service needed)
- State preservation across tab switches is out of scope for MVP (components unmount/remount)
