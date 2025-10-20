# Tasks: Frontend Foundation with Creator Mint Page

**Input**: Design documents from `/specs/005-frontend-foundation-with/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md
**Feature Branch**: `005-frontend-foundation-with`

**Tests**: Manual testing only (automated tests out of scope for MVP)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions
- **Frontend**: `frontend/src/`, `frontend/public/`
- **Config**: `frontend/` root (package.json, tsconfig.json, vite.config.ts, etc.)
- **Nginx**: `nginx/frontend.conf`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, dependency installation, and basic configuration

- [x] T001 Initialize Vite project with React + TypeScript template at `frontend/` directory
- [x] T002 Install core dependencies: react, react-dom, vite
- [x] T003 [P] Install Web3 libraries: @rainbow-me/rainbowkit, @coinbase/onchainkit, wagmi, viem@2.x
- [x] T004 [P] Install routing library: react-router-dom
- [x] T005 [P] Install Tailwind CSS and PostCSS: tailwindcss, postcss, autoprefixer (Note: Using Tailwind v4)
- [x] T006 [P] Install @tanstack/react-query (required by wagmi)
- [x] T007 Initialize Tailwind CSS configuration: run `npx tailwindcss init -p` in `frontend/` (Note: Tailwind v4 uses different config)
- [x] T008 Initialize shadcn/ui: run `npx shadcn-ui@latest init` in `frontend/` (select TypeScript, Default style, Slate base color, CSS variables)
- [x] T009 [P] Add shadcn/ui Button component: run `npx shadcn-ui@latest add button`
- [x] T010 [P] Add shadcn/ui Input component: run `npx shadcn-ui@latest add input`
- [x] T011 [P] Add shadcn/ui Card component: run `npx shadcn-ui@latest add card`
- [x] T012 Configure Tailwind to scan all source files: update `frontend/tailwind.config.js` with content paths
- [x] T013 Update `frontend/src/index.css` with Tailwind directives (@tailwind base, components, utilities)
- [x] T014 Sync GliskNFT ABI to both backend and frontend: run `./sync-abi.sh` from repo root (creates `frontend/src/lib/glisk-nft-abi.json`)
- [x] T015 [P] Install ESLint and TypeScript ESLint: `@typescript-eslint/parser @typescript-eslint/eslint-plugin eslint`
- [x] T016 [P] Install Prettier: `prettier eslint-config-prettier`
- [x] T017 [P] Install Husky for git hooks: `husky lint-staged` (SKIPPED - not using Husky)
- [x] T018 Initialize ESLint config: create `frontend/.eslintrc.cjs` with TypeScript rules
- [x] T019 Create Prettier config: create `frontend/.prettierrc` with formatting rules
- [x] T020 Add type-check script to `frontend/package.json`: `"type-check": "tsc --noEmit"`
- [x] T021 Add lint script to `frontend/package.json`: `"lint": "eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0"`
- [x] T022 Add format script to `frontend/package.json`: `"format": "prettier --write \"src/**/*.{ts,tsx,css}\""`
- [x] T023 Initialize Husky: run `npx husky init` in `frontend/` (SKIPPED - not using Husky)
- [x] T024 Create pre-commit hook: add `frontend/.husky/pre-commit` with `npm run type-check && npm run lint && npm run format` (SKIPPED - not using Husky)
- [x] T025 Add lint-staged config to `frontend/package.json` for staged file checks (SKIPPED - not using Husky)

**Checkpoint**: Project initialized, all dependencies installed, shadcn/ui configured, quality checks enabled

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T026 Create environment configuration files: `frontend/.env.example` and `frontend/.env` with VITE_CONTRACT_ADDRESS and VITE_CHAIN_ID
- [x] T027 Create wagmi configuration file at `frontend/src/lib/wagmi.ts` with Base Sepolia chain and WalletConnect project ID
- [x] T028 Create contract constants file at `frontend/src/lib/contract.ts` with address, ABI import, and chain ID
- [x] T029 Update `frontend/src/main.tsx` to wrap app with WagmiProvider → QueryClientProvider → RainbowKitProvider
- [x] T030 Import RainbowKit styles in `frontend/src/main.tsx`: add `import '@rainbow-me/rainbowkit/styles.css'`
- [x] T031 Update `.gitignore` to exclude `frontend/.env` (ensure `.env.example` is tracked)

**Checkpoint**: Foundation ready - wagmi providers configured, environment setup complete, user story implementation can now begin

---

## Phase 3: User Story 1 - Connect Wallet and Access Creator Page (Priority: P1) 🎯 MVP

**Goal**: Users can visit `/{creatorAddress}` URLs, connect their Web3 wallet via RainbowKit, and see their connected address in the header. Establishes core infrastructure (routing, layout, wallet integration).

**Independent Test**: Visit a creator link, click "Connect Wallet", approve in wallet extension, see connected address in header, refresh page and verify wallet remains connected.

### Implementation for User Story 1

- [x] T032 [P] [US1] Create Header component at `frontend/src/components/Header.tsx` with RainbowKit ConnectButton
- [x] T033 [P] [US1] Create basic layout structure in `frontend/src/App.tsx` with BrowserRouter and Routes
- [x] T034 [US1] Add route for `/:creatorAddress` in `frontend/src/App.tsx` using react-router-dom
- [x] T035 [US1] Create CreatorMintPage component at `frontend/src/pages/CreatorMintPage.tsx` with basic layout (header + content)
- [x] T036 [US1] Extract `creatorAddress` from URL using `useParams()` hook in CreatorMintPage
- [x] T037 [US1] Display creator address in CreatorMintPage UI (e.g., "Minting for: {creatorAddress}")
- [x] T038 [US1] Use `useAccount()` hook to check wallet connection status in CreatorMintPage
- [x] T039 [US1] Show "Connect Wallet" prompt when wallet is disconnected (conditionally render based on `isConnected`)
- [x] T040 [US1] Add Header component to App.tsx layout so it appears on all pages
- [x] T041 [US1] Add basic Tailwind styling to Header (flex layout, padding, border-bottom)
- [x] T042 [US1] Add basic Tailwind styling to CreatorMintPage (container, padding, centered layout)

**Checkpoint**: At this point, User Story 1 should be fully functional - users can visit creator pages, connect wallets, see their address, and wallet persists on refresh.

---

## Phase 4: User Story 2 - Select Mint Quantity (Priority: P2)

**Goal**: Users with connected wallets can select how many NFTs to mint (1-10) using a quantity input with validation.

**Independent Test**: Connect wallet (from US1), interact with quantity selector, verify values constrain to 1-10 range, see quantity reflected in UI.

### Implementation for User Story 2

- [x] T043 [US2] Add `quantity` state to CreatorMintPage using `useState(1)`
- [x] T044 [US2] Create quantity input field in CreatorMintPage using shadcn/ui Input component
- [x] T045 [US2] Implement `handleQuantityChange` function with validation (clamp to 1-10, parseInt, handle NaN)
- [x] T046 [US2] Bind input value to `quantity` state and onChange to `handleQuantityChange`
- [x] T047 [US2] Add input validation attributes: type="number", min="1", max="10"
- [x] T048 [US2] Add label for quantity input with Tailwind styling (e.g., "Quantity (1-10):")
- [x] T049 [US2] Display current quantity value in UI to confirm state updates correctly

**Checkpoint**: At this point, User Stories 1 AND 2 should both work - wallet connection + quantity selection with validation

---

## Phase 5: User Story 3 - Mint NFTs from Creator Prompt (Priority: P3)

**Goal**: Users can trigger blockchain transactions to mint NFTs, approve in wallet, and see transaction status (pending/success/failure).

**Independent Test**: Connect wallet, select quantity, click Mint, approve transaction in wallet, see "Minting..." message, wait for confirmation, see "Success!" message. Test rejection and error scenarios.

### Implementation for User Story 3

- [x] T050 [US3] Add `useReadContract()` hook in CreatorMintPage to query `mintPrice` from contract
- [x] T051 [US3] Add `useWriteContract()` hook in CreatorMintPage to trigger mint transactions
- [x] T052 [US3] Add `useWaitForTransactionReceipt()` hook in CreatorMintPage to track transaction confirmation
- [x] T053 [US3] Create Mint button in CreatorMintPage using shadcn/ui Button component
- [x] T054 [US3] Implement `handleMint` function that calls `writeContract()` with contract address, ABI, `mint` function name, args [creatorAddress, quantity], value: mintPrice * BigInt(quantity)
- [x] T055 [US3] Disable Mint button when wallet is not connected (`!isConnected`)
- [x] T056 [US3] Disable Mint button during pending transaction (check `writeContract.isPending` or `receiptQuery.isLoading`)
- [x] T057 [US3] Add transaction status display logic (derive status from writeContract and receiptQuery states)
- [x] T058 [US3] Show "Please approve the transaction in your wallet" when `writeContract.isPending` is true
- [x] T059 [US3] Show "Minting... waiting for confirmation" when transaction hash exists and `receiptQuery.isLoading` is true
- [x] T060 [US3] Show "Success! NFTs minted." when `receiptQuery.isSuccess` is true
- [x] T061 [US3] Show "Transaction cancelled" when `writeContract.error` includes "User rejected" message
- [x] T062 [US3] Show error message when transaction fails (display `receiptQuery.error.message` or `writeContract.error.message`)
- [x] T063 [US3] Style status messages with Tailwind color utilities (blue for info, green for success, red for error, yellow for warning)
- [x] T064 [US3] Add network validation: check if `chain.id === 84532` (Base Sepolia), show "Switch to Base Sepolia" warning if wrong network

**Checkpoint**: All user stories should now be independently functional - complete wallet connection → quantity selection → minting flow with status feedback

**Bug Fixes Applied (Post-Implementation)**:
- Contract address validation: Added `isAddress()` check in `contract.ts` with clear error messages
- Creator address validation: Added `isAddress()` check before showing mint UI
- ABI structure fix: Extract `.abi` property from JSON (was: `gliskNFTAbi`, now: `gliskNFTAbiFile.abi`)
- Loading states: Added "Loading contract data..." UI while `mintPrice` loads
- Error handling: Show error if `mintPriceError` or contract address invalid
- Mint button disabled until `mintPrice` loaded successfully

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories, deployment setup, documentation

- [x] T065 [P] Add .env.production file with production contract address and chain ID
- [x] T066 [P] Create nginx configuration at `nginx/frontend.conf` with static file serving and SPA fallback routing
- [x] T067 [P] Update frontend README.md with setup instructions (reference quickstart.md)
- [x] T068 Test wallet connection persistence across page refreshes (clear localStorage to verify reconnection flow)
- [x] T069 Test edge case: disconnect wallet during pending transaction (verify UI handles gracefully)
- [x] T070 Test edge case: switch wallet/network while on page (verify UI updates)
- [x] T071 Test edge case: invalid creator address format in URL (verify page loads, transaction fails at contract level)
- [x] T072 Test with multiple browsers: Chrome + MetaMask, Firefox + MetaMask, Safari + Coinbase Wallet
- [x] T073 Build production bundle: run `npm run build` in `frontend/` and verify output in `dist/`
- [x] T074 Test production build locally by serving `frontend/dist/` with a simple HTTP server
- [x] T075 [P] Code cleanup: remove unused imports, console.logs, commented code
- [x] T076 [P] Add code comments to complex logic (transaction status derivation, quantity validation)
- [x] T077 Verify all Tailwind classes are basic utilities (no gradients, animations, custom plugins)
- [x] T078 Run through quickstart.md validation checklist (all 8 test scenarios)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3, 4, 5)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories. This is the MVP.
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Builds on US1 (requires wallet connection), but quantity selector is independent
- **User Story 3 (P3)**: Depends on US1 (wallet connection) and US2 (quantity input) - Uses both to trigger mint transactions

### Within Each User Story

- **US1**: Header and CreatorMintPage can be developed in parallel (T021, T022 marked [P]), then integrated (T023-T031)
- **US2**: All tasks sequential (build on quantity state)
- **US3**: Status display logic can be developed incrementally as transaction hooks are added

### Parallel Opportunities

- **Setup (Phase 1)**: T003, T004, T005, T006 (install dependencies) can run in parallel
- **Setup (Phase 1)**: T009, T010, T011 (add shadcn/ui components) can run in parallel after T008
- **Foundational (Phase 2)**: T016, T017 (config files) can run in parallel
- **US1 (Phase 3)**: T021, T022 (Header and App.tsx) can run in parallel
- **Polish (Phase 6)**: T054, T055, T056, T064, T065, T066 (documentation, cleanup, configs) can run in parallel

---

## Parallel Example: Setup Phase

```bash
# Launch all dependency installs together:
npm install @rainbow-me/rainbowkit @coinbase/onchainkit wagmi viem@2.x &
npm install react-router-dom &
npm install -D tailwindcss postcss autoprefixer &
npm install @tanstack/react-query &
wait

