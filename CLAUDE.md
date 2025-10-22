# glisk Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-10-10

## Active Technologies
- Solidity ^0.8.20 + OpenZeppelin Contracts v5.x (ERC721Enumerable, AccessControl, ReentrancyGuard, ERC2981) (001-full-smart-contract)
- Markdown for command definitions, Bash for orchestration scripts (002-smart-contract-audit)
- File-based (audit history in `.audit/` directory, results as markdown reports) (002-smart-contract-audit)
- Python 3.13 (standard GIL-enabled version) + FastAPI, SQLModel, psycopg3 (async), Alembic, Pydantic BaseSettings, structlog, pytest, testcontainers (003-003a-backend-foundation)
- PostgreSQL 14+ with 200 connection pool, UTC timestamps, JSONB suppor (003-003a-backend-foundation)
- React 18 + TypeScript (via Vite) (005-frontend-foundation-with)
- N/A (stateless frontend, no persistence) (005-frontend-foundation-with)
- Python 3.13 (backend), TypeScript 5.x (frontend) (007-link-x-twitter)
- React 18 + TypeScript (via Vite), Python 3.13 (backend) (008-unified-profile-page)
- TypeScript 5.x + React 18 (frontend), Python 3.13 (backend for new API endpoint) + @coinbase/onchainkit (NFTCard components), wagmi + viem (blockchain reads), react-router-dom (query param navigation) (008-unified-profile-page)
- N/A (frontend reads from backend API and blockchain RPC) (008-unified-profile-page)
- PostgreSQL 14+ (existing database with tokens_s0 table) (009-create-a-main)

## Project Structure
```
src/
tests/
```

## Commands

### Smart Contract Audit Commands

**Purpose**: Automated security auditing for Solidity contracts using Slither and Mythril.

#### `/audit [contract-path]`
Run comprehensive security audit on a contract.

**Usage**:
```bash
/audit contracts/src/GliskNFT.sol    # Audit specific contract
/audit                                # Auto-detect contract
```

**What it does**:
- Executes Slither (static analysis) and Mythril (symbolic execution)
- Analyzes findings with INoT (Introspection of Thought) multi-perspective analysis
- Generates beginner-friendly explanations for all findings
- Calculates security score (0-100)
- Provides deployment readiness decision
- Saves audit history and reports to `.audit/` directory

**Execution time**: 3-5 minutes for 500-1500 line contracts

**Prerequisites**:
- Foundry (forge) - Required for compilation
- Slither - Required for static analysis (install via `pip3 install slither-analyzer` or use `uvx`)
- Mythril - Optional for symbolic execution (install via `pip3 install mythril`)
- Tests - Recommended for coverage analysis

**Configuration**: Edit `.audit/config.json` to customize:
- Tool paths and timeouts
- False positive patterns (OpenZeppelin patterns included by default)
- Security score weights (Critical: 40%, High: 30%, Medium: 15%, Coverage: 10%, Best Practices: 5%)
- Contract size limits (default: 1500 lines max)
- INoT analysis settings for multi-perspective security analysis

**Output**:
- Executive summary with deployment readiness decision
- Security score (0-100) with detailed breakdown
- Findings categorized by severity (Critical, High, Medium, Low, Informational)
- Beginner-friendly explanations for each finding
- Code references with line numbers
- Actionable recommendations with fix examples
- Test coverage integration

#### `/audit.report [contract-name]`
View and compare audit reports.

**Usage**:
```bash
/audit.report glisknft                      # View latest report
/audit.report glisknft --list               # List all audits
/audit.report glisknft --compare id1 id2    # Compare two audits
```

**Features**:
- Track audit history across multiple runs
- Compare security scores and findings over time
- Identify trends (improving/degrading/stable)
- View detailed comparison of fixed/new/unchanged findings

### Audit Best Practices

1. **Run audits at key milestones**: After major features, before deployment
2. **Track history**: Use `/audit.report --list` to monitor security trends
3. **Understand findings**: Read beginner explanations, don't just look at scores
4. **Complement with professional audits**: Automated tools find common issues, but hire professionals for mainnet
5. **Maintain test coverage**: Higher coverage = more accurate audit results

