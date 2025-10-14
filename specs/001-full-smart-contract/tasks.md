# Tasks: GLISK Smart Contract System

**Feature**: 001-full-smart-contract
**Branch**: `001-full-smart-contract`
**Input**: Design documents from `/specs/001-full-smart-contract/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/IGliskNFT.sol

**Tests**: This feature includes comprehensive testing (unit, integration, fuzz, invariant) as documented in research.md and quickstart.md.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story. Smart contract features will be built incrementally with testing at each phase.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Project Infrastructure) ✅

**Purpose**: Initialize Foundry project structure and core dependencies

- [X] T001 Initialize Foundry project in `contracts/` with forge, anvil, and cast
- [X] T002 [P] Install OpenZeppelin contracts v5.0.0 (`forge install OpenZeppelin/openzeppelin-contracts@v5.0.0`)
- [X] T003 [P] Configure `contracts/foundry.toml` with Solidity 0.8.20, optimizer (200 runs), Base RPC endpoints
- [X] T004 [P] Create `contracts/.env.example` with environment variable template (RPC URLs, private key, API keys, placeholder URI, initial price)
- [X] T005 [P] Setup `contracts/remappings.txt` for OpenZeppelin imports (if not auto-generated)
- [X] T006 Create directory structure: `contracts/src/`, `contracts/test/unit/`, `contracts/test/integration/`, `contracts/script/`

**Checkpoint**: Foundry project initialized, dependencies installed, configuration ready ✅

---

## Phase 2: Foundational (Core Contract Structure) ✅

**Purpose**: Build the base GliskNFT contract skeleton with inherited contracts and state variables. This MUST be complete before implementing any user story features.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T007 Create `contracts/src/GliskNFT.sol` with contract declaration inheriting from ERC721, AccessControl, ReentrancyGuard, ERC2981
- [X] T008 [US-FOUNDATION] Implement constructor with parameters (name, symbol, placeholderURI, initialMintPrice) and DEFAULT_ADMIN_ROLE setup
- [X] T009 [US-FOUNDATION] Define state variables: `_nextTokenId`, `mintPrice`, `treasuryBalance`, `_placeholderURI`, `seasonEnded`, `seasonEndTime`, `SWEEP_PROTECTION_PERIOD`, `MAX_BATCH_SIZE`
- [X] T010 [P] [US-FOUNDATION] Define mappings: `tokenPromptAuthor`, `_tokenURIs`, `_revealed`, `authorClaimable`
- [X] T011 [P] [US-FOUNDATION] Define constants: `KEEPER_ROLE`, `SWEEP_PROTECTION_PERIOD = 14 days`, `MAX_BATCH_SIZE = 50`
- [X] T012 [P] [US-FOUNDATION] Define custom errors: `InvalidQuantity()`, `ExceedsMaxBatchSize()`, `InsufficientPayment()`, `MintingDisabled()`, `SeasonAlreadyEnded()`, `SweepProtectionActive()`, `SeasonNotEnded()`, `NoBalance()`, `AlreadyRevealed()`, `LengthMismatch()`, `TransferFailed()`
- [X] T013 [P] [US-FOUNDATION] Define all events per IGliskNFT.sol interface
- [X] T014 [US-FOUNDATION] Implement `supportsInterface()` override for ERC721, ERC2981, and AccessControl
- [X] T015 [US-FOUNDATION] Implement `receive()` function to accept direct ETH payments to treasury

**Checkpoint**: Foundation contract structure complete with all state variables, errors, events, and base overrides - ready for feature implementation ✅

---

## Phase 3: User Story 1 - Mint Blind Box NFT (Priority: P1) 🎯 MVP ✅

**Goal**: Users can mint surprise NFTs by selecting a prompt author, specifying quantity, and paying the total price

**Independent Test**: User connects wallet, selects a prompt author, specifies quantity (1 or more), pays the mint price (price × quantity), receives NFT tokens. Author's claimable balance increases by 50% of payment. Treasury receives 50%. Can be fully tested without any other features working.

### Tests for User Story 1

**NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T016 [P] [US1] Create `contracts/test/unit/GliskNFT.Minting.t.sol` with test setup (deploy contract, fund test accounts)
- [X] T017 [P] [US1] Write test: `testMintSingleNFT()` - Mint 1 NFT with exact payment, verify token ownership, author balance, treasury balance
- [X] T018 [P] [US1] Write test: `testMintBatchNFTs()` - Mint 5 NFTs in batch, verify sequential token IDs, payment split
- [X] T019 [P] [US1] Write test: `testMintWithOverpayment()` - Mint with excess ETH, verify overpayment goes to treasury
- [X] T020 [P] [US1] Write test: `testMintRevertsInsufficientPayment()` - Mint with underpayment reverts
- [X] T021 [P] [US1] Write test: `testMintRevertsZeroQuantity()` - Mint with quantity 0 reverts
- [X] T022 [P] [US1] Write test: `testMintRevertsExceedsMaxBatch()` - Mint with quantity 51 reverts
- [X] T023 [P] [US1] Write test: `testConcurrentMintsUniqueTokenIDs()` - Multiple users mint simultaneously, verify no token ID collisions
- [X] T024 [P] [US1] Write test: `testPromptAuthorAssociation()` - Verify prompt author address is stored correctly for each token in batch

### Implementation for User Story 1

- [X] T025 [US1] Implement `mint(address promptAuthor, uint256 quantity)` function in `contracts/src/GliskNFT.sol`:
  - Validate quantity (> 0 and <= MAX_BATCH_SIZE)
  - Validate payment (msg.value >= mintPrice × quantity)
  - Check season not ended
  - Calculate payment split (50/50 base, overpayment to treasury)
  - Update authorClaimable and treasuryBalance
  - Loop mint tokens with _safeMint() and store promptAuthor
  - Emit BatchMinted event
  - Add nonReentrant modifier
- [X] T026 [US1] Run all User Story 1 tests and verify they pass
- [X] T027 [US1] Add NatSpec comments to mint() function

**Checkpoint**: At this point, User Story 1 (minting) should be fully functional and testable independently ✅

---

## Phase 4: User Story 2 - Prompt Author Earnings and Claims (Priority: P1) 🎯 MVP ✅

**Goal**: Prompt authors earn 50% of each mint from their prompts and can claim all accumulated rewards at any time

**Independent Test**: After multiple mints from an author's collection, the author can withdraw all accumulated rewards to their wallet. Can be tested independently by minting, checking balance, and claiming.

### Tests for User Story 2

- [X] T028 [P] [US2] Create `contracts/test/unit/GliskNFT.Rewards.t.sol` with test setup
- [X] T029 [P] [US2] Write test: `testAuthorBalanceAfterMint()` - Verify author claimable balance is 50% of mint payment
- [X] T030 [P] [US2] Write test: `testClaimAuthorRewards()` - Author claims rewards, balance transfers and resets to zero
- [X] T031 [P] [US2] Write test: `testClaimWithZeroBalance()` - Claim with zero balance succeeds without revert
- [X] T032 [P] [US2] Write test: `testMultipleMintsAccumulate()` - Multiple mints to same author accumulate correctly
- [X] T033 [P] [US2] Write test: `testClaimTransferFails()` - Handle transfer failure gracefully (test with contract that rejects ETH)

### Implementation for User Story 2

- [X] T034 [US2] Implement `claimAuthorRewards()` function in `contracts/src/GliskNFT.sol`:
  - Read authorClaimable[msg.sender]
  - Update state to zero before transfer
  - Transfer ETH using call{value}
  - Require success
  - Emit AuthorClaimed event
  - Add nonReentrant modifier
- [X] T035 [US2] Implement view function `authorClaimable(address)` (public mapping already provides this)
- [X] T036 [US2] Run all User Story 2 tests and verify they pass
- [X] T037 [US2] Add NatSpec comments to claimAuthorRewards() function

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently (mint + claim) ✅

---

## Phase 5: User Story 8 - NFT Reveal and Metadata Update (Priority: P1) 🎯 MVP ✅

**Goal**: NFTs start with a placeholder image and are permanently revealed after off-chain image generation by updating their metadata URIs once

**Independent Test**: Newly minted NFTs show placeholder metadata. Owner can update placeholder URI. Owner or Keeper can batch reveal tokens by setting their URIs. Once revealed, a token's URI cannot be changed again.

### Tests for User Story 8

- [X] T038 [P] [US8] Create `contracts/test/unit/GliskNFT.Reveal.t.sol` with test setup
- [X] T039 [P] [US8] Write test: `testTokenURIUnrevealed()` - New token returns placeholder URI
- [X] T040 [P] [US8] Write test: `testUpdatePlaceholderURI()` - Owner updates placeholder, unrevealed tokens reflect change
- [X] T041 [P] [US8] Write test: `testRevealTokens()` - Owner/Keeper reveals batch of tokens with unique URIs
- [X] T042 [P] [US8] Write test: `testRevealedTokenImmutable()` - Attempting to re-reveal token reverts
- [X] T043 [P] [US8] Write test: `testRevealLengthMismatch()` - Mismatched array lengths revert
- [X] T044 [P] [US8] Write test: `testIsRevealed()` - isRevealed() returns correct status
- [X] T045 [P] [US8] Write test: `testKeeperCanReveal()` - Keeper role can reveal tokens

### Implementation for User Story 8

- [X] T046 [US8] Override `tokenURI(uint256)` function in `contracts/src/GliskNFT.sol`:
  - Check token exists (_requireOwned)
  - If revealed, return _tokenURIs[tokenId]
  - Else return _placeholderURI
- [X] T047 [US8] Implement `setPlaceholderURI(string)` function:
  - Require DEFAULT_ADMIN_ROLE
  - Update _placeholderURI
  - Emit PlaceholderURIUpdated event
- [X] T048 [US8] Implement `revealTokens(uint256[] calldata, string[] calldata)` function:
  - Require DEFAULT_ADMIN_ROLE or KEEPER_ROLE
  - Validate array lengths match
  - Loop through tokens
  - Check not already revealed
  - Set _tokenURIs and _revealed[tokenId] = true
  - Emit TokensRevealed event
- [X] T049 [US8] Implement `isRevealed(uint256)` view function
- [X] T050 [US8] Implement `tokenPromptAuthor(uint256)` view function (public mapping already provides this)
- [X] T051 [US8] Run all User Story 8 tests and verify they pass
- [X] T052 [US8] Add NatSpec comments to all reveal functions

**Checkpoint**: At this point, User Stories 1, 2, AND 8 should work independently (mint + claim + reveal) ✅

---

## Phase 6: User Story 5 - Treasury Management (Priority: P3) ✅

**Goal**: Treasury funds accumulate from mint fees (50% of each mint) and direct payments, with Owner able to withdraw all treasury funds for platform operations

**Independent Test**: Treasury balance increases from mints and direct transfers. Owner can withdraw all treasury funds. Unauthorized addresses cannot withdraw.

### Tests for User Story 5

- [X] T053 [P] [US5] Create `contracts/test/unit/GliskNFT.Treasury.t.sol` with test setup
- [X] T054 [P] [US5] Write test: `testTreasuryAccumulatesFromMints()` - Treasury balance increases by 50% per mint
- [X] T055 [P] [US5] Write test: `testDirectPaymentToTreasury()` - Send ETH directly to contract, verify treasury balance increases
- [X] T056 [P] [US5] Write test: `testWithdrawTreasury()` - Owner withdraws all treasury funds
- [X] T057 [P] [US5] Write test: `testWithdrawRevertsUnauthorized()` - Non-owner cannot withdraw
- [X] T058 [P] [US5] Write test: `testWithdrawRevertsNoBalance()` - Withdraw with zero balance reverts

### Implementation for User Story 5

- [X] T059 [US5] Implement `withdrawTreasury()` function in `contracts/src/GliskNFT.sol`:
  - Require DEFAULT_ADMIN_ROLE
  - Check treasuryBalance > 0
  - Store amount, update state to zero
  - Transfer ETH using call{value}
  - Require success
  - Emit TreasuryWithdrawn event
  - Add nonReentrant modifier
- [X] T060 [US5] Verify `receive()` function already implemented (from T015) emits DirectPaymentReceived event
- [X] T061 [US5] Implement view function `treasuryBalance()` (public variable already provides this)
- [X] T062 [US5] Run all User Story 5 tests and verify they pass
- [X] T063 [US5] Add NatSpec comments to withdrawTreasury()

**Checkpoint**: Treasury management complete and testable ✅

---

## Phase 7: User Story 3 - Dynamic Pricing Management (Priority: P2) ✅

**Goal**: Authorized roles (Owner or Keeper) can adjust the mint price in response to ETH volatility

**Independent Test**: Owner or Keeper can update the mint price, and subsequent mints use the new price. Unauthorized addresses cannot update price.

### Tests for User Story 3

- [X] T064 [P] [US3] Create `contracts/test/unit/GliskNFT.Pricing.t.sol` with test setup
- [X] T065 [P] [US3] Write test: `testOwnerUpdatesMintPrice()` - Owner updates price, subsequent mints use new price
- [X] T066 [P] [US3] Write test: `testKeeperUpdatesMintPrice()` - Keeper updates price successfully
- [X] T067 [P] [US3] Write test: `testUnauthorizedCannotUpdatePrice()` - Non-owner/keeper cannot update
- [X] T068 [P] [US3] Write test: `testPriceUpdateDoesNotAffectPastMints()` - Previous mints remain at old price split

### Implementation for User Story 3

- [X] T069 [US3] Implement `setMintPrice(uint256)` function in `contracts/src/GliskNFT.sol`:
  - Require DEFAULT_ADMIN_ROLE or KEEPER_ROLE
  - Store old price
  - Update mintPrice
  - Emit MintPriceUpdated event
- [X] T070 [US3] Implement view function `mintPrice()` (public variable already provides this)
- [X] T071 [US3] Run all User Story 3 tests and verify they pass
- [X] T072 [US3] Add NatSpec comments to setMintPrice()

**Checkpoint**: Pricing management complete ✅

---

## Phase 8: User Story 6 - Role-Based Access Control (Priority: P2) ✅

**Goal**: System implements hierarchical role-based access for different operations: Owner (full control) and Keeper (limited operations)

**Independent Test**: Owner can grant/revoke Keeper role. Keeper can update URIs and prices but cannot withdraw funds or manage seasons. Owner can perform all operations.

### Tests for User Story 6

- [X] T073 [P] [US6] Create `contracts/test/unit/GliskNFT.Access.t.sol` with test setup
- [X] T074 [P] [US6] Write test: `testOwnerGrantsKeeperRole()` - Owner grants KEEPER_ROLE to address
- [X] T075 [P] [US6] Write test: `testKeeperCanUpdateURIs()` - Keeper can call revealTokens()
- [X] T076 [P] [US6] Write test: `testKeeperCanUpdatePrice()` - Keeper can call setMintPrice()
- [X] T077 [P] [US6] Write test: `testKeeperCannotWithdrawTreasury()` - Keeper cannot call withdrawTreasury()
- [X] T078 [P] [US6] Write test: `testKeeperCannotEndSeason()` - Keeper cannot call endSeason()
- [X] T079 [P] [US6] Write test: `testOwnerRevokesKeeperRole()` - Owner revokes KEEPER_ROLE
- [X] T080 [P] [US6] Write test: `testOwnerHasAllPermissions()` - Owner can perform all operations

### Implementation for User Story 6

- [X] T081 [US6] Verify KEEPER_ROLE constant is defined (from T011)
- [X] T082 [US6] Verify constructor grants DEFAULT_ADMIN_ROLE to deployer (from T008)
- [X] T083 [US6] Add role checks to existing functions (already done via onlyRole modifiers in previous phases)
- [X] T084 [US6] Run all User Story 6 tests and verify they pass
- [X] T085 [US6] Document role hierarchy in contract comments

**Checkpoint**: Role-based access control verified and tested ✅

---

## Phase 9: User Story 4 - Season End and Unclaimed Rewards (Priority: P2) ✅

**Goal**: Owner can end a season, which stops all new minting and starts a 2-week countdown, giving prompt authors time to claim rewards before unclaimed funds return to treasury

**Independent Test**: Owner triggers seasonEnd which immediately stops minting and starts 2-week countdown. During countdown, authors can still claim but minting is disabled. After countdown expires, Owner can sweep unclaimed rewards to treasury.

### Tests for User Story 4

- [X] T086 [P] [US4] Create `contracts/test/unit/GliskNFT.Season.t.sol` with test setup
- [X] T087 [P] [US4] Write test: `testEndSeason()` - Owner ends season, minting stops, countdown starts
- [X] T088 [P] [US4] Write test: `testMintRevertsAfterSeasonEnd()` - Mint attempt after seasonEnd reverts
- [X] T089 [P] [US4] Write test: `testClaimDuringCountdown()` - Authors can claim during countdown period
- [X] T090 [P] [US4] Write test: `testSweepAfterCountdown()` - Owner sweeps unclaimed rewards after 2 weeks
- [X] T091 [P] [US4] Write test: `testSweepRevertsBeforeCountdown()` - Sweep before countdown expires reverts
- [X] T092 [P] [US4] Write test: `testSweepRevertsSeasonNotEnded()` - Sweep without seasonEnd reverts
- [X] T093 [P] [US4] Write test: `testSeasonEndRevertsIfAlreadyEnded()` - Cannot end season twice
- [X] T094 [P] [US4] Write test: `testSweepMultipleAuthors()` - Sweep batch of authors correctly

### Implementation for User Story 4

- [X] T095 [US4] Implement `endSeason()` function in `contracts/src/GliskNFT.sol`:
  - Require DEFAULT_ADMIN_ROLE
  - Check !seasonEnded
  - Set seasonEnded = true
  - Set seasonEndTime = block.timestamp
  - Emit SeasonEnded event
- [X] T096 [US4] Implement `sweepUnclaimedRewards(address[] calldata authors)` function:
  - Require DEFAULT_ADMIN_ROLE
  - Check seasonEnded == true
  - Check block.timestamp >= seasonEndTime + SWEEP_PROTECTION_PERIOD
  - Loop through authors array
  - For each: read authorClaimable, reset to zero, accumulate total
  - Add total to treasuryBalance
  - Emit UnclaimedRewardsSwept event
- [X] T097 [US4] Add seasonEnded check to mint() function (revert if true)
- [X] T098 [US4] Implement view functions: `seasonEnded()`, `seasonEndTime()`, `SWEEP_PROTECTION_PERIOD()` (public variables already provide these)
- [X] T099 [US4] Run all User Story 4 tests and verify they pass
- [X] T100 [US4] Add NatSpec comments to endSeason() and sweepUnclaimedRewards()

**Checkpoint**: Season lifecycle management complete ✅

---

## Phase 10: User Story 7 - Secondary Sales Royalties (Priority: P3) ✅

**Goal**: NFTs support marketplace royalties where secondary sales pay a 2.5% royalty fee that goes entirely to the treasury

**Independent Test**: NFT contract exposes royalty information. When queried for any token's royalty, it returns 2.5% with treasury as the recipient.

### Tests for User Story 7

- [X] T101 [P] [US7] Create `contracts/test/unit/GliskNFT.Royalty.t.sol` with test setup
- [X] T102 [P] [US7] Write test: `testDefaultRoyaltyInfo()` - Query royaltyInfo() returns 2.5% and treasury address
- [X] T103 [P] [US7] Write test: `testOwnerUpdatesRoyalty()` - Owner updates royalty percentage and receiver
- [X] T104 [P] [US7] Write test: `testSupportsERC2981Interface()` - Contract supports ERC2981 interface
- [X] T105 [P] [US7] Write test: `testRoyaltyCalculation()` - Verify royalty amount calculation for various sale prices

### Implementation for User Story 7

- [X] T106 [US7] Update constructor in `contracts/src/GliskNFT.sol` to call `_setDefaultRoyalty(treasuryAddress, 250)` (250 basis points = 2.5%)
- [X] T107 [US7] Implement `setDefaultRoyalty(address receiver, uint96 feeNumerator)` function:
  - Require DEFAULT_ADMIN_ROLE
  - Call _setDefaultRoyalty()
  - Emit RoyaltyUpdated event
- [X] T108 [US7] Verify `supportsInterface()` includes ERC2981 (already done in T014)
- [X] T109 [US7] Run all User Story 7 tests and verify they pass
- [X] T110 [US7] Add NatSpec comments to setDefaultRoyalty()

**Checkpoint**: Royalty support complete ✅

---

## Phase 11: Integration Testing ✅

**Purpose**: Test end-to-end user journeys across multiple user stories

- [X] T111 [P] Create `contracts/test/integration/GliskNFT.integration.t.sol` with comprehensive test setup
- [X] T112 [P] Write integration test: `testCompleteUserJourney()` - User mints, author claims, owner reveals, season ends, sweep
- [X] T113 [P] Write integration test: `testMultipleUsersConcurrent()` - Multiple users mint/claim/interact simultaneously
- [X] T114 [P] Write integration test: `testPriceUpdateMidSeason()` - Price changes during active minting
- [X] T115 [P] Write integration test: `testSeasonLifecycle()` - Complete season from mint to sweep
- [X] T116 [P] Write integration test: `testRoleManagementWorkflow()` - Owner grants keeper, keeper operates, owner revokes
- [X] T117 Run all integration tests and verify they pass

**Checkpoint**: All integration tests passing ✅

---

## Phase 12: Advanced Testing (Fuzz & Invariant) ✅

**Purpose**: Ensure contract security and correctness under edge cases

- [X] T118 [P] Create `contracts/test/fuzz/GliskNFT.fuzz.t.sol` for fuzz testing
- [X] T119 [P] Write fuzz test: `testFuzzMintQuantity()` - Fuzz mint quantity and payment amounts
- [X] T120 [P] Write fuzz test: `testFuzzPaymentDistribution()` - Verify 50/50 split with various amounts
- [X] T121 [P] Write fuzz test: `testFuzzBatchReveal()` - Fuzz batch sizes and URI formats
- [X] T122 [P] Create `contracts/test/invariant/GliskNFT.invariant.t.sol` for invariant testing
- [X] T123 [P] Write invariant test: Balance conservation - contract.balance == treasuryBalance + sum(authorClaimable)
- [X] T124 [P] Write invariant test: Token ID uniqueness - no duplicate token IDs
- [X] T125 [P] Write invariant test: Reveal immutability - revealed tokens remain revealed
- [X] T126 Run all fuzz and invariant tests with high iteration counts (--fuzz-runs 5000)

**Checkpoint**: Advanced testing complete, security properties verified ✅

---

## Phase 13: Deployment Infrastructure ✅

**Purpose**: Create deployment scripts and verification tools

- [X] T127 [P] Create `contracts/script/Deploy.s.sol` Foundry deployment script:
  - Read environment variables (PRIVATE_KEY, PLACEHOLDER_URI, INITIAL_MINT_PRICE)
  - Deploy GliskNFT with constructor parameters
  - Log deployed address
  - Save deployment artifacts
- [X] T128 [P] Create `contracts/script/Verify.s.sol` for contract verification on Basescan
- [X] T129 [P] Update `contracts/.env.example` with all required variables
- [X] T130 Test deployment script on local Anvil chain
- [ ] T131 Test deployment script on Base Sepolia testnet (requires external network)
- [ ] T132 Verify contract on Base Sepolia explorer (requires external network)

**Checkpoint**: Deployment infrastructure ready for mainnet (local testing complete) ✅

---

## Phase 14: Documentation & Polish ✅

**Purpose**: Final documentation and code quality improvements

- [X] T133 [P] Add comprehensive NatSpec comments to all public/external functions in `contracts/src/GliskNFT.sol`
- [X] T134 [P] Create `contracts/README.md` with project overview, setup instructions, and deployment guide
- [X] T135 [P] Generate ABI export: `forge inspect GliskNFT abi > abi/GliskNFT.json`
- [X] T136 [P] Run gas report: `forge test --gas-report` and document gas costs
- [X] T137 [P] Run Slither static analysis: `slither contracts/src/GliskNFT.sol` and address findings (Complete - 0 actionable issues found)
- [X] T138 Format all Solidity code: `forge fmt`
- [X] T139 Generate coverage report: `forge coverage` and verify >95% coverage (achieved 100% on GliskNFT.sol)
- [ ] T140 Review and update quickstart.md with actual deployed contract details (optional - quickstart already comprehensive)
- [X] T141 Create deployment checklist based on quickstart.md (included in README.md)

**Checkpoint**: Documentation complete, ready for audit/deployment ✅

---

## Phase 15: ERC20 Safety Mechanism (Edge Case) ✅

**Purpose**: Add safety mechanism for accidentally sent ERC20 tokens

- [X] T142 Create `contracts/test/unit/GliskNFT.ERC20Recovery.t.sol` with test setup
- [X] T143 [P] Write test: `testRecoverERC20Tokens()` - Owner can withdraw ERC20 tokens
- [X] T144 [P] Write test: `testUnauthorizedCannotRecoverERC20()` - Non-owner cannot withdraw
- [X] T145 Implement `recoverERC20(address tokenAddress, uint256 amount)` function in `contracts/src/GliskNFT.sol`:
  - Require DEFAULT_ADMIN_ROLE
  - Transfer ERC20 tokens to msg.sender using IERC20 interface
  - Emit event
- [X] T146 Run ERC20 recovery tests and verify they pass (8 tests passing)
- [X] T147 Add NatSpec comments to recoverERC20()

**Checkpoint**: ERC20 recovery mechanism complete ✅

---

## Phase 16: Security Audit Fixes (Post-Audit)

**Purpose**: Address security findings from comprehensive audit (Slither + Mythril)

**Audit Results Summary**:
- Security Score: 85/100 → 95/100 (after fixes)
- Critical: 0 issues
- High: 1 issue (unchecked ERC20 transfer)
- Medium: 0 issues (all false positives)
- Low: 4 issues (all acceptable)

**Tasks**:

- [X] T148 Add OpenZeppelin SafeERC20 import to `contracts/src/GliskNFT.sol`:
  - Import: `import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";`
  - Add using directive: `using SafeERC20 for IERC20;`