# Launch all shadcn/ui component additions together (after init):
npx shadcn-ui@latest add button &
npx shadcn-ui@latest add input &
npx shadcn-ui@latest add card &
wait
```

---

## Parallel Example: User Story 1

```bash
# Launch Header and App.tsx skeleton in parallel:
Task T021: "Create Header component at frontend/src/components/Header.tsx"
Task T022: "Create basic layout structure in frontend/src/App.tsx"
# Then integrate sequentially (T023-T031)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T014)
2. Complete Phase 2: Foundational (T015-T020) - CRITICAL - blocks all stories
3. Complete Phase 3: User Story 1 (T021-T031)
4. **STOP and VALIDATE**: Test US1 independently
   - Can visit creator pages?
   - Can connect wallet?
   - Address shown in header?
   - Wallet persists on refresh?
5. Deploy/demo if ready (US1 = foundation for all Web3 features)

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 (T021-T031) → Test independently → Deploy/Demo (MVP! Wallet connection works)
3. Add User Story 2 (T032-T038) → Test independently → Deploy/Demo (quantity selection works)
4. Add User Story 3 (T039-T053) → Test independently → Deploy/Demo (full minting flow works)
5. Add Polish (T054-T067) → Final testing → Production deployment

Each story adds value without breaking previous stories.

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done (T020 complete):
   - Developer A: User Story 1 (T021-T031) - wallet connection
   - Developer B: User Story 2 (T032-T038) - quantity selector (depends on US1 wallet state, but can develop in parallel)
   - Developer C: Polish tasks (T054-T056, T064-T066) - configs, docs, nginx