### Common Issues and Troubleshooting

For detailed troubleshooting, see `.audit/TROUBLESHOOTING.md`. Quick reference:

**"Slither not found"**:
```bash
# Option 1: Ephemeral execution (recommended)
uvx --from slither-analyzer slither --version

# Option 2: Global installation
pip3 install slither-analyzer
```

**"Contract compilation failed"**:
```bash
cd contracts
forge build                  # Check errors
forge install               # Install dependencies
forge clean && forge build  # Clean build
```

**"Mythril timeout"**:
- Edit `.audit/config.json` and increase `tools.mythril.timeout_seconds` (default: 300)
- Complex loops may cause timeouts - consider contract refactoring
- Audit will continue with Slither results only

**"Too many false positives"**:
- OpenZeppelin patterns are auto-detected
- Add custom patterns to `.audit/config.json` → `false_positive_patterns`
- Review INoT analysis explanations - they explain why findings are false positives

**"Contract exceeds size limit"**:
- Default limit: 1500 lines (configurable in `.audit/config.json`)
- Consider splitting into smaller contracts
- Large contracts may produce incomplete/timeout results

### Audit Data Structure

```
.audit/                          # Gitignored by default
├── config.json                  # Audit configuration
├── history/                     # Audit run metadata (JSON)
│   └── {contract-name}/
│       └── {timestamp}-audit.json
├── raw/                         # Raw tool outputs
│   ├── {audit-id}-slither.json
│   └── {audit-id}-mythril.json
├── reports/                     # Markdown reports (can commit these)
│   └── {contract-name}/
│       └── {timestamp}-audit-report.md
└── findings/                    # Intermediate analysis data
    └── {audit-id}-findings.json
```

## Smart Contract Development

After modifying contracts, sync the ABI to backend:

```bash
./sync-abi.sh
```

## Code Style
Solidity ^0.8.20: Follow standard conventions

## Backend Features

### Mint Event Detection System (003-003b-event-detection)

**Status**: ✅ Complete (Phases 1-6 implemented)

**Purpose**: Real-time blockchain event detection for NFT mints via Alchemy webhooks.

**Features Implemented**:
- ✅ Phase 1: Setup (web3.py dependency, Alchemy configuration)
- ✅ Phase 2: Foundational security (HMAC signature validation with constant-time comparison)
- ✅ Phase 3: Webhook authentication (signature validation dependency, unit tests)
- ✅ Phase 4: Real-time mint detection (POST /webhooks/alchemy endpoint, event parsing, database storage)
- ✅ Phase 6: Polish (structured logging, quickstart validation tests, code review, documentation)

**Key Files**:
- `backend/src/glisk/api/routes/webhooks.py` - Webhook endpoint (POST /webhooks/alchemy)
- `backend/src/glisk/services/blockchain/alchemy_signature.py` - HMAC-SHA256 signature validation
- `backend/tests/test_quickstart.py` - Quickstart validation test suite

**Usage**:

*Webhook Endpoint* (Real-time detection):
```bash
# Endpoint receives Alchemy webhooks at POST /webhooks/alchemy
# Validates HMAC signature, parses BatchMinted events, stores to database
# See specs/003-003b-event-detection/quickstart.md for setup
```

**Configuration** (.env):
```bash
ALCHEMY_API_KEY=your_api_key
ALCHEMY_WEBHOOK_SECRET=your_signing_key
GLISK_NFT_CONTRACT_ADDRESS=0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0
NETWORK=BASE_SEPOLIA
GLISK_DEFAULT_AUTHOR_WALLET=0x0000000000000000000000000000000000000001
```

**Testing**:
```bash
# Run all tests (includes quickstart validation)
cd backend
TZ=America/Los_Angeles uv run pytest tests/ -v

# Run quickstart validation only
TZ=America/Los_Angeles uv run pytest tests/test_quickstart.py -v
```

**Documentation**:
- Specification: `specs/003-003b-event-detection/spec.md`
- Implementation Plan: `specs/003-003b-event-detection/plan.md`
- Quickstart Guide: `specs/003-003b-event-detection/quickstart.md`
- API Contracts: `specs/003-003b-event-detection/contracts/`
- Research Notes: `specs/003-003b-event-detection/research.md`

