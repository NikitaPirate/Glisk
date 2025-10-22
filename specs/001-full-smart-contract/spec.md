# Feature Specification: GLISK Smart Contract System

**Feature Branch**: `001-full-smart-contract`
**Created**: 2025-10-10
**Status**: Draft
**Input**: Full smart contract implementation for GLISK Season 0 blind box NFT platform

**Note**: Contract now implements ERC721Enumerable (added October 2025) for improved marketplace compatibility and token enumeration. Current deployment: `0x569d456c584Ac2bb2d66b075a31278630E7d43a0`

## Clarifications

### Session 2025-10-10

- Q: Should there be a maximum total supply of NFTs that can be minted in Season 0? → A: Unlimited supply; seasonEnd stops minting and starts countdown for unclaimed rewards
- Q: How should prompt author addresses be controlled during minting? → A: Open system - any address can be specified as prompt author during mint
- Q: How should the system handle payment amounts during minting? → A: Minimum payment - accept overpayment, keep excess in treasury
- Q: Should users be able to mint multiple NFTs in a single transaction? → A: Batch minting - user specifies quantity, all same author (gas efficient)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Mint Blind Box NFT (Priority: P1)

Users can mint surprise NFTs by selecting a prompt author, specifying quantity, and paying the total price, without knowing what they'll get.

**Why this priority**: Core revenue-generating action. Without minting, the platform has no purpose. This is the primary user interaction that drives the entire ecosystem. Batch minting reduces gas costs for users minting multiple NFTs.

**Independent Test**: User connects wallet, selects a prompt author, specifies quantity (1 or more), pays the total mint price (price × quantity), receives NFT tokens. Author's claimable balance increases by 50% of payment. Treasury receives 50%. Can be fully tested without any other features working.

**Acceptance Scenarios**:

1. **Given** a user has sufficient ETH balance, **When** they mint a single NFT from an author's collection with exact payment, **Then** they receive a unique NFT token and payment is split 50/50 between author rewards and treasury
2. **Given** a user wants multiple NFTs, **When** they mint a batch (quantity N) from same author with exact payment (price × N), **Then** they receive N unique NFT tokens and total payment is split 50/50 between author rewards and treasury
3. **Given** a user sends overpayment, **When** they mint, **Then** the base mint price × quantity is split 50/50 and any excess goes entirely to treasury
4. **Given** a user attempts to mint, **When** they provide insufficient payment for the requested quantity, **Then** the transaction reverts and no NFTs are minted
5. **Given** a user requests batch mint with quantity 0, **When** the transaction is submitted, **Then** the transaction reverts
6. **Given** multiple users mint simultaneously, **When** transactions process, **Then** each receives unique token IDs with no collisions
7. **Given** a batch mint is successful, **When** the NFTs are transferred to the user, **Then** the prompt author's address is permanently associated with all tokens on-chain

---

### User Story 2 - Prompt Author Earnings and Claims (Priority: P1)

Prompt authors earn 50% of each mint from their prompts and can claim all accumulated rewards at any time.

**Why this priority**: Author incentive is critical for content supply. If authors can't earn and claim rewards, there's no motivation to create prompts. This is as essential as minting itself.

**Independent Test**: After multiple mints from an author's collection, the author can withdraw all accumulated rewards to their wallet. Can be tested independently by minting, checking balance, and claiming.

**Acceptance Scenarios**:

1. **Given** users have minted NFTs from an author's prompts, **When** the author checks their claimable balance, **Then** it reflects 50% of all mint payments for their prompts
2. **Given** an author has claimable rewards, **When** they claim, **Then** the full balance transfers to their wallet and their claimable balance resets to zero
3. **Given** an author has zero claimable balance, **When** they claim, **Then** the transaction processes successfully with zero transfer (no revert)

---

### User Story 3 - Dynamic Pricing Management (Priority: P2)

Authorized roles (Owner or Keeper) can adjust the mint price in response to ETH volatility to maintain target USD pricing.

**Why this priority**: Important for maintaining ~$0.05 target price, but not blocking for initial launch. Can launch with a fixed price and adjust as needed. Keeper role allows future automation.

**Independent Test**: Owner or Keeper can update the mint price, and subsequent mints use the new price. Previous mints are unaffected. Unauthorized addresses cannot update price.

**Acceptance Scenarios**:

1. **Given** Owner detects ETH price volatility, **When** they update the mint price, **Then** all subsequent mints use the new price
2. **Given** a Keeper role updates the price, **When** they submit the transaction, **Then** it succeeds and all subsequent mints use the new price
3. **Given** a price update transaction, **When** submitted by an unauthorized address, **Then** the transaction reverts
4. **Given** mints have occurred at the old price, **When** the price updates, **Then** the 50/50 split remains consistent for all mints regardless of price
5. **Given** a price update, **When** users query the mint price, **Then** they receive the current price to include in their mint transaction

---

### User Story 4 - Season End and Unclaimed Rewards (Priority: P2)

Owner can end a season, which stops all new minting and starts a 2-week countdown, giving prompt authors time to claim rewards before unclaimed funds return to treasury.

**Why this priority**: Necessary for season transitions but not needed at launch. Can be implemented before first season ends.

**Independent Test**: Owner triggers seasonEnd which immediately stops minting and starts 2-week countdown. During countdown, authors can still claim but minting is disabled. After countdown expires, Owner can sweep unclaimed rewards to treasury. Can be tested with a shorter countdown in test environment.

**Acceptance Scenarios**:

1. **Given** a season is ending, **When** Owner triggers seasonEnd, **Then** minting immediately stops and a 2-week countdown begins
2. **Given** seasonEnd has been triggered, **When** a user attempts to mint, **Then** the transaction reverts
3. **Given** the countdown is active, **When** authors claim their rewards, **Then** claims process normally
4. **Given** the countdown has expired, **When** Owner sweeps unclaimed rewards, **Then** all unclaimed author balances transfer to treasury and reset to zero
5. **Given** the countdown is active, **When** Owner attempts to sweep early, **Then** the transaction reverts
6. **Given** seasonEnd has not been triggered, **When** Owner attempts to sweep, **Then** the transaction reverts

---

### User Story 5 - Treasury Management (Priority: P3)

Treasury funds accumulate from mint fees (50% of each mint) and direct payments, with Owner able to withdraw all treasury funds for platform operations.

**Why this priority**: Important for sustainability but not critical for initial testing. Can be implemented after core minting and rewards flow is proven.

**Independent Test**: Treasury balance increases from mints and direct transfers. Owner can withdraw all treasury funds. Unauthorized addresses cannot withdraw. Can test by checking balance changes and withdrawal permissions.

**Acceptance Scenarios**:

1. **Given** mints occur, **When** payments are split, **Then** 50% of each payment accumulates in the treasury balance
2. **Given** someone sends ETH directly to the contract, **When** the payment is received, **Then** it adds to the treasury balance
3. **Given** treasury has a balance, **When** Owner withdraws, **Then** the full treasury balance transfers to Owner and treasury balance resets to zero
4. **Given** an unauthorized address attempts treasury withdrawal, **When** the transaction is submitted, **Then** it reverts with access control error

---

### User Story 6 - Role-Based Access Control (Priority: P2)

System implements hierarchical role-based access for different operations: Owner (full control) and Keeper (limited operations like URI updates and price management).

**Why this priority**: Critical for operational flexibility. Owner has ultimate control, while Keeper role can handle routine maintenance like updating NFT metadata after image generation and future price automation.

**Independent Test**: Owner can grant/revoke Keeper role. Keeper can update URIs and prices but cannot withdraw funds or manage seasons. Owner can perform all operations. Can test by checking role permissions and operation restrictions.

**Acceptance Scenarios**:

1. **Given** an address needs Keeper permissions, **When** Owner grants Keeper role, **Then** that address can perform Keeper operations
2. **Given** a Keeper role address, **When** they update NFT metadata URIs, **Then** the operation succeeds
3. **Given** a Keeper role address, **When** they attempt to withdraw treasury funds, **Then** the transaction reverts
4. **Given** a Keeper role address, **When** they attempt to start season finalization, **Then** the transaction reverts
5. **Given** Owner needs to revoke Keeper access, **When** they revoke the role, **Then** that address can no longer perform Keeper operations
6. **Given** Owner performs any operation, **When** the transaction is submitted, **Then** it succeeds (Owner has all permissions)

---

### User Story 7 - Secondary Sales Royalties (Priority: P3)

NFTs support marketplace royalties where secondary sales pay a 2.5% royalty fee that goes entirely to the treasury.

**Why this priority**: Important for ongoing revenue but depends on marketplace support. Not critical for launch since primary mints are the main revenue source. Simplified to single receiver (treasury) due to standard limitations.

**Independent Test**: NFT contract exposes royalty information. When queried for any token's royalty, it returns 2.5% with treasury as the recipient. Marketplaces that support royalty standards will automatically enforce this.

**Acceptance Scenarios**:

