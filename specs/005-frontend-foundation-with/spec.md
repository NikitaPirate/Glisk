# Feature Specification: Frontend Foundation with Creator Mint Page

**Feature Branch**: `005-frontend-foundation-with`
**Created**: 2025-10-20
**Status**: Draft
**Input**: User description: "Frontend Foundation with Creator Mint Page - React app with Web3 wallet integration for NFT minting from creator prompts"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Connect Wallet and Access Creator Page (Priority: P1)

A user receives a shareable creator link (e.g., `/{creatorAddress}`) and wants to connect their Web3 wallet to prepare for minting NFTs.

**Why this priority**: This is the foundation for all other interactions. Without wallet connection, users cannot mint NFTs. This establishes the core infrastructure (wallet integration, routing, basic layout) that all subsequent features depend on.

**Independent Test**: Can be fully tested by visiting a creator link and successfully connecting a wallet. Delivers value by enabling users to authenticate and view the creator page interface.

**Acceptance Scenarios**:

1. **Given** user visits `/{creatorAddress}` without wallet connected, **When** user clicks "Connect Wallet", **Then** wallet selection modal appears with supported wallet options
2. **Given** user selects a wallet from the modal, **When** wallet extension prompts for approval, **Then** user sees their connected wallet address in the header after approval
3. **Given** user has connected wallet, **When** user refreshes the page, **Then** wallet remains connected and user sees their address in header
4. **Given** user visits an invalid creator address, **When** page loads, **Then** user sees the page layout with wallet connection still functional

---

### User Story 2 - Select Mint Quantity (Priority: P2)

A user with connected wallet wants to choose how many NFTs to mint from the creator's prompt (between 1-10 NFTs).

**Why this priority**: This enables users to specify their desired purchase quantity before committing to a transaction. It's a key user input that directly affects the transaction cost and user intent.

**Independent Test**: Can be tested by connecting wallet, then interacting with the quantity selector. Delivers value by giving users control over their purchase amount before transaction approval.

**Acceptance Scenarios**:

1. **Given** user is on creator page with wallet connected, **When** user interacts with quantity selector, **Then** user can select any number between 1-10 NFTs
2. **Given** user selects a quantity (e.g., 5), **When** quantity is updated, **Then** user sees the selected quantity reflected in the UI
3. **Given** user attempts to select quantity less than 1 or greater than 10, **When** input is validated, **Then** selector constrains value to valid range (1-10)

---

### User Story 3 - Mint NFTs from Creator Prompt (Priority: P3)

A user with connected wallet and selected quantity wants to mint NFTs by approving a blockchain transaction.

**Why this priority**: This is the core value proposition - enabling users to mint NFTs. While highest in user value, it depends on P1 (wallet) and P2 (quantity) being functional first.

**Independent Test**: Can be tested by connecting wallet, selecting quantity, clicking Mint, approving transaction in wallet, and verifying success message. Delivers the complete end-to-end minting experience.

**Acceptance Scenarios**:

1. **Given** user has connected wallet and selected quantity, **When** user clicks "Mint" button, **Then** wallet extension prompts transaction approval with correct mint parameters
2. **Given** user approves transaction in wallet, **When** transaction is submitted, **Then** UI shows "pending" status with transaction indicator
3. **Given** transaction is pending, **When** transaction confirms on blockchain, **Then** UI shows success message
4. **Given** transaction is pending, **When** user rejects transaction in wallet, **Then** UI shows error message and returns to ready state
5. **Given** transaction fails on blockchain, **When** failure is detected, **Then** UI shows error message with failure reason

---

### Edge Cases

- What happens when user disconnects wallet during transaction?
- What happens when user switches wallet/network while on creator page?
- How does system handle creator address with no NFT contract deployed?
- What happens when user attempts to mint with insufficient ETH balance?
- How does system handle network congestion (slow transaction confirmation)?
- What happens when user navigates away during pending transaction?

## Requirements *(mandatory)*

### Functional Requirements

#### Foundation Setup