**Next Steps** (Future features):
- 003-003c: Image Generation (process detected events → generate AI images)
- 003-003d: IPFS Upload & Metadata (upload images, update token URIs)

---

### Image Generation Worker (003-003c-image-generation)

**Status**: ✅ Complete (Phases 1-6 implemented)

**Purpose**: Background worker that polls for newly detected NFT mint events, generates AI images using Replicate API with the author's text prompt, and updates token records with generated image URLs.

**Features Implemented**:
- ✅ Phase 1: Setup (Replicate SDK dependency, environment configuration)
- ✅ Phase 2: Foundational (database schema extensions, error classification hierarchy)
- ✅ Phase 3: User Story 1 - Automatic image generation for detected tokens
- ✅ Phase 4: User Story 2 - Resilient retries with exponential backoff
- ✅ Phase 5: User Story 3 - Graceful failure handling and error visibility
- ✅ Phase 6: Polish (configuration validation, schema verification, code cleanup, documentation)

**Key Files**:
- `backend/src/glisk/workers/image_generation_worker.py` - Polling loop with lifecycle management
- `backend/src/glisk/services/image_generation/replicate_client.py` - Replicate API integration
- `backend/src/glisk/services/image_generation/prompt_validator.py` - Prompt validation logic
- `backend/src/glisk/repositories/token.py` - Repository methods for token updates
- `backend/alembic/versions/*_add_image_generation_fields.py` - Database migration

**Worker Lifecycle**:

The worker starts automatically with the FastAPI application and runs as a background task:

```bash
cd backend
uv run uvicorn glisk.main:app --reload

# Worker logs on startup:
# INFO: worker.started poll_interval=1 batch_size=10
```

**Configuration** (.env):

```bash
# Required
REPLICATE_API_TOKEN=r8_YourApiTokenHere123456789

# Optional (defaults shown)
REPLICATE_MODEL_VERSION=black-forest-labs/flux-schnell
FALLBACK_CENSORED_PROMPT="Cute kittens playing with yarn balls in a sunny meadow with flowers"
POLL_INTERVAL_SECONDS=1
WORKER_BATCH_SIZE=10
```

**Testing**:

```bash
# Run all tests
cd backend
TZ=America/Los_Angeles uv run pytest tests/ -v

# Manual testing per quickstart.md
# Test 1: Single token generation
# Test 2: Transient failure with retry
# Test 3: Content policy violation with fallback
```

**Monitoring**:

Query token status to monitor worker progress:

```bash
# Count tokens by status
docker exec backend-postgres-1 psql -U glisk -d glisk -c "SELECT status, COUNT(*) FROM tokens_s0 GROUP BY status"

# Check queue depth (pending generation)
docker exec backend-postgres-1 psql -U glisk -d glisk -c "SELECT COUNT(*) FROM tokens_s0 WHERE status='detected'"

# Inspect failed tokens
docker exec backend-postgres-1 psql -U glisk -d glisk -c "SELECT token_id, generation_attempts, generation_error FROM tokens_s0 WHERE status='failed' ORDER BY mint_timestamp DESC LIMIT 10"
```

**Structured Log Events**:

```bash
# Monitor worker health
tail -f backend/logs/glisk.log | grep "worker\."

# Track generation events
tail -f backend/logs/glisk.log | grep "token\.generation"

# Audit censorship events
tail -f backend/logs/glisk.log | grep "token\.censored"
```

**Manual Recovery**:

Reset failed tokens after resolving issues (e.g., API outage, bad configuration):

```bash
# Reset specific token
docker exec backend-postgres-1 psql -U glisk -d glisk <<EOF
UPDATE tokens_s0
SET status = 'detected', generation_attempts = 0, generation_error = NULL
WHERE token_id = 123;
EOF

# Bulk reset after outage (tokens with retry budget remaining)
docker exec backend-postgres-1 psql -U glisk -d glisk <<EOF
UPDATE tokens_s0
SET status = 'detected', generation_error = NULL
WHERE status = 'failed' AND generation_attempts < 3;
EOF
```