1. **Given** any NFT token, **When** a marketplace queries royalty information, **Then** the system returns 2.5% royalty with treasury address as the sole recipient
2. **Given** Owner wants to adjust royalty percentage, **When** they update the royalty rate, **Then** all subsequent royalty queries reflect the new percentage
3. **Given** a marketplace respects royalty standards, **When** a secondary sale occurs, **Then** the marketplace sends the royalty payment to treasury

---

### User Story 8 - NFT Reveal and Metadata Update (Priority: P1)

NFTs start with a placeholder image and are permanently revealed after off-chain image generation by updating their metadata URIs once.

**Why this priority**: Core to the blind box experience. Users mint without knowing the result, then the reveal happens after generation. Once revealed, URIs are immutable for reliability and historical preservation. Critical for the product concept.

**Independent Test**: Newly minted NFTs show placeholder metadata. Owner can update placeholder URI. Owner or Keeper can batch reveal tokens by setting their URIs. Once revealed, a token's URI cannot be changed again. Placeholder URI is set at deployment with ability to update it.

**Acceptance Scenarios**:

1. **Given** a new NFT is minted, **When** metadata is queried, **Then** it returns the current placeholder URI
2. **Given** placeholder URI needs updating, **When** Owner updates it, **Then** all unrevealed tokens use the new placeholder URI
3. **Given** images have been generated off-chain, **When** Owner or Keeper submits batch URI update for unrevealed token IDs, **Then** those tokens' metadata updates to their generated image URIs permanently
4. **Given** multiple tokens need revealing, **When** Keeper or Owner updates URIs in batch, **Then** all specified unrevealed tokens update in a single transaction
5. **Given** a token has been revealed, **When** Owner or Keeper attempts to update its URI again, **Then** the transaction reverts (revealed tokens are immutable)

---

### Edge Cases

- What happens when ETH price changes mid-mint transaction? (Price is locked at transaction submission time)
- What if a user overpays for a mint? (System accepts minimum payment; excess goes entirely to treasury, no refund)
- What if a user underpays for a batch mint? (Transaction reverts with insufficient payment error)
- What if a user requests quantity 0? (Transaction reverts; must mint at least 1 NFT)
- Is there a maximum batch size per transaction? (Implementation should enforce reasonable gas-based limit; typically 20-50 NFTs per transaction)
- How does batch minting affect author rewards? (Total payment split 50/50 regardless of quantity; all to same author since batch uses single author)
- How does the system handle a prompt author address that is a contract? (Treats it like any other address; author contract must handle receiving ETH)
- Can any address be specified as prompt author? (Yes, open system with no registry or whitelist; off-chain validation determines legitimate authors)
- What if zero address (0x0) is specified as prompt author? (System accepts it; rewards accumulate to zero address and are effectively burned)
- What if a prompt author never claims rewards? (After seasonEnd countdown expires, unclaimed funds sweep to treasury)
- Can a prompt author mint their own NFTs? (Yes, they pay the mint price and 50% reward is added to their claimable balance, but only before seasonEnd)
- What if the same author address is used for multiple mints before any claims? (Rewards accumulate; single claim withdraws total)
- Can an author claim with zero balance? (Yes, transaction succeeds with zero transfer)
- What if Keeper role is compromised? (Keeper can only update URIs and prices; cannot steal funds. Owner can revoke role immediately)
- What if a token's URI is never updated from placeholder? (Token continues showing placeholder; no automatic reveal mechanism)
- Can a revealed token's URI be updated again? (No, once revealed it's immutable for reliability and historical preservation)
- What happens if placeholder URI needs updating? (Owner can update it anytime; affects all unrevealed tokens immediately)
- Can placeholder URI be different for different tokens? (No, all unrevealed tokens share the same placeholder URI)
- What if someone sends ERC20 tokens to the contract by mistake? (Owner can withdraw them; simple safety mechanism, not a feature)
- What happens to ERC20 tokens if never withdrawn? (They remain in contract; no automatic handling)
- Is there a maximum supply cap for NFTs? (No, unlimited supply until seasonEnd is triggered)
- Can minting resume after seasonEnd? (No, seasonEnd permanently stops minting for that contract; new season requires new deployment)

## Requirements *(mandatory)*

### Functional Requirements