- [X] T149 Update `recoverERC20()` function to use `safeTransfer()`:
  - Replace `IERC20(tokenAddress).transfer(msg.sender, amount);`
  - With: `IERC20(tokenAddress).safeTransfer(msg.sender, amount);`

- [X] T150 Run full test suite and verify all tests pass:
  - `forge test` - all 117 tests passed ✅
  - Verify ERC20 recovery tests still work with SafeERC20 ✅

- [X] T151 Re-run Slither analysis to confirm fix:
  - `slither . --filter-paths "test/|script/" --json .audit/raw/post-fix-slither.json` ✅
  - Verify "unchecked-transfer" finding is resolved ✅

- [X] T152 Update security documentation:
  - Update `audit-fixes.md` with implementation status ✅
  - Mark H-1 finding as resolved ✅

**Checkpoint**: Security audit fixes complete, contract ready for testnet deployment ✅
**Security Score**: 95/100 (improved from 85/100)

**References**:
- Audit Report: `.audit/reports/glisknft/glisknft-2025-10-14T11-23-36-audit-report.md`
- Findings Document: `specs/001-full-smart-contract/audit-fixes.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phases 3-10)**: All depend on Foundational phase completion
  - **Phase 3 (US1 - Mint)**: Can start after Foundational - MVP CRITICAL
  - **Phase 4 (US2 - Claims)**: Can start after Foundational - MVP CRITICAL, uses mint data
  - **Phase 5 (US8 - Reveal)**: Can start after Foundational - MVP CRITICAL
  - **Phase 6 (US5 - Treasury)**: Can start after Foundational - Independent
  - **Phase 7 (US3 - Pricing)**: Can start after Foundational - Independent
  - **Phase 8 (US6 - Access Control)**: Can start after Foundational - Validates existing role checks
  - **Phase 9 (US4 - Season End)**: Can start after Foundational - Independent
  - **Phase 10 (US7 - Royalties)**: Can start after Foundational - Independent
- **Integration Testing (Phase 11)**: Depends on all desired user stories being complete
- **Advanced Testing (Phase 12)**: Can run in parallel with Phase 11
- **Deployment (Phase 13)**: Depends on all testing phases passing
- **Documentation (Phase 14)**: Can run in parallel with Phases 11-13
- **ERC20 Recovery (Phase 15)**: Independent, can be added anytime

### User Story Dependencies

**MVP Core (Must complete together):**
- User Story 1 (P1 - Mint): Foundation for all functionality
- User Story 2 (P1 - Claims): Depends on mint data but independently testable
- User Story 8 (P1 - Reveal): Depends on minted tokens but independently testable

**Independent Features (Can be added in any order after MVP):**
- User Story 5 (P3 - Treasury): Uses treasury balance from mints
- User Story 3 (P2 - Pricing): Updates mint price
- User Story 6 (P2 - Access Control): Validates existing role usage
- User Story 4 (P2 - Season End): Controls mint availability
- User Story 7 (P3 - Royalties): Standalone royalty configuration

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Contract state setup before business logic
- Core functionality before edge cases
- NatSpec documentation after implementation verified

### Parallel Opportunities

**Setup Phase (Phase 1):**
- T002, T003, T004, T005 can run in parallel (different files)

**Foundational Phase (Phase 2):**
- T010, T011, T012, T013 can run in parallel (different concerns in same file - requires coordination)

**Per User Story Tests:**
- All test files within a story marked [P] can be written in parallel
- Example US1: T016-T024 can all be written in parallel (different test cases)

**User Stories (After Foundational):**
- Phases 3-10 can be worked on in parallel by different developers
- Recommended order for sequential: US1 → US2 → US8 (MVP core) → US3 → US4 → US6 → US5 → US7

**Documentation Phase:**
- T133, T134, T135, T136, T137 can run in parallel

---

## Parallel Example: User Story 1 (Minting)

```bash
# Write all tests for User Story 1 together:
Task: "Write test: testMintSingleNFT() in GliskNFT.Minting.t.sol"
Task: "Write test: testMintBatchNFTs() in GliskNFT.Minting.t.sol"
Task: "Write test: testMintWithOverpayment() in GliskNFT.Minting.t.sol"
Task: "Write test: testMintRevertsInsufficientPayment() in GliskNFT.Minting.t.sol"
Task: "Write test: testMintRevertsZeroQuantity() in GliskNFT.Minting.t.sol"
Task: "Write test: testMintRevertsExceedsMaxBatch() in GliskNFT.Minting.t.sol"
Task: "Write test: testConcurrentMintsUniqueTokenIDs() in GliskNFT.Minting.t.sol"
Task: "Write test: testPromptAuthorAssociation() in GliskNFT.Minting.t.sol"

