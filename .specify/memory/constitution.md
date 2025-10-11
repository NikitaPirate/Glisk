<!--
SYNC IMPACT REPORT
==================
Version Change: Initial → 1.0.0
Created: 2025-10-10
Change Type: Initial constitution creation

Principles Added:
- I. Simplicity First
- II. Seasonal MVP Philosophy
- III. Monorepo Structure
- IV. Smart Contract Security
- V. Clear Over Clever

Sections Added:
- Core Principles (5 principles)
- Technical Constraints
- Development Standards
- Governance

Templates Status:
- ✅ plan-template.md (reviewed - constitution check section compatible)
- ✅ spec-template.md (reviewed - requirements align with principles)
- ✅ tasks-template.md (reviewed - task structure supports principles)

Follow-up TODOs:
- None - all placeholders filled
-->

# GLISK Constitution

## Core Principles

### I. Simplicity First

Code MUST be clear and elegant above all else. Complexity requires explicit justification.

**Rules:**
- Choose the simplest solution that solves the problem
- Avoid premature abstraction or over-engineering
- Prefer direct implementations over design patterns unless complexity is warranted
- Code should be readable and self-documenting

**Rationale:** Season-based lifecycle means code doesn't need to support infinite future use cases. Clean, simple code is faster to write, easier to debug, and sufficient for time-boxed seasons.

### II. Seasonal MVP Philosophy

Development targets fast MVP delivery for time-limited seasons. Solutions prioritize working code over long-term scalability.

**Rules:**
- Ship working features quickly over perfect architecture
- Optimize for iteration speed and clarity
- Solutions need only survive one season (~1-3 months)
- Technical debt is acceptable if it doesn't compromise core functionality or security
- Document tradeoffs explicitly when taking shortcuts

**Rationale:** Each season is a complete, standalone experience. When the season ends, we can rebuild with fresh insights rather than maintaining legacy code forever. This removes the burden of long-term maintenance while maintaining quality standards.

### III. Monorepo Structure

Project is organized as a monorepo with three distinct domains: contracts, backend, frontend.

**Rules:**
- `/contracts/` - Solidity smart contracts (ERC-721, payment logic, season management)
- `/backend/` - Off-chain services (event listeners, image generation, metadata storage)
- `/frontend/` - Web application (user interface, wallet integration)
- Each domain maintains independent testing and deployment
- Shared types/schemas live in `/shared/` when needed
- Cross-domain dependencies MUST be explicit and documented

**Rationale:** Clear separation enables parallel development while maintaining shared context. Currently focusing on contracts; backend and frontend specifics will be added when development begins.

### IV. Smart Contract Security

Smart contracts MUST prioritize security and correctness over feature richness.

**Rules:**
- Gas efficiency matters, but security comes first
- All payment flows MUST be auditable and tested
- Follow established patterns (OpenZeppelin, proven implementations)
- State changes MUST be atomic and revert on failure
- Events MUST be emitted for all critical state changes
- Admin functions MUST have appropriate access controls

**Rationale:** Contracts handle real funds and are immutable post-deployment. Security vulnerabilities can't be patched quickly in a season model. Better to ship simple, secure contracts than complex, risky ones.

### V. Clear Over Clever

Code MUST favor clarity and directness over cleverness or optimization unless performance requirements demand otherwise.

**Rules:**
- Variable and function names MUST be descriptive
- Magic numbers and strings MUST be replaced with named constants
- Complex logic MUST have explanatory comments
- Avoid language tricks that reduce readability
- If optimization is needed, document why and benchmark the improvement

**Rationale:** Enables rapid iteration and reduces bugs. When seasons are short, maintenance burden must be minimal. Clear code can be understood and modified quickly.

## Technical Constraints

### Smart Contracts

**Target Chain:** Base (Ethereum L2)

**Language:** Solidity ^0.8.20

**Standards:**
- ERC-721 for NFT implementation
- OpenZeppelin contracts for security-critical components

**Key Requirements:**
- Fixed ETH price stored on-chain (admin-updatable for volatility)
- Payment distribution: creator percentage (claimable) + treasury
- Batch reveal support for post-mint URI updates
- Season finalization with countdown for unclaimed rewards (sweepDust)
- Direct payments to contract address go to treasury

**Storage:**
- IPFS via Lighthouse.storage for NFT metadata and images
- On-chain: prompt author address only
- Off-chain: social handles, prompt text, generation params

### Backend (Future)

**Purpose:** Event listening, image generation, metadata management

**Key Functions:**
- Listen for mint events on-chain
- Store author-address-prompt mapping in database
- Generate images using AI (Flux Schnell model)
- Upload to IPFS and update NFT metadata
- One author = one prompt relationship

### Frontend (Future)

**Purpose:** 4-page MVP for users and creators

**Pages:**
1. Home/Explore - Browse creators, recent mints
2. Creator Page - Shareable profile, mint button
3. Creator Dashboard - Manage prompts, view earnings
4. My Collection - User's minted NFTs

### Cross-Cutting

**Target Mint Cost:** <$0.05 USD (includes creator reward, IPFS, generation, treasury)

**Testing:** Contracts MUST have comprehensive unit tests and integration tests before mainnet deployment

## Development Standards

### Code Quality

- Use consistent formatting (Prettier/Forge fmt)
- Run linters before commits (Solhint for contracts)
- Keep functions small and focused
- Avoid deep nesting (max 3 levels)

### Documentation

- README MUST explain how to set up and run the project
- Smart contracts MUST have NatSpec comments for public functions
- Complex business logic MUST have explanation comments
- Document deployment procedures and contract addresses

### Testing

- Smart contracts MUST have test coverage for all state transitions
- Critical payment flows MUST have dedicated test scenarios
- Test both happy paths and failure cases
- Mock external dependencies in tests

### Version Control

- Commit messages should be clear and descriptive
- Feature branches for new functionality
- Main branch always deployable for current season

## Governance

### Constitution Authority

This constitution defines the standards and principles for GLISK development. All code, specifications, and planning documents MUST align with these principles.

### Amendments

- Constitution can be amended when starting a new season or domain (backend/frontend)
- MINOR version bump when adding new principles or expanding existing ones
- PATCH version bump for clarifications or wording improvements
- MAJOR version bump when removing or fundamentally changing principles

### Compliance

- Specification documents MUST reference relevant constitutional principles
- Implementation plans MUST verify constitutional compliance before execution
- Code reviews MUST check adherence to simplicity and clarity standards
- Complexity violations MUST be explicitly justified in implementation plans

### Version Information

**Version**: 1.0.0 | **Ratified**: 2025-10-10 | **Last Amended**: 2025-10-10