**Performance Tuning**:

```bash
# Reduce CPU usage (increase polling interval)
POLL_INTERVAL_SECONDS=5  # Default: 1

# Reduce concurrent load (avoid rate limits)
WORKER_BATCH_SIZE=3  # Default: 10

# Increase throughput (high volume)
WORKER_BATCH_SIZE=20  # Default: 10
```

**Common Issues**:

| Issue | Diagnosis | Resolution |
|-------|-----------|------------|
| Tokens stuck in 'generating' | Worker crash | Restart worker (triggers auto-recovery) |
| High failure rate | Check `generation_error` distribution | Fix REPLICATE_API_TOKEN or reduce batch size |
| Slow generation (>2 min) | Model latency | Switch to faster model (flux-schnell) |
| Worker not starting | Missing config | Verify REPLICATE_API_TOKEN in .env |

**Documentation**:
- Specification: `specs/003-003c-image-generation/spec.md`
- Implementation Plan: `specs/003-003c-image-generation/plan.md`
- Quickstart Guide: `specs/003-003c-image-generation/quickstart.md`
- Internal Contracts: `specs/003-003c-image-generation/contracts/internal-service-contracts.md`
- Data Model: `specs/003-003c-image-generation/data-model.md`
- Research Notes: `specs/003-003c-image-generation/research.md`

**Next Steps** (Future features):
- 003-003d: IPFS Upload & Reveal ✅ COMPLETE
- 003-003e: Future enhancements (admin APIs, health endpoints, custom monitoring)

---

### IPFS Upload and Batch Reveal (003-003d-ipfs-reveal)

**Status**: ✅ Complete (Phases 1-6 implemented)

**Purpose**: Completes the MVP pipeline by uploading generated images to IPFS via Pinata, creating ERC721-compliant metadata, and batch-revealing tokens on-chain for gas optimization.

**Features Implemented**:
- ✅ Phase 1: Setup (requests library, error hierarchy, Pinata/keeper configuration)
- ✅ Phase 2: Foundational (database schema extensions, audit tables, repositories)
- ✅ Phase 3: User Story 1 - Automatic IPFS upload for images and metadata
- ✅ Phase 4: User Story 2 - Automatic batch reveal on blockchain
- ✅ Phase 5: User Story 3 - Resilient error handling with exponential backoff and recovery
- ✅ Phase 6: Polish (documentation, validation, configuration reference)

**Key Files**:
- `backend/src/glisk/workers/ipfs_upload_worker.py` - IPFS upload worker (140 LOC)
- `backend/src/glisk/workers/reveal_worker.py` - Batch reveal worker (150 LOC)
- `backend/src/glisk/services/ipfs/pinata_client.py` - Pinata IPFS client (80 LOC)
- `backend/src/glisk/services/blockchain/keeper.py` - Blockchain keeper service (100 LOC)
- `backend/src/glisk/repositories/token.py` - Extended with upload/reveal methods
- `backend/alembic/versions/*_add_ipfs_reveal_fields.py` - Three migrations for schema

**Worker Lifecycle**:

Both workers start automatically with the FastAPI application:

```bash
cd backend
uv run uvicorn glisk.main:app --reload

# Worker logs on startup:
# INFO: worker.started worker_type=ipfs_upload poll_interval=1 batch_size=10
# INFO: worker.started worker=reveal_worker poll_interval=1 batch_max_size=50
```

**Configuration** (.env):

```bash
# IPFS Upload (Pinata) - Required
PINATA_JWT=your_pinata_jwt_token_here
PINATA_GATEWAY=gateway.pinata.cloud

# Blockchain Keeper - Required
KEEPER_PRIVATE_KEY=0xYOUR_KEEPER_PRIVATE_KEY_HERE_64_HEX_CHARS
KEEPER_GAS_STRATEGY=medium
REVEAL_GAS_BUFFER=1.2
REVEAL_MAX_GAS_PRICE_GWEI=50  # Optional: Skip reveals when gas exceeds this (prevents overpaying)
TRANSACTION_TIMEOUT_SECONDS=180

# Worker Configuration - Optional
POLL_INTERVAL_SECONDS=1
WORKER_BATCH_SIZE=10
BATCH_REVEAL_WAIT_SECONDS=5
BATCH_REVEAL_MAX_TOKENS=50
```

