# Implementation Plan: Frontend Foundation with Creator Mint Page

**Branch**: `005-frontend-foundation-with` | **Date**: 2025-10-20 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/005-frontend-foundation-with/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Build a minimal React frontend that enables users to connect Web3 wallets and mint NFTs from shareable creator links. Users visit `/{creatorAddress}`, connect their wallet, select quantity (1-10 NFTs), and approve a blockchain transaction to mint. The application displays transaction status (pending/success/failure) with basic text feedback. Focus is on core functionality with minimal styling (basic Tailwind utilities only).

## Technical Context

**Language/Version**: React 18 + TypeScript (via Vite)
**Primary Dependencies**:
- `vite` - Build tool and dev server
- `react` + `react-dom` - UI framework
- `react-router-dom` - Client-side routing
- `@rainbow-me/rainbowkit` - Wallet connection UI
- `@coinbase/onchainkit` - Coinbase wallet integration
- `wagmi` - React hooks for Ethereum
- `viem` - TypeScript Ethereum library (wagmi dependency)
- `tailwindcss` - Utility-first CSS
- `shadcn/ui` (Button, Input, Card) - Unstyled UI primitives

**Storage**: N/A (stateless frontend, no persistence)
**Testing**: Manual testing only for MVP (automated tests out of scope)
**Target Platform**: Web browsers (Chrome, Firefox, Safari with wallet extensions)
**Project Type**: Single-page application (SPA) with client-side routing
**Performance Goals**:
- Wallet connection modal appears in <1 second
- Transaction status updates within 2 seconds of state change
- Page load time <3 seconds on fast 3G
**Constraints**:
- Base Sepolia testnet only (no multi-chain support)
- No backend integration (direct contract calls only)
- Minimal styling (basic Tailwind utilities, no custom design)
- No custom hooks unless absolutely necessary
- No state management library (useState/useContext only)
**Scale/Scope**:
- 2 pages: Root (/) redirects to creator page, Creator Mint Page (/{creatorAddress})
- 3 components: Header, CreatorMintPage, Layout
- ~300-500 total lines of code

**Contract Integration**:
- Contract address: `0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0` (Base Sepolia)
- ABI location: `backend/src/glisk/contracts/GliskNFT.json`
- Mint function: `mint(address promptAuthor, uint256 quantity) payable`
- Mint price: Query via public `mintPrice` state variable
- Network: Base Sepolia (chainId: 84532)

**Environment Variables**:
- `VITE_CONTRACT_ADDRESS` - GliskNFT contract address
- `VITE_CHAIN_ID` - Chain ID (84532 for Base Sepolia)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with GLISK Constitution v1.1.0:

- [x] **Simplicity First**: Solution uses simplest approach (direct wagmi hooks, no abstractions, minimal components)
- [x] **Seasonal MVP**: Design targets fast delivery (~3-5 days), optimized for 1-3 month lifecycle
- [x] **Monorepo Structure**: Respects structure by creating `/frontend/` directory at repo root
- [x] **Smart Contract Security**: N/A (frontend reads from deployed contract, no contract changes)
- [x] **Clear Over Clever**: Implementation uses direct hooks (useAccount, useWriteContract), simple useState, basic text feedback

*No constitutional violations. All principles followed.*

## Project Structure

### Documentation (this feature)

```
specs/005-frontend-foundation-with/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (technical decisions)
├── data-model.md        # Phase 1 output (state/entities)
├── quickstart.md        # Phase 1 output (setup + testing)
├── contracts/           # Phase 1 output (N/A for frontend - no API contracts)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```
frontend/                       # NEW - Created by this feature
├── public/
│   └── vite.svg
├── src/
│   ├── components/
│   │   └── Header.tsx         # Wallet connection button, connected address display
│   ├── pages/
│   │   └── CreatorMintPage.tsx # Quantity selector, mint button, transaction status
│   ├── lib/
│   │   ├── wagmi.ts           # wagmi config (chains, transports, connectors)
│   │   └── contract.ts        # Contract address + ABI constants
│   ├── App.tsx                # RainbowKit + wagmi providers, routing setup
│   ├── main.tsx               # React entry point
│   └── index.css              # Tailwind imports
├── .env.example               # Environment variable template
├── .env                       # Local environment config (gitignored)
├── index.html
├── package.json
├── tsconfig.json
├── tsconfig.node.json
├── vite.config.ts
├── tailwind.config.js
├── postcss.config.js
└── components.json            # shadcn/ui config

nginx/                          # NEW - Nginx reverse proxy config
└── frontend.conf              # Static file serving + SPA fallback routing
```

**Structure Decision**: This feature creates the `/frontend/` domain with a minimal React SPA. All frontend code lives in `frontend/src/`. The application uses:
- Client-side routing (react-router-dom) for `/{creatorAddress}` dynamic routes
- RainbowKit providers wrap the app for wallet connectivity
- wagmi hooks for contract interactions (useWriteContract, useWaitForTransactionReceipt)
- No backend integration (all data comes from blockchain via wagmi)

## Complexity Tracking

*No violations. Constitution Check passed.*

## Phase 0: Research & Technical Decisions

All technical decisions provided by user. No research needed. See `research.md` for documentation of locked decisions.

## Phase 1: Design Artifacts

### Data Model

See `data-model.md` for:
- Client-side state (wallet connection, mint transaction, form inputs)
- State transitions (transaction lifecycle: idle → pending → success/failed)
- No persistent storage (all state ephemeral)

### API Contracts

N/A - Frontend calls smart contract directly via wagmi. No REST/GraphQL APIs.

Contract interface documented in `research.md` (batchMint function signature).

### Quickstart Guide

See `quickstart.md` for:
1. Project setup (`npm create vite@latest`, dependency installation)
2. Environment configuration (.env file setup)
3. Development server (`npm run dev`)
4. Manual testing steps (wallet connection, minting flow, transaction status)
5. Build and deployment (`npm run build`, nginx configuration)

## Phase 2: Task Generation

**NOT INCLUDED IN THIS COMMAND**. Run `/speckit.tasks` after plan approval to generate implementation tasks.

Tasks will cover:
1. Project initialization (Vite setup, dependencies)
2. RainbowKit + wagmi configuration
3. Component implementation (Header, CreatorMintPage)
4. Routing setup
5. Contract integration
6. Environment configuration
7. Build and deployment setup

## Timeline Estimate

**Total**: 3-5 days for single developer

- Phase 0 (Research): 0 days (decisions provided)
- Phase 1 (Design): 0.5 days (this plan + artifacts)
- Phase 2 (Implementation): 2-3 days
  - Day 1: Project setup, RainbowKit/wagmi config, basic layout
  - Day 2: Mint page, contract integration, transaction flow
  - Day 3: Testing, bug fixes, deployment setup
- Phase 3 (Testing): 0.5-1 day (manual testing, edge cases)

**Deliverable**: Working frontend where users can connect wallet and mint NFTs via shareable creator links.