# All tests in same file but test different scenarios - can be written concurrently
```

---

## Implementation Strategy

### MVP First (Core Functionality - Phases 1-5)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (Minting) - Test independently ✅
4. Complete Phase 4: User Story 2 (Claims) - Test independently ✅
5. Complete Phase 5: User Story 8 (Reveal) - Test independently ✅
6. **STOP and VALIDATE**: Run all tests, verify MVP is functional
7. Deploy to testnet and validate end-to-end

### Incremental Delivery (Add Features)

After MVP is validated:

8. Add Phase 7: User Story 3 (Pricing) - Test independently
9. Add Phase 9: User Story 4 (Season End) - Test independently
10. Add Phase 8: User Story 6 (Access Control) - Validate existing roles
11. Add Phase 6: User Story 5 (Treasury) - Test independently
12. Add Phase 10: User Story 7 (Royalties) - Test independently
13. Each addition is independently testable and deployable

### Final Polish

14. Complete Phase 11: Integration Testing
15. Complete Phase 12: Advanced Testing (Fuzz & Invariant)
16. Complete Phase 13: Deployment Infrastructure
17. Complete Phase 14: Documentation
18. Complete Phase 15: ERC20 Recovery (optional safety feature)

### Parallel Team Strategy

With multiple developers after Foundational phase:

- **Developer A**: User Story 1 (Minting) - Most critical
- **Developer B**: User Story 2 (Claims) - Depends on mint data
- **Developer C**: User Story 8 (Reveal) - Depends on minted tokens

Once MVP core is done:

- **Developer A**: User Story 3 (Pricing) + User Story 4 (Season End)
- **Developer B**: User Story 6 (Access Control) + User Story 5 (Treasury)
- **Developer C**: User Story 7 (Royalties) + Integration Testing

---

## Notes

- **[P]** tasks = different files or independent concerns within same file, no blocking dependencies
- **[Story]** label (US1, US2, etc.) maps task to specific user story for traceability
- Each user story should be independently completable and testable
- **TDD Approach**: All tests MUST be written and FAIL before implementation begins
- **Gas Optimization**: Focus on correctness first, optimize in Phase 14 if needed
- **Security**: Run Slither and review findings before mainnet deployment
- Verify tests fail before implementing, then verify they pass after
- Commit after each logical task group or checkpoint
- Stop at any checkpoint to validate story independently
- **Constitution Alignment**: All tasks follow "Simplicity First" and "Clear Over Clever" principles

---

## Task Summary

**Total Tasks**: 147
**Test Tasks**: 64 (43.5% of total - comprehensive TDD approach)
**Implementation Tasks**: 83 (56.5% of total)

**Tasks per User Story**:
- Setup (Phase 1): 6 tasks
- Foundational (Phase 2): 9 tasks
- US1 - Mint (Phase 3): 12 tasks (9 tests + 3 implementation)
- US2 - Claims (Phase 4): 10 tasks (6 tests + 4 implementation)
- US8 - Reveal (Phase 5): 15 tasks (8 tests + 7 implementation)
- US5 - Treasury (Phase 6): 11 tasks (6 tests + 5 implementation)
- US3 - Pricing (Phase 7): 9 tasks (5 tests + 4 implementation)
- US6 - Access Control (Phase 8): 13 tasks (8 tests + 5 implementation)
- US4 - Season End (Phase 9): 15 tasks (9 tests + 6 implementation)
- US7 - Royalties (Phase 10): 10 tasks (5 tests + 5 implementation)
- Integration Testing (Phase 11): 7 tasks
- Advanced Testing (Phase 12): 9 tasks
- Deployment (Phase 13): 6 tasks
- Documentation (Phase 14): 9 tasks
- ERC20 Recovery (Phase 15): 6 tasks

**Parallel Opportunities**: 89 tasks marked [P] (60.5% can be parallelized)

**MVP Scope (Phases 1-5)**: 52 tasks
**Full Feature Set**: 147 tasks

**Independent Test Criteria**:
- ✅ Each user story has clear acceptance scenarios from spec.md
- ✅ Each user story has dedicated test suite
- ✅ Each user story can be validated without others
- ✅ Integration tests verify cross-story interactions
