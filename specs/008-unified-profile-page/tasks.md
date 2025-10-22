# Tasks: Unified Profile Page with Author & Collector Tabs

**Input**: Design documents from `/specs/008-unified-profile-page/`
**Prerequisites**: plan.md (✅), spec.md (✅), research.md (✅), data-model.md (✅), contracts/ (✅)

**Tests**: Unit tests included for backend API endpoint. Manual testing for frontend (MVP approach).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions
- **GLISK Monorepo**:
  - Backend: `backend/src/glisk/`, `backend/tests/`
  - Frontend: `frontend/src/`, `frontend/tests/`
  - Contracts: `contracts/src/` (no changes needed)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Install dependencies and configure providers for thirdweb and OnchainKit integration

- [ ] T001 Install frontend dependencies: `cd frontend && npm install thirdweb @coinbase/onchainkit`
- [ ] T002 Add environment variables to `frontend/.env`: `VITE_THIRDWEB_CLIENT_ID` and `VITE_ONCHAINKIT_API_KEY`
- [ ] T003 Create thirdweb client configuration in `frontend/src/lib/thirdweb.ts`
- [ ] T004 Import OnchainKit styles in `frontend/src/main.tsx`: `import '@coinbase/onchainkit/styles.css'`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Backend API endpoint and repository method that User Stories 1 and 2 depend on

**⚠️ CRITICAL**: Backend API must be complete before frontend Author tab can display authored NFTs

### Backend Foundation

- [ ] T005 [P] Create Pydantic response models in `backend/src/glisk/api/routes/tokens.py`: `TokenResponse` (token_id, status, image_url, metadata_cid, created_at) and `AuthorTokensResponse` (tokens, total, page, limit)
- [ ] T006 [P] Add repository method `get_by_author_paginated(author_id: UUID, page: int, limit: int)` in `backend/src/glisk/repositories/token.py` with SQL query using LIMIT/OFFSET and ORDER BY created_at DESC
- [ ] T007 Create API endpoint `GET /api/authors/{wallet_address}/tokens` in `backend/src/glisk/api/routes/tokens.py` with wallet address normalization via Web3.to_checksum_address and pagination query params (page, limit)
- [ ] T008 Register tokens router in `backend/src/glisk/main.py`: `app.include_router(tokens.router, prefix="/api")`

### Backend Tests

- [ ] T009 [P] Write unit tests in `backend/tests/test_tokens_api.py` for: valid wallet with tokens (200), wallet without author (200 empty array), invalid address format (400), pagination bounds (empty array beyond pages), limit validation (422 for <1 or >100)
- [ ] T010 Run backend tests with `cd backend && TZ=America/Los_Angeles uv run pytest tests/test_tokens_api.py -v` and verify all pass

### Frontend Foundation

- [ ] T011 Add ThirdwebProvider wrapper in `frontend/src/main.tsx` (above existing WagmiConfig)
- [ ] T012 Add OnchainKitProvider wrapper in `frontend/src/main.tsx` with `apiKey` and `chain` props (baseSepolia)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Navigate to Unified Profile Page (Priority: P1) 🎯 MVP

**Goal**: Users can navigate from header to a unified `/profile` page with Author tab active by default, consolidating prompt management and X linking sections.

**Independent Test**: Connect wallet, click Profile button in header, verify navigation to `/profile?tab=author` and see consolidated Author tab content.

### Implementation for User Story 1

