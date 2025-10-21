# Feature Specification: Author Profile Management

**Feature Branch**: `006-author-profile-management`
**Created**: 2025-10-20
**Status**: Draft
**Input**: User description: "Author Profile Management - Creator dashboard for setting prompts and claiming rewards

  Core features:
  1. Prompt Management: Authors can create and update their NFT generation prompt (text used for AI image generation when users mint from their address)
  2. Reward Claiming: Authors can claim accumulated creator rewards from minted NFTs

  Implementation:
  - New `/creator-dashboard` page (separate from `/{creatorAddress}` mint page)
  - Backend API endpoints for prompt storage and reward claiming
  - Wallet signature verification for ownership confirmation
  - No special logic on `/{creatorAddress}` page - owners can mint their own tokens like any user

  Out of scope:
  - Social integrations (X, Farcaster)
  - Profile avatars/images
  - Author statistics/analytics
  - NFT galleries

  Development approach: Parallel backend + frontend implementation in proper sequence"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Set AI Generation Prompt (Priority: P1)

An author wants to define the text prompt that will be used to generate AI images when users mint NFTs attributed to their wallet address. This is the core value proposition for authors - controlling what images represent their creative identity.

**Why this priority**: Without a stored prompt, the system cannot generate images for newly minted tokens. This is the foundational feature that enables the entire creator experience and must work before any other functionality.

**Independent Test**: Can be fully tested by connecting a wallet, entering a text prompt (e.g., "Surreal landscapes with neon lighting"), saving it, and verifying the prompt persists when reloading the dashboard. Delivers immediate value by allowing authors to define their artistic vision.

**Acceptance Scenarios**:

1. **Given** I am an author with a wallet, **When** I connect my wallet to the creator dashboard and enter my prompt text, **Then** my prompt is saved to the database and associated with my wallet address
2. **Given** I am an author who has previously set a prompt, **When** I open the creator dashboard, **Then** I see a status indicator showing that my prompt is configured
3. **Given** I am an author updating my prompt, **When** I modify my existing prompt text and save, **Then** the new prompt replaces the old one in the database
4. **Given** I am an author, **When** I try to save an empty prompt or a prompt exceeding 1000 characters, **Then** I see a validation error and the prompt is not saved
5. **Given** I am not connected with a wallet, **When** I try to access the creator dashboard, **Then** I see a message prompting me to connect my wallet first

---

### User Story 2 - Claim Creator Rewards (Priority: P2)

An author wants to withdraw the ETH rewards they've accumulated from users minting NFTs with their wallet address as the prompt author. When users mint NFTs, 50% of the mint price goes to the treasury and 50% is reserved for the prompt author.

**Why this priority**: This enables authors to financially benefit from their creative contributions. While important, it depends on users actually minting NFTs first (which requires a working prompt from P1), making it secondary in priority.

**Independent Test**: Can be fully tested by funding an author's balance on the smart contract (via test mint transactions or direct contract interaction), connecting the author's wallet to the dashboard, clicking "Claim Rewards", and verifying the ETH transfer completes and the claimable balance updates to zero. Delivers tangible financial value to authors.

**Acceptance Scenarios**:

1. **Given** I am an author with accumulated rewards on-chain, **When** I view the creator dashboard, **Then** I see my current claimable balance displayed in ETH
2. **Given** I am an author with a non-zero claimable balance, **When** I click the "Claim Rewards" button, **Then** a blockchain transaction is initiated to transfer my rewards to my wallet
3. **Given** my claim transaction succeeds, **When** the transaction is confirmed on-chain, **Then** my claimable balance on the dashboard updates to 0 ETH
4. **Given** I am an author with zero claimable rewards, **When** I view the creator dashboard, **Then** the claim button is disabled and shows "No rewards to claim"
5. **Given** my claim transaction fails (e.g., network error, user rejection), **When** the error occurs, **Then** I see an error message and my claimable balance remains unchanged

---

### User Story 3 - Wallet Ownership Verification (Priority: P1)

The system must verify that the connected wallet address matches the author making profile changes. This prevents unauthorized users from modifying another author's prompt or claiming their rewards.

**Why this priority**: Security is fundamental. Without ownership verification, the system would allow malicious actors to steal rewards or sabotage other authors' prompts. This must be implemented alongside P1 to ensure secure prompt management.

**Independent Test**: Can be tested by connecting a wallet, initiating a prompt save, signing the verification message, and confirming the save succeeds. Then disconnect, connect a different wallet, and verify that the first wallet's prompt cannot be modified. Delivers secure access control.

**Acceptance Scenarios**:

1. **Given** I am updating my prompt, **When** I click save, **Then** I am prompted to sign a message with my wallet to verify ownership
2. **Given** I sign the ownership verification message, **When** the signature is validated, **Then** my prompt update is processed
3. **Given** I reject the signature request, **When** the wallet cancels the signature, **Then** the prompt update is aborted and I see a message explaining the operation was cancelled
4. **Given** I am connected with wallet A, **When** I try to modify a prompt associated with wallet B, **Then** the system rejects the operation and shows an error message
5. **Given** my wallet session expires, **When** I try to save a prompt or claim rewards, **Then** I am prompted to reconnect my wallet

