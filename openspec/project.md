# Project Context

## Purpose

GLISK is an NFT platform that transforms text prompts into AI-generated artwork on the blockchain. The project follows a **seasonal MVP philosophy** - each season (~1-3 months) is a complete, standalone experience with time-boxed development focusing on working code over long-term scalability.

**Core Value Proposition:**
- Users mint NFTs with text prompts at minimal cost (<$0.05 USD)
- AI generates unique artwork from prompts (Flux Schnell model)
- Automated pipeline handles detection → generation → IPFS storage → on-chain reveals
- Authors earn rewards claimable in USD
- Farcaster integration via Base mini app

**Live Demo:** [glisk.xyz](https://glisk.xyz)
**Contract:** `0xb43185E67D4Fb27115AC419C9F8A335cC0B837B9` (Base Mainnet)

## Tech Stack

### Smart Contracts
- **Language:** Solidity ^0.8.20
- **Framework:** Foundry (forge, anvil, cast)
- **Standards:** ERC721Enumerable, ERC2981 (royalties)
- **Libraries:** OpenZeppelin Contracts v5.x (AccessControl, ReentrancyGuard)
- **Network:** Base Mainnet (Ethereum L2)
- **Testing:** Foundry test framework (100% coverage requirement)

### Backend
- **Language:** Python 3.13 (standard GIL-enabled version)
- **Framework:** FastAPI ^0.119.0
- **Database:** PostgreSQL 17 (async via psycopg3)
- **ORM:** SQLModel ^0.0.27
- **Migrations:** Alembic ^1.17.0 + alembic-postgresql-enum
- **Logging:** structlog ^25.4.0
- **Testing:** pytest ^8.4.2 + testcontainers[postgres] ^4.13.2
- **Linting/Formatting:** Ruff ^0.14.1, Pyright ^1.1.406
- **Package Manager:** uv (hatchling build backend)
- **Web3:** web3.py ^7.14.0
- **Key Services:**
  - Replicate API ^1.0.7 (AI image generation)
  - Pinata (IPFS storage via requests)
  - Alchemy (webhooks, RPC)
  - SIWE ^4.4.0 (Sign-In with Ethereum)

### Frontend
- **Language:** TypeScript ~5.9.3
- **Framework:** React 19.1.1 (via Vite ^7.1.7)
- **Routing:** React Router DOM ^7.9.4
- **Build Tool:** Vite with @vitejs/plugin-react
- **Styling:** Tailwind CSS ^4.1.15 (utility-first)
- **UI Components:** shadcn/ui (@radix-ui primitives)
- **Web3:**
  - RainbowKit ^2.2.9 (wallet connection UI)
  - wagmi ^2.18.1 + viem ^2.38.3 (Ethereum interactions)
  - @coinbase/onchainkit ^1.1.1 (NFT components)
- **Farcaster:** @farcaster/miniapp-sdk ^0.2.1, @farcaster/auth-kit ^0.8.1
- **State Management:** React Query (@tanstack/react-query ^5.90.5)
- **Linting/Formatting:** ESLint ^9.38.0, Prettier ^3.6.2, typescript-eslint ^8.45.0
- **Theming:** next-themes ^0.4.6
- **Notifications:** sonner ^2.0.7
- **Icons:** lucide-react ^0.546.0, react-icons ^5.5.0

### Development Tools
- **Methodology:** GitHub Spec Kit (specification-driven development)
- **AI Assistance:** Anthropic Claude (Claude Code)
- **Pre-commit:** Husky ^9.1.7 + lint-staged ^16.2.4
- **Container:** Docker + docker-compose (PostgreSQL 17)

## Project Conventions

### Code Style

**Smart Contracts (Solidity):**
- Foundry formatter (`forge fmt`)
- Solhint for linting
- NatSpec comments for all public functions
- OpenZeppelin patterns for security-critical code

**Backend (Python):**
- Ruff for linting and formatting (line-length: 100)
- Pyright for type checking (basic mode)
- structlog for structured logging (JSON format)
- UTC enforcement for all datetime handling (`TZ=UTC`)
- Repository pattern (direct implementations, no generic base classes)

**Frontend (TypeScript):**
- ESLint + Prettier with consistent formatting
- TypeScript strict mode disabled (pragmatic MVP approach)
- JSDoc comments for complex component logic
- Direct wagmi hooks (no abstractions)
- Utility-first Tailwind CSS (no custom animations/gradients for MVP)

**Universal Rules:**
- Variable and function names MUST be descriptive
- Magic numbers/strings MUST be replaced with named constants
- Complex logic MUST have explanatory comments
- Avoid deep nesting (max 3 levels)
- Keep functions small and focused

### Architecture Patterns

**Monorepo Structure:**
```
/contracts/   - Smart contracts (Solidity)
/backend/     - Off-chain services (Python/FastAPI)
/frontend/    - Web application (React/TypeScript)
/specs/       - Feature specifications (deprecated)
/openspec/    - OpenSpec change proposals (active)
.specify/     - GitHub Spec Kit templates and constitution
```

**Backend Pipeline Architecture:**
```
Mint Event → Detection → Image Generation → IPFS Upload → Batch Reveal
            (webhook)   (Replicate AI)    (Pinata)     (on-chain)
```

**Key Patterns:**
- **Unit of Work (UoW):** Transaction boundaries with async context managers
- **Repository Pattern:** Direct implementations per domain entity
- **Worker Pattern:** Background polling workers (image generation, IPFS upload, reveal)
- **Event-Driven:** Alchemy webhooks trigger mint detection
- **Idempotency:** Database UNIQUE constraints prevent duplicate processing
- **Recovery:** CLI tools for manual token recovery via `nextTokenId()`

**Frontend Patterns:**
- Direct wagmi hooks (`useAccount`, `useWriteContract`, `useWaitForTransactionReceipt`)
- useState only for component state (no Redux/Zustand)
- Client-side routing with dynamic creator pages (`/{creatorAddress}`)
- Manual testing for MVP (automated tests deferred)

**Simplicity First:**
- Choose the simplest solution that solves the problem
- Avoid premature abstraction or over-engineering
- Prefer direct implementations over design patterns unless complexity is warranted
- Code should be readable and self-documenting

### Testing Strategy

**Smart Contracts (MANDATORY 100% coverage):**
- Foundry test framework
- Test all state transitions and payment flows
- Both happy paths and failure cases
- Gas optimization benchmarks
- Security-focused (reentrancy, access control, overflow)

**Backend (Pragmatic Coverage):**
- pytest + pytest-asyncio
- **Focus tests on complex logic:** FOR UPDATE SKIP LOCKED, state transitions, error handling
- **Skip testing simple CRUD operations** (trust SQLModel)
- Real databases via testcontainers (no mocks)
- Test migration idempotency: `alembic downgrade base && alembic upgrade head`
- **MANDATORY:** All tests must pass before starting new phases

**Frontend (Manual for MVP):**
- Manual testing of wallet connection, transaction flows, edge cases
- Automated tests deferred to post-MVP
- Browser compatibility testing (Chrome, Safari, mobile)

**Phase-Based Testing (MANDATORY Workflow):**
```bash
# Before starting each phase
cd backend && uv run pytest tests/ -v

# After completing each phase
cd backend && uv run pytest tests/ -v
# If tests fail = BLOCKER. Fix before next phase.
```

### Git Workflow

**Branching:**
- `main` branch always deployable for current season
- Feature branches for new functionality
- Merge with `--no-ff` to preserve history
- Branch naming: `feature/description` or `fix/description`

**Commit Conventions:**
- Clear, descriptive commit messages
- Claude Code format: ends with AI attribution
- **MANDATORY:** Never bypass pre-commit hooks
  - ❌ FORBIDDEN: `git commit --no-verify` or `git commit -n`
  - If hook fails: Fix the issue, don't skip

**Pre-commit Hooks:**
- Ruff (backend linting/formatting)
- Prettier + ESLint (frontend)
- Type checking (Pyright, TypeScript)
- Must pass before commit accepted

**Pull Request Flow:**
- Claude Code auto-generates PR descriptions with test plan
- Reviews check constitutional compliance (simplicity, clarity)
- Complexity violations MUST be explicitly justified

## Domain Context

### NFT Minting & Blockchain
- **ERC-721 standard** with custom batch minting (`BatchMinted` events)
- **Fixed ETH price** stored on-chain (admin-updatable for volatility)
- **Payment distribution:** creator percentage (claimable) + treasury
- **Season finalization** with countdown for unclaimed rewards (`sweepDust`)
- **Batch reveals** for gas optimization (50 tokens per transaction)
- **On-chain storage:** author address only
- **Off-chain storage (IPFS):** social handles, prompt text, generation params, images

### AI Image Generation
- **Model:** Flux Schnell via Replicate API
- **Prompt validation:** Content policy enforcement
- **Fallback prompt:** "Cute kittens playing with yarn balls..." (censorship)
- **Retry logic:** Exponential backoff (3 attempts max)
- **Idempotency:** `generation_attempts` counter prevents infinite retries

### IPFS & Metadata
- **Provider:** Pinata (JWT authentication)
- **ERC721 metadata format:** `{"name": "...", "description": "...", "image": "ipfs://..."}`
- **Token URI:** `ipfs://<metadata_cid>`
- **Image URI:** `ipfs://<image_cid>`
- **Gateway:** `gateway.pinata.cloud`

### Farcaster Integration
- **Base mini app:** Native Farcaster client integration
- **Auth Kit:** Sign-In with Farcaster (SIWE)
- **Miniapp SDK:** Context API for user data

### Database Schema
- **Primary table:** `tokens_s0` (Season 0 tokens)
- **Audit tables:** `ipfs_upload_records`, `reveal_transactions`
- **UTC enforcement:** Application-level (no timezone-aware PostgreSQL types)
- **Alembic workflow:** Autogenerate from SQLModel changes, manual review

## Important Constraints

### Seasonal Lifecycle
- **Duration:** ~1-3 months per season
- **Philosophy:** Solutions need only survive one season
- **Technical debt:** Acceptable if it doesn't compromise core functionality or security
- **Rebuild strategy:** Fresh insights each season vs. maintaining legacy code forever

### Blockchain & Network
- **Target chain:** Base (Ethereum L2) ONLY
- **Network config:** Environment-driven (BASE_SEPOLIA or BASE_MAINNET)
- **Contract addresses:** Must match selected network (see `contracts/deployments/`)
- **Gas optimization:** Critical for <$0.05 mint cost
- **Immutability:** Contracts can't be patched post-deployment

### Security Requirements
- **Smart contracts:** Security over feature richness
- **Payment flows:** Must be auditable and tested
- **Access controls:** Admin functions with appropriate guards
- **HMAC validation:** Alchemy webhooks (constant-time comparison)
- **No secrets in version control:** .env files for sensitive data

### Cost Constraints
- **Target mint cost:** <$0.05 USD total
  - Creator reward
  - IPFS storage
  - AI generation
  - Treasury fee
  - Gas costs

### Development Speed
- **Optimize for iteration speed and clarity**
- **Ship working features quickly over perfect architecture**
- **Document tradeoffs explicitly when taking shortcuts**

## External Dependencies

### Blockchain Services
- **Alchemy:**
  - Webhooks (mint event detection)
  - RPC provider (blockchain reads/writes)
  - Requires: `ALCHEMY_API_KEY`, `ALCHEMY_WEBHOOK_SECRET`
  - Rate limits: Standard tier (check dashboard)

### AI Services
- **Replicate:**
  - Model: `black-forest-labs/flux-schnell`
  - Authentication: JWT token
  - Requires: `REPLICATE_API_TOKEN`
  - Rate limits: Check account quota
  - SLA: ~2-10 seconds per generation

### Storage Services
- **Pinata (IPFS):**
  - File uploads: `pinFileToIPFS`
  - JSON metadata: `pinJSONToIPFS`
  - Authentication: JWT token
  - Requires: `PINATA_JWT`, `PINATA_GATEWAY`
  - Rate limits: 180 requests/minute (free tier)
  - Storage quota: Check account dashboard

### Infrastructure
- **PostgreSQL 17:**
  - Connection pool: 200 connections
  - Async driver: psycopg3
  - Extensions: None required
  - Docker deployment: `docker-compose.yml`

- **Base Network:**
  - Mainnet RPC: Via Alchemy
  - Sepolia RPC: Via Alchemy (testnet)
  - Block explorer: basescan.org
  - Gas price volatility: High (affects reveal timing)

### Farcaster
- **Miniapp SDK:**
  - Context API for user sessions
  - Auth Kit for SIWE flows
  - Requires Farcaster-compatible client (Warpcast, etc.)

### Development Tools
- **Foundry:** Solidity compiler, testing, deployment
- **Docker:** PostgreSQL container
- **GitHub:** Spec Kit templates, version control
- **Claude Code:** AI-assisted development

## Working Directory

**Repository root:** `/Users/nikita/PycharmProjects/glisk`

**Key paths:**
- Smart contracts: `contracts/src/`
- Backend code: `backend/src/glisk/`
- Frontend code: `frontend/src/`
- Tests: `backend/tests/`, `contracts/test/`
- Migrations: `backend/alembic/versions/`
- Documentation: `specs/`, `openspec/`
- Constitution: `.specify/memory/constitution.md`

**Docker commands:** Always use `docker exec backend-postgres-1` for PostgreSQL access (works from anywhere)

**Python commands:** Run from `backend/` directory (e.g., `uv run pytest`, `uv run alembic`)

**Contract commands:** Run from `contracts/` directory (e.g., `forge build`, `forge test`)

## Additional Notes

### Alembic Migration Workflow (MANDATORY Order)
1. **Update SQLModel models first** (`backend/src/glisk/db/models.py`)
2. **Autogenerate migration:** `uv run alembic revision --autogenerate -m "description"`
3. **Review generated migration** (check indexes, constraints, enums)
4. **Apply migration:** `uv run alembic upgrade head`
5. **Verify schema:** `docker exec backend-postgres-1 psql -U glisk -d glisk -c "\d table_name"`

Models are source of truth. Never write migrations before updating models.

### Constitutional Authority
This project follows `.specify/memory/constitution.md` (v1.2.0) for all development decisions. Key principles:
1. **Simplicity First** - Clear and elegant code above all else
2. **Seasonal MVP Philosophy** - Fast delivery over long-term scalability
3. **Monorepo Structure** - Clear domain separation
4. **Smart Contract Security** - Security and correctness over feature richness
5. **Clear Over Clever** - Favor clarity and directness

All code, specifications, and planning documents MUST align with constitutional principles.

### OpenSpec Workflow
Active change management via `openspec/` directory. When planning new features or architectural changes, create OpenSpec proposals (`/openspec:proposal`). See `openspec/AGENTS.md` for workflow.

Deprecated: `specs/` directory (GitHub Spec Kit v1) - kept for historical reference but not actively maintained.