**Setup Requirements**:

1. **Pinata Account** (IPFS storage):
   - Sign up at https://pinata.cloud
   - Create API key with `pinFileToIPFS` and `pinJSONToIPFS` permissions
   - Copy JWT token to `PINATA_JWT`

2. **Keeper Wallet** (blockchain transactions):
   - Generate new wallet: `cast wallet new` (Foundry)
   - Fund wallet with ETH on Base Sepolia (for gas)
   - Copy private key to `KEEPER_PRIVATE_KEY`

**Testing**:

```bash
# Run all tests
cd backend
TZ=America/Los_Angeles uv run pytest tests/ -v

# Manual testing per quickstart.md
# Test 1: IPFS upload single token
# Test 2: Batch reveal multiple tokens
# Test 3: IPFS upload failure handling
# Test 4: Reveal transaction revert handling
```

**Monitoring**:

Query token status and audit tables to monitor pipeline:

```bash
# Count tokens by status
docker exec backend-postgres-1 psql -U glisk -d glisk -c "SELECT status, COUNT(*) FROM tokens_s0 GROUP BY status"

# Check IPFS upload queue depth
docker exec backend-postgres-1 psql -U glisk -d glisk -c "SELECT COUNT(*) FROM tokens_s0 WHERE status='uploading'"

# Check reveal queue depth
docker exec backend-postgres-1 psql -U glisk -d glisk -c "SELECT COUNT(*) FROM tokens_s0 WHERE status='ready'"

# Inspect IPFS upload audit trail
docker exec backend-postgres-1 psql -U glisk -d glisk -c "SELECT token_id, upload_type, status, ipfs_cid FROM ipfs_upload_records ORDER BY created_at DESC LIMIT 10"

# Inspect reveal transactions
docker exec backend-postgres-1 psql -U glisk -d glisk -c "SELECT reveal_id, tx_hash, array_length(token_ids, 1) as batch_size, status, gas_used FROM reveal_transactions ORDER BY submitted_at DESC LIMIT 10"
```

**Structured Log Events**:

```bash
# Monitor IPFS upload worker health
tail -f backend/logs/glisk.log | grep "ipfs\."

# Monitor reveal worker health
tail -f backend/logs/glisk.log | grep "reveal\."

# Track worker lifecycle events
tail -f backend/logs/glisk.log | grep "worker\."

# Audit transient errors (retries)
tail -f backend/logs/glisk.log | grep "transient_error"

# Audit permanent errors (manual investigation needed)
tail -f backend/logs/glisk.log | grep "permanent_error"
```

**Manual Recovery**:

Reset tokens after resolving issues:

```bash
# Reset specific token stuck in 'uploading'
docker exec backend-postgres-1 psql -U glisk -d glisk <<EOF
UPDATE tokens_s0
SET status = 'uploading', generation_attempts = 0, generation_error = NULL
WHERE token_id = 123;
EOF

# Bulk reset after IPFS service outage
docker exec backend-postgres-1 psql -U glisk -d glisk <<EOF
UPDATE tokens_s0
SET status = 'uploading', generation_error = NULL
WHERE status = 'failed' AND generation_attempts < 3;
EOF

# Reset tokens stuck in 'ready' after reveal issues
docker exec backend-postgres-1 psql -U glisk -d glisk <<EOF
UPDATE tokens_s0
SET status = 'ready'
WHERE token_id IN (SELECT unnest(token_ids) FROM reveal_transactions WHERE status = 'failed');
EOF
```

**Performance Tuning**:

```bash
# Reduce IPFS upload worker CPU usage
POLL_INTERVAL_SECONDS=5  # Default: 1
WORKER_BATCH_SIZE=3  # Default: 10

# Optimize reveal batch efficiency (more tokens = better gas efficiency)
BATCH_REVEAL_MAX_TOKENS=50  # Default: 50
BATCH_REVEAL_WAIT_SECONDS=10  # Default: 5 (wait longer for fuller batches)

# Increase gas safety buffer for volatile gas markets
REVEAL_GAS_BUFFER=1.5  # Default: 1.2 (20% buffer)

# Prevent overpaying during gas spikes (skip reveals until gas drops)
REVEAL_MAX_GAS_PRICE_GWEI=50  # Optional: Reject transactions exceeding this price

# Reduce transaction timeout for faster failure detection
TRANSACTION_TIMEOUT_SECONDS=120  # Default: 180
```

**Common Issues**:

| Issue | Diagnosis | Resolution |
|-------|-----------|------------|
| Tokens stuck in 'uploading' | Worker crash | Restart worker (triggers auto-recovery) |
| IPFS upload 401/403 errors | Invalid/expired JWT | Check `PINATA_JWT` configuration, regenerate at pinata.cloud |
| Reveal transaction reverts | Invalid token IDs | Check token state on-chain at basescan.org |
| Keeper wallet insufficient funds | Low ETH balance | Fund keeper wallet with ETH for gas |
| Slow reveal confirmations | Network congestion | Set `REVEAL_MAX_GAS_PRICE_GWEI` to skip during high gas, or increase `REVEAL_GAS_BUFFER` |
| Reveals skipped during gas spikes | High gas prices | Normal behavior if `REVEAL_MAX_GAS_PRICE_GWEI` set. Reveals resume when gas drops |
| Orphaned pending transactions | Worker restart during tx | Worker auto-recovers on startup, checks blockchain receipts |

**Error Messages Guide**:

The system provides actionable error messages:

- **401 Unauthorized (IPFS)**: "Check PINATA_JWT configuration in .env file. Verify JWT token is active at https://app.pinata.cloud/developers/api-keys"
- **403 Forbidden (IPFS)**: "Check PINATA_JWT permissions (requires pinFileToIPFS access). Verify account status and quota limits at https://app.pinata.cloud/billing"
- **Gas estimation failure**: "Keeper wallet has insufficient balance for gas. Check balance at {keeper_address}. Fund wallet or adjust REVEAL_GAS_BUFFER setting."
- **Gas price too high**: "Gas price too high (X.XX Gwei > cap Y.YY Gwei). Waiting for lower gas prices." - Reveals will be skipped until gas drops below configured REVEAL_MAX_GAS_PRICE_GWEI
- **Transaction revert**: "Verify token IDs are valid and metadata URIs match format 'ipfs://<CID>'. Check transaction details at https://sepolia.basescan.org/tx/{tx_hash}"

**State Transitions**:

```
detected → generating → uploading → ready → revealed
            ↓              ↓          ↓
          failed       failed     failed
```

- `uploading`: IPFS upload worker processes token
- `ready`: Token has IPFS CIDs, awaiting batch reveal
- `revealed`: Token revealed on-chain with transaction hash

**Documentation**:
- Specification: `specs/003-003d-ipfs-reveal/spec.md`
- Implementation Plan: `specs/003-003d-ipfs-reveal/plan.md`
- Quickstart Guide: `specs/003-003d-ipfs-reveal/quickstart.md`
- Internal Contracts: `specs/003-003d-ipfs-reveal/contracts/internal-service-contracts.md`
- Data Model: `specs/003-003d-ipfs-reveal/data-model.md`
- Research Notes: `specs/003-003d-ipfs-reveal/research.md`

**Next Steps** (Future features):
- 003-003e: Admin APIs for manual token management
- 003-003f: Health endpoints and custom monitoring dashboards
- 003-003g: Advanced gas optimization strategies

---

### Token Recovery via nextTokenId (004-recovery-1-nexttokenid)

**Status**: 🚧 In Progress (Phases 1-4 complete)

**Purpose**: Simplified token recovery mechanism that queries the smart contract's `nextTokenId()` counter to identify missing tokens in the database, then creates records with accurate author attribution from on-chain data.

