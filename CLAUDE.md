# glisk Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-10-10

## Active Technologies
- Solidity ^0.8.20 + OpenZeppelin Contracts v5.x (ERC721, AccessControl, ReentrancyGuard, ERC2981) (001-full-smart-contract)
- Markdown for command definitions, Bash for orchestration scripts (002-smart-contract-audit)
- File-based (audit history in `.audit/` directory, results as markdown reports) (002-smart-contract-audit)
- Python 3.14 (standard GIL-enabled version) + FastAPI, SQLModel, psycopg3 (async), Alembic, Pydantic BaseSettings, structlog, pytest, testcontainers (003-003a-backend-foundation)
- PostgreSQL 14+ with 200 connection pool, UTC timestamps, JSONB suppor (003-003a-backend-foundation)
- Python 3.14 (standard GIL-enabled version) + FastAPI, Alchemy SDK (py-alchemy-sdk), hmac (stdlib), SQLModel, psycopg3 (async), Pydantic BaseSettings (003-003b-event-detection)
- PostgreSQL 14+ with JSONB support (tables: mint_events, tokens_s0, authors, system_state from 003a) (003-003b-event-detection)

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

## Code Style
Solidity ^0.8.20: Follow standard conventions

## Backend Features

### Mint Event Detection System (003-003b-event-detection)

**Status**: ✅ Complete (Phases 1-6 implemented)

**Purpose**: Real-time blockchain event detection for NFT mints via Alchemy webhooks + historical event recovery via eth_getLogs.

**Features Implemented**:
- ✅ Phase 1: Setup (web3.py dependency, Alchemy configuration)
- ✅ Phase 2: Foundational security (HMAC signature validation with constant-time comparison)
- ✅ Phase 3: Webhook authentication (signature validation dependency, unit tests)
- ✅ Phase 4: Real-time mint detection (POST /webhooks/alchemy endpoint, event parsing, database storage)
- ✅ Phase 5: Event recovery CLI (`python -m glisk.cli.recover_events` with pagination and state management)
- ✅ Phase 6: Polish (structured logging, quickstart validation tests, code review, documentation)

**Key Files**:
- `backend/src/glisk/api/routes/webhooks.py` - Webhook endpoint (POST /webhooks/alchemy)
- `backend/src/glisk/services/blockchain/alchemy_signature.py` - HMAC-SHA256 signature validation
- `backend/src/glisk/services/blockchain/event_recovery.py` - eth_getLogs recovery mechanism
- `backend/src/glisk/cli/recover_events.py` - CLI command for historical event recovery
- `backend/tests/test_quickstart.py` - Quickstart validation test suite

**Usage**:

*Webhook Endpoint* (Real-time detection):
```bash
# Endpoint receives Alchemy webhooks at POST /webhooks/alchemy
# Validates HMAC signature, parses BatchMinted events, stores to database
# See specs/003-003b-event-detection/quickstart.md for setup
```

*Event Recovery CLI* (Historical events):
```bash
# First-time recovery from contract deployment block
cd backend
python -m glisk.cli.recover_events --from-block 12345000

# Resume from last checkpoint
python -m glisk.cli.recover_events

# Dry run (no database writes)
python -m glisk.cli.recover_events --from-block 12345000 --dry-run

# Verbose logging
python -m glisk.cli.recover_events --from-block 12345000 -v
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
- 003-003d: IPFS Upload & Metadata (upload images to IPFS, update token URIs)
- 003-003e: Reveal Mechanism (batch reveal tokens on-chain)

## Recent Changes
- 003-003d-ipfs-reveal: Added Python 3.14 (standard GIL-enabled version)
- 003-003c-image-generation: Added Python 3.14 (standard GIL-enabled version) + FastAPI (lifecycle hooks), Replicate Python SDK, SQLModel, psycopg3 (async), structlog
- 003-003b-event-detection: ✅ COMPLETE - Mint event detection system with webhooks and recovery CLI

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
