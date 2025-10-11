# Implementation Plan: GLISK Smart Contract System

**Branch**: `001-full-smart-contract` | **Date**: 2025-10-10 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-full-smart-contract/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement a complete ERC-721 NFT smart contract system for GLISK Season 0 blind box platform on Base L2. The contract handles batch minting with prompt author attribution, payment distribution (50/50 split between author rewards and treasury), dynamic pricing, role-based access control (Owner/Keeper), NFT reveal workflow (placeholder → permanent URI), season lifecycle management (seasonEnd with 2-week countdown), treasury management, and ERC-2981 royalty support. Technical approach uses OpenZeppelin battle-tested contracts, Solidity ^0.8.20, Foundry for testing/deployment, and IPFS for metadata storage.

## Technical Context

**Language/Version**: Solidity ^0.8.20
**Primary Dependencies**: OpenZeppelin Contracts v5.x (ERC721, AccessControl, ReentrancyGuard, ERC2981)
**Storage**: On-chain state (Ethereum/Base), IPFS via Lighthouse.storage for metadata/images
**Testing**: Foundry (forge test, anvil local chain)
**Target Platform**: Base L2 (Ethereum Layer 2)
**Project Type**: Smart contract (single primary contract with modular components)
**Performance Goals**: Batch mint 20-50 NFTs per transaction, gas-optimized payment distribution
**Constraints**: <$0.05 USD per mint (including L2 gas), immutable post-deployment, security-first design
**Scale/Scope**: Unlimited NFT supply until seasonEnd, ~1-3 month season lifecycle, multiple concurrent users

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with GLISK Constitution v1.0.0:

- [x] **Simplicity First**: Single primary contract (GliskNFT.sol) using battle-tested OpenZeppelin base contracts. No custom token logic, no complex state machines. Batch minting for gas efficiency is justified by user experience and cost requirements.
- [x] **Seasonal MVP**: Design targets single season lifecycle (~1-3 months). seasonEnd permanently stops minting; new seasons = new deployments. No upgrade mechanisms, no long-term migration paths. Optimized for fast delivery.
- [x] **Monorepo Structure**: All smart contracts in `/contracts/` domain. Backend and frontend are future work, clearly separated. No cross-domain coupling in this phase.
- [x] **Smart Contract Security**: OpenZeppelin contracts for access control (AccessControl), reentrancy protection (ReentrancyGuard), and standards (ERC721, ERC2981). All payment flows use pull-over-push pattern. Events for all critical state changes. Atomic operations with revert-on-failure.
- [x] **Clear Over Clever**: Explicit state variables, descriptive function names, NatSpec comments for all public functions. No assembly, no delegate calls, no proxy patterns. Direct implementations with clear payment logic.

**Initial Assessment**: PASSES all constitutional principles. No violations requiring justification.

---

**Post-Design Re-evaluation** (2025-10-10):

After completing Phase 0 (research.md) and Phase 1 (data-model.md, contracts/, quickstart.md):

- [x] **Simplicity First**: ✅ CONFIRMED
  - Single contract (GliskNFT.sol) with clear interface
  - Direct use of OpenZeppelin base contracts (no custom token logic)
  - Pull-over-push payment pattern (industry standard)
  - No assembly, no proxies, no complex state machines
  - Batch operations justified by gas efficiency and user experience

- [x] **Seasonal MVP**: ✅ CONFIRMED
  - seasonEnd permanently stops minting (no resume capability)
  - No upgrade mechanisms or migration paths
  - Fixed 2-week countdown (hardcoded constant)
  - Simple two-step sweep process
  - Designed for ~1-3 month lifecycle

- [x] **Monorepo Structure**: ✅ CONFIRMED
  - All artifacts in `/contracts/` domain
  - Clear separation: specs in `/specs/`, implementation in `/contracts/src/`
  - No dependencies on backend or frontend in this phase
  - Future integration points documented but not implemented

- [x] **Smart Contract Security**: ✅ CONFIRMED
  - ReentrancyGuard on all payable functions
  - Pull pattern for rewards (prevents reentrancy and DoS)
  - AccessControl for role-based permissions
  - State-before-external-call pattern
  - Comprehensive events for audit trail
  - Input validation on all public functions
  - No unchecked arithmetic (Solidity 0.8+ built-in)

- [x] **Clear Over Clever**: ✅ CONFIRMED
  - Descriptive variable names (authorClaimable, treasuryBalance, seasonEndTime)
  - Explicit constants (SWEEP_PROTECTION_PERIOD, MAX_BATCH_SIZE, KEEPER_ROLE)
  - NatSpec documentation in interface
  - Simple mappings instead of complex data structures
  - No gas micro-optimizations at expense of clarity

**Final Assessment**: PASSES all constitutional principles. Design phase reinforces simplicity, security, and seasonal MVP philosophy. No complexity violations detected.

*Constitution Check: APPROVED for implementation phase.*

## Project Structure

### Documentation (this feature)

```
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Fill in the specific paths and modules for this feature.
  GLISK uses a monorepo structure with contracts, backend, and frontend domains.
-->

```
# GLISK Monorepo Structure

contracts/
├── src/
│   ├── GliskNFT.sol           # Main ERC-721 contract
│   └── [feature-contracts]/
├── test/
│   ├── unit/
│   └── integration/
└── scripts/                    # Deploy and management scripts

backend/                        # Future: Event listeners, AI generation
├── src/
│   ├── services/
│   ├── db/
│   └── api/
└── tests/

frontend/                       # Future: Web UI
├── src/
│   ├── components/
│   ├── pages/
│   └── hooks/
└── tests/

shared/                         # Shared types and schemas (if needed)
└── types/
```

**Structure Decision**: This feature affects only the `/contracts/` domain. This is the foundational smart contract implementation for Season 0.

**Files to be created:**
- `contracts/src/GliskNFT.sol` - Main ERC-721 contract with all Season 0 functionality
- `contracts/test/unit/GliskNFT.t.sol` - Unit tests for core contract functions
- `contracts/test/integration/GliskNFT.integration.t.sol` - Integration tests for end-to-end scenarios
- `contracts/script/Deploy.s.sol` - Foundry deployment script
- `contracts/script/Verify.s.sol` - Contract verification script for Base explorer
- `contracts/.env.example` - Environment variable template for deployment

**Files to be modified:**
- `contracts/foundry.toml` - Configure Base RPC, optimizer settings, test settings
- `contracts/remappings.txt` - Import path mappings (if not auto-generated)

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

**Status**: No constitutional violations detected. Constitution Check passed without requiring complexity justification.