**Minting & Payment Distribution:**
- **FR-001**: System MUST support batch minting where users specify quantity (N ≥ 1) and pay at least mint price × quantity (unlimited supply until seasonEnd)
- **FR-002**: System MUST accept a prompt author address as a parameter for each mint operation (applies to all NFTs in batch)
- **FR-003**: System MUST split the total base payment (mint price × quantity) exactly 50/50 between author rewards (escrow) and platform treasury
- **FR-004**: System MUST accept overpayment and send excess amount entirely to treasury (no refund)
- **FR-005**: System MUST revert transactions with insufficient payment for the requested quantity
- **FR-006**: System MUST revert transactions with quantity 0
- **FR-007**: System MUST assign sequential or unique token IDs without collisions across all batch mints
- **FR-008**: System MUST store only the prompt author's address on-chain for each token in the batch
- **FR-009**: System MUST prevent minting after seasonEnd has been triggered
- **FR-010**: System SHOULD enforce a reasonable maximum batch size per transaction to prevent gas limit issues (recommended 20-50)

**Author Rewards:**
- **FR-011**: System MUST track claimable reward balance for each prompt author address independently
- **FR-012**: Prompt authors MUST be able to claim all accumulated rewards at any time
- **FR-013**: System MUST transfer the full claimable balance to authors when they claim
- **FR-014**: System MUST reset author's claimable balance to zero after successful claim
- **FR-015**: System MUST allow claims even when balance is zero (no revert)

**Role-Based Access Control:**
- **FR-016**: System MUST implement Owner role with full control over all operations
- **FR-017**: System MUST implement Keeper role with limited permissions (URI updates, price updates only)
- **FR-018**: Owner MUST be able to grant and revoke Keeper role
- **FR-019**: System MUST prevent unauthorized addresses from performing privileged operations
- **FR-020**: Keeper MUST NOT be able to withdraw funds or manage season end

**Pricing:**
- **FR-021**: Owner or Keeper MUST be able to update the mint price to respond to ETH volatility

**NFT Reveal & Metadata:**
- **FR-022**: System MUST use a placeholder URI for all newly minted tokens until revealed
- **FR-023**: Placeholder URI MUST be set at contract deployment as initial value
- **FR-024**: Owner MUST be able to update the placeholder URI at any time
- **FR-025**: Placeholder URI changes MUST affect all unrevealed tokens immediately
- **FR-026**: Owner or Keeper MUST be able to batch reveal multiple unrevealed tokens in a single transaction
- **FR-027**: System MUST prevent URI updates for already-revealed tokens (revealed tokens are immutable)
- **FR-028**: Each token MUST be able to have its own unique URI after reveal

**Season End:**
- **FR-029**: Owner MUST be able to trigger seasonEnd which immediately stops all minting
- **FR-030**: System MUST enforce a 2-week waiting period after seasonEnd is triggered before allowing reward sweep
- **FR-031**: Owner MUST be able to sweep unclaimed author rewards to treasury after countdown expires
- **FR-032**: System MUST prevent sweeping unclaimed rewards before countdown expires
- **FR-033**: Authors MUST be able to claim rewards during the countdown period after seasonEnd

**Treasury Management:**
- **FR-034**: System MUST accumulate treasury funds from 50% of each mint, overpayment excess, and direct payments
- **FR-035**: Owner MUST be able to withdraw all treasury funds
- **FR-036**: System MUST accept direct ETH payments and add them to treasury balance

**Secondary Sales Royalties:**
- **FR-037**: System MUST expose royalty information for each token following standard interfaces
- **FR-038**: System MUST return treasury address as the sole royalty recipient
- **FR-039**: System MUST configure default royalty at 2.5% to treasury
- **FR-040**: Owner MUST be able to update the royalty percentage

**ERC20 Safety Mechanism:**
- **FR-041**: Owner MUST be able to safely withdraw any ERC20 tokens sent to the contract using OpenZeppelin SafeERC20 library to handle non-standard tokens (safety mechanism only)

**Events & Monitoring:**
- **FR-042**: System MUST emit events for all critical state changes (mints, claims, price updates, withdrawals, role changes, URI updates, seasonEnd)

### Key Entities