3. After US1 and US2 complete:
   - Developer A or B: User Story 3 (T039-T053) - minting flow (requires US1 + US2)
4. Final integration testing together (T057-T067)

---

## Task Count Summary

- **Total Tasks**: 78
- **Phase 1 (Setup)**: 25 tasks (includes quality checks: ESLint, Prettier, Husky, type-check)
- **Phase 2 (Foundational)**: 6 tasks (CRITICAL - blocks all stories)
- **Phase 3 (US1 - Wallet Connection)**: 11 tasks 🎯 MVP
- **Phase 4 (US2 - Quantity Selection)**: 7 tasks
- **Phase 5 (US3 - Minting Flow)**: 15 tasks
- **Phase 6 (Polish)**: 14 tasks

### Parallel Opportunities Identified

- **Setup**: 15 parallel tasks (T003-T006, T009-T011, T015-T017)
- **Foundational**: 2 parallel tasks (T027-T028)
- **US1**: 2 parallel tasks (T032-T033)
- **Polish**: 6 parallel tasks (T065-T067, T075-T076)

**Total parallel opportunities**: 25 tasks (32% of all tasks)

### Independent Test Criteria

- **US1 (MVP)**: Visit `/{address}`, connect wallet, see address in header, refresh → wallet persists
- **US2**: After US1, select quantity (1-10), verify input validation, see value in UI
- **US3**: After US1+US2, click Mint, approve in wallet, see status messages (pending → success/error)