---

### Edge Cases

- What happens when an author tries to claim rewards but their wallet address has zero claimable balance on the smart contract? (System should show "No rewards to claim" without initiating a transaction)
- What happens when an author sets a prompt containing special characters, emojis, or multi-line text? (System should accept all valid UTF-8 characters up to 1000 characters and persist them for image generation)
- What happens when the blockchain network is congested and the claim transaction times out? (System should show appropriate error message and allow retry without losing the user's claimable balance)
- What happens when an author connects their wallet but has never minted any NFTs as a prompt author? (Dashboard should show zero claimable balance and allow them to set/update their prompt normally)
- What happens if two authors try to claim rewards simultaneously from the same contract? (Smart contract handles this with proper state management - both transactions process independently)
- What happens when an author switches to a different wallet address while on the dashboard? (System should detect the wallet change and reload data for the new wallet address)
- What happens if the smart contract is not deployed or the RPC endpoint is unreachable? (System should display a clear error message indicating blockchain connectivity issues)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a `/creator-dashboard` route separate from the `/{creatorAddress}` mint page
- **FR-002**: System MUST verify wallet ownership via cryptographic signature before allowing prompt updates
- **FR-003**: System MUST store author prompts in a database table with wallet address as the unique identifier
- **FR-004**: System MUST validate prompt text to ensure it is between 1 and 1000 characters in length
- **FR-005**: System MUST query the smart contract `authorClaimable[address]` mapping to display current claimable balance
- **FR-006**: System MUST provide a backend API endpoint to save/update author prompts (e.g., `POST /api/authors/prompt`)
- **FR-007**: System MUST provide a backend API endpoint to check if an author has configured a prompt (e.g., `GET /api/authors/{wallet_address}` returns boolean status)
- **FR-008**: System MUST initiate a blockchain transaction calling `claimAuthorRewards()` when an author requests to claim rewards
- **FR-009**: System MUST display the current claimable balance in ETH with appropriate decimal precision (18 decimals for wei conversion)
- **FR-010**: System MUST disable the claim button when claimable balance is zero or when a claim transaction is in progress
- **FR-011**: System MUST provide clear error messages for validation failures (invalid prompt length, signature rejection, transaction failures)
- **FR-012**: System MUST allow authors to update their existing prompt without requiring deletion and recreation
- **FR-013**: System MUST persist prompt changes immediately upon successful signature verification
- **FR-014**: System MUST handle wallet disconnection gracefully by showing a connection prompt
- **FR-015**: System MUST support standard Ethereum wallet providers (MetaMask, WalletConnect, Coinbase Wallet)
- **FR-016**: Backend MUST validate that the signature corresponds to the wallet address claiming to update the prompt
- **FR-017**: Backend MUST return appropriate HTTP status codes (200 for success, 400 for validation errors, 401 for unauthorized, 500 for server errors)
- **FR-018**: Frontend MUST update the displayed claimable balance after a successful claim transaction is confirmed on-chain
- **FR-019**: System MUST preserve existing prompt if an update fails (no partial updates)
- **FR-020**: System MUST allow authors to view the dashboard and set prompts even if they have never minted any NFTs

### Key Entities

- **Author Profile**: Represents an author's profile containing their wallet address (unique identifier), AI generation prompt (text used for image generation), and optional social handles (Twitter/Farcaster - out of scope for this feature but present in schema). Each wallet address maps to exactly one author profile.

- **Claimable Rewards**: Represents the accumulated ETH balance for an author stored in the smart contract's `authorClaimable` mapping. This balance increases each time a user mints an NFT with this author as the prompt author (50% of mint price), and decreases to zero when the author claims rewards.

- **Signature Verification**: Represents the cryptographic proof that the connected wallet owner authorizes a specific action (prompt update or reward claim). Contains the wallet address, signed message, and signature bytes used for backend validation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Authors can set or update their AI generation prompt in under 30 seconds (including wallet connection and signature)
- **SC-002**: Prompt changes persist correctly in database with 100% accuracy (verified via backend logs, not user-visible)
- **SC-003**: Authors can successfully claim rewards in under 2 minutes (including transaction confirmation time on Base Sepolia testnet)
- **SC-004**: 95% of signature verification requests succeed on first attempt when users approve the signature
- **SC-005**: Zero unauthorized prompt modifications (all prompt changes require valid wallet signature)
- **SC-006**: Dashboard correctly displays claimable balance within 5 seconds of page load
- **SC-007**: System handles wallet disconnection/reconnection without requiring page refresh
- **SC-008**: Error messages provide actionable guidance in 100% of failure scenarios (users understand what went wrong and how to fix it)
- **SC-009**: Claim transactions fail gracefully with clear error messages when insufficient gas, rejected by user, or network issues occur
- **SC-010**: Dashboard remains responsive and functional when blockchain RPC endpoint has latency up to 5 seconds
