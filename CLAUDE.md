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

## Recent Changes
- 003-003b-event-detection: Added Python 3.14 (standard GIL-enabled version) + FastAPI, Alchemy SDK (py-alchemy-sdk), hmac (stdlib), SQLModel, psycopg3 (async), Pydantic BaseSettings
- 003-003a-backend-foundation: Added Python 3.14 (standard GIL-enabled version) + FastAPI, SQLModel, psycopg3 (async), Alembic, Pydantic BaseSettings, structlog, pytest, testcontainers
- 002-smart-contract-audit: Added Markdown for command definitions, Bash for orchestration scripts

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

<!-- MANUAL ADDITIONS END -->