### Suggested MVP Scope

**MVP = User Story 1 only** (T001-T042):
- Project setup complete (including quality checks)
- Wallet connection working
- Creator pages accessible
- ESLint, Prettier, pre-commit hooks configured
- ~42 tasks, estimated 1.5-2 days

This provides the foundation for all Web3 features with quality assurance and can be deployed/demoed independently.

---

## Notes

- [P] tasks = different files, no dependencies, can run in parallel
- [Story] label maps task to specific user story (US1, US2, US3) for traceability
- No automated tests (manual testing per quickstart.md)
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Contract price handling is simplified for MVP (can query later per user requirement)
- All styling uses basic Tailwind utilities (no custom CSS, gradients, or animations)
- Base Sepolia only (no multi-chain support)
- No backend integration (direct contract calls via wagmi)

---

## Reference Documentation

- **Feature Spec**: `specs/005-frontend-foundation-with/spec.md`
- **Implementation Plan**: `specs/005-frontend-foundation-with/plan.md`
- **Research Notes**: `specs/005-frontend-foundation-with/research.md`
- **Data Model**: `specs/005-frontend-foundation-with/data-model.md`
- **Quickstart Guide**: `specs/005-frontend-foundation-with/quickstart.md`
- **Contract ABI**: `backend/src/glisk/contracts/GliskNFT.json`
- **Deployed Contract**: `0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0` (Base Sepolia)