- **FR-001**: System MUST provide a React application built with Vite and TypeScript
- **FR-002**: System MUST include Tailwind CSS for basic utility styling
- **FR-003**: System MUST integrate shadcn/ui component library for UI elements
- **FR-004**: System MUST support client-side routing with routes for creator pages

#### Wallet Integration

- **FR-005**: System MUST integrate RainbowKit, OnchainKit, and wagmi for Web3 wallet connectivity
- **FR-006**: System MUST support Base Sepolia testnet for blockchain interactions
- **FR-007**: System MUST display a wallet connection button in the application header
- **FR-008**: System MUST persist wallet connection across page refreshes
- **FR-009**: System MUST display connected wallet address when wallet is connected
- **FR-010**: System MUST allow users to disconnect their wallet

#### Creator Mint Page

- **FR-011**: System MUST provide a route pattern `/{creatorAddress}` that accepts Ethereum addresses
- **FR-012**: System MUST display a quantity selector allowing users to choose 1-10 NFTs
- **FR-013**: System MUST enforce minimum quantity of 1 NFT and maximum quantity of 10 NFTs
- **FR-014**: System MUST display a "Mint" button that is disabled when wallet is not connected
- **FR-015**: System MUST trigger smart contract transaction when user clicks "Mint" button
- **FR-016**: System MUST use the creator address from URL as the `author` parameter in mint transaction
- **FR-017**: System MUST use user's selected quantity for mint transaction
- **FR-018**: System MUST prompt user's wallet for transaction approval

#### Transaction Status

- **FR-019**: System MUST display "pending" status when transaction is submitted to blockchain
- **FR-020**: System MUST display "success" message when transaction confirms on blockchain
- **FR-021**: System MUST display error message when transaction fails or is rejected
- **FR-022**: System MUST disable mint button during pending transaction to prevent duplicate submissions

#### Layout & Navigation

- **FR-023**: System MUST provide a header component visible on all pages
- **FR-024**: System MUST provide a content area for page-specific content
- **FR-025**: System MUST use basic Tailwind utility classes for layout without custom styling, animations, or gradients

### Key Entities

- **Creator**: An Ethereum address representing the NFT prompt author. Identified by the address in the URL path. Used as the `author` parameter in mint transactions.
- **Mint Transaction**: A blockchain transaction that creates new NFTs. Contains quantity (1-10) and creator address. Has states: not started, pending, success, failed.
- **Wallet Connection**: The user's Web3 wallet session. Contains wallet address and network. Persists across page refreshes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can connect their Web3 wallet in under 10 seconds
- **SC-002**: Users can navigate to any creator page by entering `/{creatorAddress}` URL
- **SC-003**: Users can select mint quantity (1-10) and initiate transaction in under 30 seconds after wallet connection
- **SC-004**: Users receive clear transaction status feedback within 2 seconds of transaction state change (pending, success, failure)
- **SC-005**: 95% of successful mint transactions complete without requiring page refresh to see success message
- **SC-006**: Wallet connection persists across page refreshes without requiring re-authentication

## Assumptions *(mandatory)*

- Users have Web3-compatible wallet browser extensions installed (MetaMask, Coinbase Wallet, etc.)
- Users have ETH on Base Sepolia testnet for gas fees
- GliskNFT smart contract is deployed on Base Sepolia with known contract address
- Contract ABI is available for frontend integration
- Users understand basic Web3 concepts (wallet approval, transaction confirmation)
- Creator addresses in URLs are valid Ethereum addresses (validation can be minimal for MVP)
- Network is Base Sepolia only (no multi-chain support needed for MVP)
- Default styling is acceptable (basic Tailwind utilities, no custom design system beyond shadcn/ui defaults)

## Out of Scope *(mandatory)*

- Custom animations, gradients, or complex visual styling
- Multi-chain support (only Base Sepolia for MVP)
- Creator profile information display (creator name, avatar, bio)
- NFT preview/gallery after minting
- Transaction history or user dashboard
- Wallet balance display or gas estimation
- Error recovery flows (retry failed transactions)
- Mobile-specific optimizations
- SEO or meta tags
- Analytics integration
- Backend integration (all interactions are direct contract calls)
- Creator registration or onboarding flows
- Social sharing features
- Multi-step wizards or guided flows