- [ ] T013 Create `frontend/src/pages/Profile.tsx` with basic component structure using `useSearchParams` hook from react-router-dom to read `?tab=` query parameter
- [ ] T014 [US1] Add tab navigation UI in `Profile.tsx`: two button controls for "Prompt Author" and "Collector" tabs that update URL query param via `setSearchParams({ tab })`
- [ ] T015 [US1] Add default tab logic in `Profile.tsx`: if no query param or invalid value, default to `?tab=author` and update URL
- [ ] T016 [US1] Create AuthorTabPanel component structure in `Profile.tsx` (or separate file) that will contain prompt management, X linking, and authored NFTs sections
- [ ] T017 [US1] Copy prompt management UI from `frontend/src/pages/CreatorDashboard.tsx` (textarea, save button, status indicators) into AuthorTabPanel
- [ ] T018 [US1] Copy X account linking UI from `frontend/src/pages/ProfileSettings.tsx` (link button, linked status display, OAuth flow) into AuthorTabPanel
- [ ] T019 [US1] Update `frontend/src/App.tsx`: add route `<Route path="/profile" element={<Profile />} />`
- [ ] T020 [US1] Update `frontend/src/components/Header.tsx`: replace "Creator Dashboard" and "Profile Settings" buttons with single "Profile" button that navigates to `/profile`
- [ ] T021 [US1] Add wallet connection check in `Profile.tsx`: if no wallet connected, show message "Please connect your wallet to view your profile"

**Checkpoint**: At this point, User Story 1 should be fully functional - navigation works, Author tab shows consolidated content, URL updates correctly

---

## Phase 4: User Story 2 - View Authored NFTs in Prompt Author Tab (Priority: P1) 🎯 MVP

**Goal**: Prompt Author tab displays a paginated list of NFTs where the connected wallet is the prompt author (fetched from backend API).

**Independent Test**: Connect wallet that has authored NFTs, navigate to Author tab, verify NFTs appear in grid with correct pagination (20 per page).

### Implementation for User Story 2

- [ ] T022 [US2] Create `AuthoredNFTsSection` component in `Profile.tsx` (or separate file) with state for NFT list, total count, current page, loading status
- [ ] T023 [US2] Add `useEffect` hook in `AuthoredNFTsSection` that watches `[address, currentPage]` and fetches from `GET /api/authors/{address}/tokens?page={page}&limit=20`
- [ ] T024 [US2] Implement NFT grid rendering in `AuthoredNFTsSection` using thirdweb `NFTProvider`, `NFTMedia`, and `NFTName` components for each authored token
- [ ] T025 [US2] Create `PaginationControls` component in `Profile.tsx` (or separate file) with Previous/Next buttons and page number display
- [ ] T026 [US2] Add pagination logic in `AuthoredNFTsSection`: calculate `totalPages = Math.ceil(total / 20)`, disable Previous on page 1, disable Next on last page, disable both during loading
- [ ] T027 [US2] Add error handling in `AuthoredNFTsSection`: catch fetch errors and display error message "Failed to load authored NFTs. Please try again."
- [ ] T028 [US2] Add empty state handling in `AuthoredNFTsSection`: when `tokens.length === 0`, show "No authored NFTs yet"
- [ ] T029 [US2] Integrate `AuthoredNFTsSection` into `AuthorTabPanel` below prompt management and X linking sections
- [ ] T030 [US2] Add wallet change detection: reset `currentPage` to 1 when `address` changes in `useEffect` dependency array

**Checkpoint**: At this point, User Story 2 should be fully functional - authored NFTs load from backend, pagination works, wallet changes refresh data

---

## Phase 5: User Story 3 - View Owned NFTs in Collector Tab (Priority: P1) 🎯 MVP

**Goal**: Collector tab displays a paginated list of NFTs owned by the connected wallet (fetched from blockchain via thirdweb).

**Independent Test**: Connect wallet that owns NFTs, switch to Collector tab, verify NFTs appear in grid with correct pagination (20 per page).

### Implementation for User Story 3