**Features Implemented**:
- ✅ Phase 1: Setup (prerequisites verification)
- ✅ Phase 2: Foundational (nextTokenId() contract getter, redeploy)
- ✅ Phase 3: User Story 1 - Automatic token discovery with author attribution
- ✅ Phase 4: User Story 2 - Remove unused metadata fields (mint_timestamp, minter_address)
- ⏳ Phase 5: User Story 3 - Deprecate event-based recovery (in progress)

**Key Files**:
- `backend/src/glisk/services/blockchain/token_recovery.py` - Recovery service using nextTokenId
- `backend/src/glisk/cli/recover_tokens.py` - CLI command for token recovery
- `backend/src/glisk/repositories/token.py` - get_missing_token_ids() query
- `contracts/src/GliskNFT.sol` - nextTokenId() public getter

**Usage**:

*Token Recovery CLI*:
```bash
cd backend

# Run recovery (automatically queries contract and fills gaps)
python -m glisk.cli.recover_tokens

# Limit number of tokens to recover
python -m glisk.cli.recover_tokens --limit 100

# Dry run (preview without persisting changes)
python -m glisk.cli.recover_tokens --dry-run

# Combined
python -m glisk.cli.recover_tokens --limit 50 --dry-run
```

**How It Works**:
1. Queries `contract.nextTokenId()` to get total minted tokens
2. Uses PostgreSQL `generate_series()` to find missing token IDs in database
3. For each missing token, queries `contract.tokenPromptAuthor(tokenId)` for accurate author
4. Creates token records with `status='detected'` for image generation pipeline
5. Handles race conditions via database UNIQUE constraint on token_id

**Configuration** (.env):
```bash
# Already configured from 003-003b-event-detection
ALCHEMY_API_KEY=your_api_key
GLISK_NFT_CONTRACT_ADDRESS=0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0
NETWORK=BASE_SEPOLIA
```

**Testing**:
```bash
# Run all tests
cd backend
TZ=America/Los_Angeles uv run pytest tests/ -v

# Run recovery-specific tests only
TZ=America/Los_Angeles uv run pytest tests/test_token_recovery.py -v
```

**Advantages over Event-Based Recovery**:
- ✅ Simpler: No event log parsing, no checkpoint management
- ✅ Faster: Single contract call + efficient SQL query
- ✅ Accurate: Author attribution from `tokenPromptAuthor()` mapping
- ✅ Maintainable: ~60% less code (200+ LOC removed)

**Documentation**:
- Specification: `specs/004-recovery-1-nexttokenid/spec.md`
- Implementation Plan: `specs/004-recovery-1-nexttokenid/plan.md`
- Quickstart Guide: `specs/004-recovery-1-nexttokenid/quickstart.md`
- Data Model: `specs/004-recovery-1-nexttokenid/data-model.md`
- Research Notes: `specs/004-recovery-1-nexttokenid/research.md`

---

## Recent Changes
- 009-create-a-main: Added PostgreSQL 14+ (existing database with tokens_s0 table)
- 008-unified-profile-page: Added TypeScript 5.x + React 18 (frontend), Python 3.13 (backend for new API endpoint) + @coinbase/onchainkit (NFTCard components), wagmi + viem (blockchain reads), react-router-dom (query param navigation)
- 008-unified-profile-page: Added React 18 + TypeScript (via Vite), Python 3.13 (backend)

<!-- MANUAL ADDITIONS START -->

## Dependency & Environment Awareness

When encountering unexpected behavior with dependencies or tools:

**Core Principle**: Distinguish between "I made a mistake" vs "something external is wrong"

### Before Applying Workarounds, Ask:
- Is this behavior expected for this library/tool version?
- Could the environment be misconfigured? (wrong version, not activated, missing prerequisites)
- Am I using outdated knowledge about this library's API?
- Would my fix degrade the solution? (downgrading versions, removing features, disabling checks)

### If Uncertain About Root Cause:
1. **Investigate first** - check versions, environment state, library documentation
2. **If environment issue suspected** - STOP, explain findings, present options (including user actions if needed)
3. **If degrading solution** - present alternatives and let user choose
4. **If my knowledge may be outdated** - check current documentation or inform user