- **NFT Token**: Represents a minted blind box NFT with unique ID, owner address, prompt author address, and metadata URI (starts as placeholder, becomes immutable after reveal); unlimited supply until seasonEnd
- **Prompt Author**: Address that created prompts; tracks accumulated claimable rewards (50% of mints)
- **Treasury**: Platform-controlled balance accumulated from 50% of mint fees, direct payments, and 2.5% royalties
- **Owner**: Top-level privileged role with full control over all system operations
- **Keeper**: Limited role authorized to reveal NFTs (update URIs) and update pricing
- **Mint Price**: Fixed ETH amount required to mint, stored on-chain and updatable by Owner/Keeper
- **Placeholder URI**: Default metadata URI for unrevealed NFTs, set at deployment and updatable by Owner anytime
- **Revealed Token**: NFT with permanently set custom URI; once revealed, URI becomes immutable
- **Season End (seasonEnd)**: Owner-triggered event that immediately stops all minting and starts a 2-week countdown before unclaimed rewards can be swept to treasury
- **Royalty**: Secondary sale fee (default 2.5%) paid entirely to treasury

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can mint single or multiple NFTs in one transaction by specifying quantity and paying total price (price × quantity), immediately receiving ownership of unique tokens
- **SC-002**: Each mint (single or batch) completes in a single transaction with payment automatically split 50/50 between author and treasury
- **SC-003**: Prompt authors can view their claimable balance and withdraw all rewards in a single transaction at any time, including when balance is zero
- **SC-004**: Owner or Keeper can update mint price and the new price takes effect for all subsequent mints within the same block
- **SC-005**: Newly minted NFTs display placeholder metadata until revealed
- **SC-006**: Owner can update placeholder URI anytime and all unrevealed tokens immediately reflect the change
- **SC-007**: Owner or Keeper can permanently reveal multiple NFTs by updating their URIs in a single batch transaction
- **SC-008**: Once revealed, an NFT's URI cannot be changed again (immutable for reliability)
- **SC-009**: seasonEnd immediately stops all minting, prevents premature reward sweeping, and enforces 2-week countdown before allowing sweep
- **SC-010**: Treasury correctly accumulates 50% of mint fees, all direct payments, and royalties without loss
- **SC-011**: Owner can withdraw all treasury funds in a single transaction
- **SC-012**: Role hierarchy restricts operations appropriately: Owner has full access, Keeper has limited access (reveals/pricing only)
- **SC-013**: System handles concurrent mints from multiple users without token ID collisions or payment errors
- **SC-014**: All critical operations emit events that can be monitored by off-chain services
- **SC-015**: NFTs expose 2.5% royalty information directing to treasury for marketplace integration
- **SC-016**: Owner can safely withdraw any ERC20 tokens mistakenly sent to the contract with proper handling of non-standard token implementations

## Assumptions

- NFTs have unlimited supply until seasonEnd is triggered
- Users can batch mint multiple NFTs in a single transaction for gas efficiency (same prompt author for all NFTs in batch)
- Prompt author addresses are open (no on-chain whitelist/registry); off-chain systems validate legitimate authors
- Payment split is fixed at 50/50 between prompt author rewards and treasury for primary mints (applies to total batch payment)
- Owner role is securely managed and has appropriate authorization
- Placeholder URI is set at deployment and can be updated by Owner as needed
- NFT metadata URIs will be permanently revealed after minting by Owner or Keeper role via off-chain generation process
- Once revealed, NFTs are immutable for reliability and historical preservation
- NFTs will be compatible with standard NFT marketplace platforms
- Transaction costs are acceptable for target users on Base L2
- One season runs for approximately 1-3 months until Owner triggers seasonEnd
- The 50/50 split applies uniformly to all prompt authors and mints
- External services will monitor system events and handle image generation workflow
- Payment operations follow industry-standard security practices to prevent exploits
- Marketplace support for royalty standards is voluntary; not all marketplaces may enforce royalties
- Secondary sale royalty percentage defaults to 2.5% and goes entirely to treasury (not split with authors)
- Contract only handles native ETH for payments; any ERC20 tokens are considered accidental
- seasonEnd permanently stops minting for that contract deployment; new seasons require new contract deployments

## Known Constraints

- No maximum supply cap; NFTs have unlimited supply until seasonEnd is triggered
- Mint price must be updated manually by Owner or Keeper; no automatic USD price adjustment
- seasonEnd countdown is fixed at 2 weeks and cannot be modified after starting
- seasonEnd permanently stops minting; cannot resume minting after triggered (new season requires new contract deployment)
- Revealed NFTs are permanently immutable; URIs cannot be changed after reveal for reliability and historical preservation
- Unrevealed tokens share a single placeholder URI (cannot have per-token placeholders)
- Prompt author associations with tokens are permanent and cannot be changed after minting
- System cannot be paused mid-season; only seasonEnd can stop minting
- Payment distribution is fixed at exactly 50/50 and applies uniformly to all mints
- Royalty enforcement depends on marketplace support; system can only expose royalty information, not enforce payment
- Royalties go 100% to treasury (cannot be split with authors due to ERC2981 single-receiver limitation)
- Role hierarchy is two-level only (Owner and Keeper); no support for additional custom roles
- Contract designed for ETH only; ERC20 tokens can be withdrawn but are not part of normal operations