- [ ] T031 [US3] Create `CollectorTabPanel` component in `Profile.tsx` (or separate file) with state for current page and pagination controls
- [ ] T032 [US3] Add contract instance using thirdweb's `getContract`: pass `client`, `chain: defineChain(84532)` for Base Sepolia, and contract address from env/config
- [ ] T033 [US3] Add `useReadContract(getOwnedNFTs)` hook in `CollectorTabPanel` with contract and owner address (from wagmi `useAccount`)
- [ ] T034 [US3] Implement client-side pagination in `CollectorTabPanel`: calculate `totalPages = Math.ceil(allNFTs.length / 20)`, slice array for current page: `allNFTs.slice((currentPage - 1) * 20, currentPage * 20)`
- [ ] T035 [US3] Implement NFT grid rendering in `CollectorTabPanel` using thirdweb `NFTProvider`, `NFTMedia`, and `NFTName` components for each owned NFT
- [ ] T036 [US3] Reuse `PaginationControls` component from User Story 2 in `CollectorTabPanel` with appropriate state and handlers
- [ ] T037 [US3] Add loading state handling in `CollectorTabPanel`: show "Loading owned NFTs..." while `isLoading` is true from `useReadContract`
- [ ] T038 [US3] Add error handling in `CollectorTabPanel`: if `error` from `useReadContract`, show "Failed to load owned NFTs. Please check your connection and try again." with retry button
- [ ] T039 [US3] Add empty state handling in `CollectorTabPanel`: when `allNFTs.length === 0`, show "No NFTs owned yet"
- [ ] T040 [US3] Add wallet change detection in `CollectorTabPanel`: reset `currentPage` to 1 when `address` changes (thirdweb hook auto-refetches)
- [ ] T041 [US3] Add conditional rendering in `Profile.tsx`: render `CollectorTabPanel` when `activeTab === 'collector'`

**Checkpoint**: At this point, User Stories 1, 2, AND 3 should all work independently - navigation, authored NFTs, and owned NFTs all functional

---

## Phase 6: User Story 4 - Tab Switching Preserves State (Priority: P2)

**Goal**: Users can switch between tabs multiple times without losing pagination state or refetching data unnecessarily.

**Independent Test**: Navigate to page 2 on Author tab, switch to Collector tab, switch back, verify Author tab is still on page 2.

### Implementation for User Story 4