**Examples of "stop and diagnose":**
- Version conflicts → check if environment needs update, don't auto-downgrade
- Tool showing unusual errors → verify environment activation/configuration
- API not working as expected → check if library updated beyond my knowledge
- Installation failures → check system prerequisites before trying workarounds

**Simple mistakes to fix immediately:**
- Forgot an import, config edit, or installation command

## Working Directory Management

**Always work from repo root**: `/Users/nikita/PycharmProjects/glisk`

### Rules
1. Run `pwd` before commands if uncertain
2. Stay at repo root unless necessary
3. Use `docker exec` for container commands (works from anywhere)

### Key Paths
- `docker compose` → Run from repo root (docker-compose.yml location)
- `uv run pytest/alembic` → Run from backend/ directory
- Backend code: `backend/src/glisk/`
- Tests: `backend/tests/`

### Recovery
```bash
pwd  # Check location
cd /Users/nikita/PycharmProjects/glisk  # Return to root
```

## Alembic Migration Workflow (Database Schema Changes)

**MANDATORY Order**: Always update SQLModel models FIRST, then autogenerate migrations from model changes.

### Correct Workflow
```bash
cd backend

# 1. UPDATE MODELS FIRST
# Edit backend/src/glisk/db/models.py to add/modify SQLModel fields
# Example: Add new fields to Token model

# 2. AUTOGENERATE MIGRATION
uv run alembic revision --autogenerate -m "descriptive_migration_name"

# 3. REVIEW GENERATED MIGRATION
# Check alembic/versions/XXXX_descriptive_migration_name.py
# Verify upgrade() and downgrade() logic
# Edit if needed (add indexes, constraints, data migrations)

# 4. APPLY MIGRATION
uv run alembic upgrade head

# 5. VERIFY SCHEMA
docker exec backend-postgres-1 psql -U glisk -d glisk -c "\d table_name"
```

### ❌ Wrong Order (Don't Do This)
```bash
# DON'T manually write migrations first
# DON'T apply migrations before updating models
# This causes model/schema mismatch
```

### Key Principles
- **Models are source of truth**: SQLModel definitions drive schema
- **Autogenerate saves time**: Alembic detects model changes automatically
- **Always review**: Autogenerate is smart but not perfect (check indexes, constraints)
- **Test idempotency**: Run `alembic downgrade -1 && alembic upgrade head` to verify

### Example: Adding Fields to Existing Table
```python
# 1. Edit models.py
class Token(SQLModel, table=True):
    __tablename__ = "tokens_s0"

    # Existing fields...
    token_id: int = Field(primary_key=True)

    # NEW FIELDS
    image_cid: Optional[str] = Field(default=None)
    metadata_cid: Optional[str] = Field(default=None)
    reveal_tx_hash: Optional[str] = Field(default=None)

# 2. Autogenerate migration
# $ uv run alembic revision --autogenerate -m "add_ipfs_reveal_fields"
# Creates: alembic/versions/XXXX_add_ipfs_reveal_fields.py

# 3. Review generated migration
def upgrade() -> None:
    op.add_column('tokens_s0', sa.Column('image_cid', sa.Text(), nullable=True))
    op.add_column('tokens_s0', sa.Column('metadata_cid', sa.Text(), nullable=True))
    op.add_column('tokens_s0', sa.Column('reveal_tx_hash', sa.Text(), nullable=True))

# 4. Apply
# $ uv run alembic upgrade head
```

## Implementation Workflow (Phase-Based Testing & Git Rules)

### Phase Testing (MANDATORY)

**Before starting each phase**:
```bash
cd backend && uv run pytest tests/ -v
```
All tests MUST pass before starting new work.

**After completing each phase**:
```bash
cd backend && uv run pytest tests/ -v
```
If tests fail = BLOCKER. Fix before next phase.

**Core principle**: Tests define correctness. If tests fail after your changes, your code is wrong.

### Git Commits (MANDATORY)

**NEVER bypass pre-commit hooks**:
- ❌ `git commit --no-verify` - FORBIDDEN
- ❌ `git commit -n` - FORBIDDEN

**If hook fails**: Fix the issue, don't skip the hook.

<!-- MANUAL ADDITIONS END -->