- [ ] T042 [US4] Refactor state management in `Profile.tsx`: create separate state objects for each tab's pagination (`authoredPagination` with currentPage/totalPages, `collectorPagination` with currentPage/totalPages)
- [ ] T043 [US4] Update `AuthoredNFTsSection` to use `authoredPagination.currentPage` and preserve state when tab switches (don't reset unless wallet changes)
- [ ] T044 [US4] Update `CollectorTabPanel` to use `collectorPagination.currentPage` and preserve state when tab switches (don't reset unless wallet changes)
- [ ] T045 [US4] Add data caching logic: store fetched NFT data in state outside the conditional render so switching tabs doesn't trigger refetch
- [ ] T046 [US4] Update wallet change handlers: when `address` changes, reset BOTH `authoredPagination.currentPage` and `collectorPagination.currentPage` to 1 and clear cached data

**Checkpoint**: All user stories should now be independently functional with enhanced UX for tab switching

---

## Phase 7: OnchainKit Transaction Integration (Enhancement)

**Purpose**: Improve minting UX by replacing raw wagmi calls with OnchainKit Transaction component

- [ ] T047 Import OnchainKit transaction components in `frontend/src/pages/CreatorMintPage.tsx`: `Transaction`, `TransactionButton`, `TransactionStatus`, `TransactionToast`
- [ ] T048 Replace `useWriteContract` and `useWaitForTransactionReceipt` hooks in `CreatorMintPage.tsx` with OnchainKit's `<Transaction>` component wrapper
- [ ] T049 Create `calls` array in `CreatorMintPage.tsx`: use `encodeFunctionData` from viem to encode `batchMint(address, promptText)` call
- [ ] T050 Replace mint button with `<TransactionButton />` component inside `<Transaction>` wrapper
- [ ] T051 Add `<TransactionStatus />` and `<TransactionToast />` components for status tracking and notifications
- [ ] T052 Add `onStatus` callback to `<Transaction>` to handle success state (log transaction hash, show success message)
- [ ] T053 Remove manual gas estimation and transaction receipt polling logic (OnchainKit handles automatically)

---

## Phase 8: Cleanup & Removal of Old Pages

**Purpose**: Remove deprecated pages after consolidation

- [ ] T054 [P] Delete `frontend/src/pages/CreatorDashboard.tsx` (functionality moved to Profile/AuthorTabPanel)
- [ ] T055 [P] Delete `frontend/src/pages/ProfileSettings.tsx` (functionality moved to Profile/AuthorTabPanel)
- [ ] T056 Remove routes from `frontend/src/App.tsx`: delete `<Route path="/creator-dashboard" ...>` and `<Route path="/profile-settings" ...>`
- [ ] T057 Verify no remaining imports or references to deleted files in the codebase (search for "CreatorDashboard" and "ProfileSettings")

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Final testing, validation, and refinement

- [ ] T058 [P] Verify minimal design implementation: no decorative CSS beyond basic Tailwind utilities, no animations, no loading skeletons (text only)
- [ ] T059 [P] Add basic Tailwind utility classes for spacing and layout (grid for NFTs, flex for tabs, padding/margins for sections)
- [ ] T060 Run through all acceptance scenarios from `spec.md` User Stories 1-4 manually
- [ ] T061 Test edge cases: invalid tab params (defaults to author), exactly 20 NFTs (no pagination), rapid tab switching (debounce/cancel in-flight requests if needed)
- [ ] T062 Test error scenarios: backend API down (Author tab error but prompt/X sections work), RPC unavailable (Collector tab error with retry), wallet disconnect mid-operation
- [ ] T063 Test wallet switching: verify data refreshes in active tab, pagination resets to page 1, no stale data shown
- [ ] T064 Verify TypeScript compilation with no errors: `cd frontend && npm run build`
- [ ] T065 Remove console.logs and debug statements from all frontend files
- [ ] T066 Test on multiple browsers: Chrome (primary), Safari (secondary), Firefox (secondary)
- [ ] T067 Test with different wallets: MetaMask, Coinbase Wallet (via RainbowKit)
- [ ] T068 Verify all success criteria from `spec.md` (SC-001 through SC-010): navigation speed, tab switching speed, load times, pagination accuracy, performance with 1000 NFTs
- [ ] T069 Run quickstart validation: follow `specs/008-unified-profile-page/quickstart.md` step-by-step to verify setup and implementation correctness

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS User Stories 1 and 2
- **User Story 1 (Phase 3)**: Depends on Foundational Phase 2 (T011, T012 for providers)
- **User Story 2 (Phase 4)**: Depends on Foundational Phase 2 (T005-T008 for backend API) AND User Story 1 (T016 for AuthorTabPanel structure)
- **User Story 3 (Phase 5)**: Depends on Foundational Phase 2 (T011 for ThirdwebProvider) AND User Story 1 (T013 for Profile.tsx structure)
- **User Story 4 (Phase 6)**: Depends on User Stories 2 and 3 completion
- **OnchainKit Integration (Phase 7)**: Depends on Foundational Phase 2 (T012 for OnchainKitProvider)
- **Cleanup (Phase 8)**: Depends on User Stories 1, 2, 3 completion (old functionality fully migrated)
- **Polish (Phase 9)**: Depends on all phases complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational Phase 2 - Independent navigation and tab structure
- **User Story 2 (P1)**: Requires backend API (Phase 2) and Author tab structure (US1 T016) - Can be tested independently once US1 provides tab container
- **User Story 3 (P1)**: Requires thirdweb provider (Phase 2) and Profile page structure (US1 T013) - Can be tested independently once US1 provides page container
- **User Story 4 (P2)**: Enhancement that builds on US2 and US3 - Requires both tabs functional

### Within Each User Story

- Backend tests (T009-T010) can run after backend implementation (T005-T008)
- Frontend provider setup (T011-T012) must complete before any thirdweb/OnchainKit components
- Tab structure (T013-T016) before tab content (T017-T021, T022-T030, T031-T041)
- NFT sections before pagination controls
- Error handling and empty states after core rendering logic

### Parallel Opportunities

- **Phase 1**: All setup tasks (T001-T004) can run in parallel
- **Phase 2 Backend**: T005 (models) and T006 (repository) can run in parallel
- **Phase 2 Tests**: T009 test writing can happen in parallel with implementation (TDD approach)
- **Phase 2 Frontend**: T011-T012 (provider setup) can run in parallel
- **Phase 3**: T017 (prompt UI copy) and T018 (X linking copy) can run in parallel after T016 (tab structure)
- **Phase 8**: T054-T055 (file deletions) can run in parallel
- **Phase 9**: T058-T059 (design verification) can run in parallel, browser/wallet testing (T066-T067) can run in parallel

---

## Parallel Example: Foundational Phase

```bash
# Backend - can work on models and repository in parallel:
Task T005: "Create Pydantic response models in backend/src/glisk/api/routes/tokens.py"
Task T006: "Add repository method get_by_author_paginated in backend/src/glisk/repositories/token.py"

# Frontend - provider setup can run in parallel:
Task T011: "Add ThirdwebProvider wrapper in frontend/src/main.tsx"
Task T012: "Add OnchainKitProvider wrapper in frontend/src/main.tsx"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 + 3 - All P1)

1. Complete Phase 1: Setup → Dependencies installed, env vars configured
2. Complete Phase 2: Foundational → Backend API working, providers configured
3. Complete Phase 3: User Story 1 → Navigation and tab structure working
4. Complete Phase 4: User Story 2 → Authored NFTs displaying with pagination
5. Complete Phase 5: User Story 3 → Owned NFTs displaying with pagination
6. **STOP and VALIDATE**: Test all three user stories independently
7. Complete Phase 8: Cleanup → Remove old pages
8. Complete Phase 9: Polish → Final testing and validation
9. Deploy/demo - MINIMAL PROTOTYPE COMPLETE ✅

### Incremental Delivery Option

If prioritization is needed:

1. Setup + Foundational → Foundation ready
2. User Story 1 only → Test navigation and tab switching → Deploy/Demo (basic consolidation working)
3. Add User Story 2 → Test authored NFTs → Deploy/Demo (author functionality complete)
4. Add User Story 3 → Test owned NFTs → Deploy/Demo (full dual-view working)
5. Add User Story 4 → Test state preservation → Deploy/Demo (enhanced UX)
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (critical path)
2. Once Foundational is done:
   - Developer A: User Story 1 (navigation and tab structure)
   - Developer B: Prepare User Story 2 implementation (review API contracts, prepare component structure)
   - Developer C: Prepare User Story 3 implementation (review thirdweb SDK, prepare component structure)
3. After User Story 1 provides page structure:
   - Developer B: Complete User Story 2 (authored NFTs section)
   - Developer C: Complete User Story 3 (owned NFTs section)
4. Stories integrate into unified profile page

---

## Notes

- [P] tasks = different files, no dependencies - safe to parallelize
- [Story] label (US1, US2, US3, US4) maps task to specific user story for traceability
- All three P1 user stories are required for MVP (navigation, authored NFTs, owned NFTs)
- User Story 4 (P2) is an enhancement - can be deferred if needed
- OnchainKit integration (Phase 7) is independent - can proceed in parallel with main profile page work
- Manual testing approach for frontend (constitution: MVP first, no test overhead)
- Backend tests included for API endpoint (standard practice for new endpoints)
- Minimal design enforced throughout (no CSS complexity, no decorative elements)
- Each checkpoint allows for independent validation and demo

---

## Total Task Count

- **Setup**: 4 tasks
- **Foundational**: 8 tasks (backend + tests + frontend providers)
- **User Story 1**: 9 tasks (navigation, tab structure, content consolidation)
- **User Story 2**: 9 tasks (authored NFTs display and pagination)
- **User Story 3**: 11 tasks (owned NFTs display and pagination)
- **User Story 4**: 5 tasks (state preservation enhancement)
- **OnchainKit Integration**: 7 tasks (minting UX improvement)
- **Cleanup**: 4 tasks (remove old pages)
- **Polish**: 12 tasks (final testing and validation)

**Grand Total**: 69 tasks

**Parallel Opportunities**: 14 tasks marked [P] for parallel execution
