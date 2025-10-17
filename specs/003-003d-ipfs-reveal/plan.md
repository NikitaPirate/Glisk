# Implementation Plan: IPFS Upload and Batch Reveal Mechanism

**Branch**: `003-003d-ipfs-reveal` | **Date**: 2025-10-17 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/003-003d-ipfs-reveal/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Complete the MVP pipeline by adding IPFS upload and batch reveal functionality. When NFT images are generated (003c), they are automatically uploaded to IPFS via Pinata service, metadata is created following ERC721 standards, and tokens are revealed on-chain in batches for gas optimization. System implements two independent workers: IPFS upload worker (generates metadata and uploads to Pinata) and reveal worker (batches ready tokens and submits on-chain reveal transactions).

## Technical Context

**Language/Version**: Python 3.14 (standard GIL-enabled version)
**Primary Dependencies**:
- FastAPI (background workers via lifespan)
- web3.py (blockchain interactions, already installed from 003b)
- Pinata API client (requests library for HTTP)
- SQLModel + psycopg3 async (database, already installed from 003a)
- structlog (structured logging, already installed from 003a)

**Storage**: PostgreSQL 14+ with extensions to `tokens_s0` table (add `image_cid`, `metadata_cid`, `reveal_tx_hash` fields) + two new audit tables (`ipfs_upload_records`, `reveal_transactions`)

**Testing**: pytest with testcontainers (integration-first, focus on worker lifecycle, IPFS error classification, batch accumulation logic, gas estimation, transaction monitoring)

**Target Platform**: Linux server (Docker container, same as 003a/003b/003c)

**Project Type**: Backend monorepo (`backend/` domain)

**Performance Goals**:
- IPFS upload: 30 seconds per token under normal service conditions
- Batch reveal: 10 seconds from batch trigger to on-chain submission
- Throughput: 1000 tokens/hour through complete pipeline
- Success rate: 95% for IPFS uploads and batch reveals (excluding service outages)

**Constraints**:
- IPFS service (Pinata): Rate limits require exponential backoff for transient failures
- Blockchain network: Gas price volatility requires 20% buffer on estimation
- Image URL lifetime: Replicate CDN URLs expire after 10 days (upload must complete within window)
- Worker isolation: Session-per-token pattern to prevent failure cascade
- Graceful shutdown: Workers must complete in-flight operations before exit

**Scale/Scope**:
- Two new background workers (IPFS upload worker, reveal worker)
- Two new services (Pinata client, keeper service)
- Two new audit tables (ipfs_upload_records, reveal_transactions)
- ~600 LOC including tests and docs
- 4-5 day implementation (36 hours)
- Completes MVP pipeline (mint → generate → upload → reveal)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with GLISK Constitution v1.1.0:

- [x] **Simplicity First**: Solution uses simplest approach. Metadata builder inlined (20 LOC, tight coupling). No custom gas monitoring (web3.py handles). No transaction monitor worker (blocking wait sufficient). Pragmatic balance between reusable services and over-engineering.

- [x] **Seasonal MVP**: Design targets fast delivery. 4-5 day timeline. Completes MVP pipeline. Defers manual admin APIs, health endpoints, and custom monitoring to 003e. Focus on working end-to-end flow.

- [x] **Monorepo Structure**: Respects `/backend/` domain. New files in `backend/src/glisk/services/ipfs/`, `backend/src/glisk/services/blockchain/`, `backend/src/glisk/workers/`. Tests in `backend/tests/`. No frontend or contracts changes.

- [x] **Smart Contract Security**: Uses existing `revealBatch()` function from 001 (already audited). Keeper service validates token IDs and metadata URIs before submission. Gas buffer prevents failed transactions. No new contract code.

- [x] **Clear Over Clever**: Implementation plan prioritizes clarity. Error classification explicit (TransientError, PermanentError). State transitions documented. Structured logging for observability. Repository pattern consistent with 003a/003b/003c. UTC enforcement, Alembic workflow, testcontainers-first testing aligned with Constitution v1.1.0 backend standards.

**Result**: ✅ All principles satisfied. No violations requiring justification.

## Project Structure

### Documentation (this feature)

```
specs/003-003d-ipfs-reveal/
├── spec.md              # Feature specification (already exists)
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (IPFS providers, gas strategies, batch optimization)
├── data-model.md        # Phase 1 output (schema extensions, audit tables, state transitions)
├── quickstart.md        # Phase 1 output (manual testing guide for IPFS + reveal)
├── contracts/           # Phase 1 output (internal service contracts)
│   └── internal-service-contracts.md  # Pinata client, keeper service APIs
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```
backend/
├── src/glisk/
│   ├── services/
│   │   ├── ipfs/
│   │   │   ├── __init__.py           # [NEW] Exports
│   │   │   └── pinata_client.py      # [NEW] 80 LOC - IPFS upload client
│   │   └── blockchain/
│   │       ├── keeper.py             # [NEW] 100 LOC - Batch reveal service
│   │       └── alchemy_signature.py  # [EXISTING] From 003b
│   │
│   ├── workers/
│   │   ├── __init__.py               # [MODIFIED] Add new worker exports
│   │   ├── image_generation_worker.py  # [EXISTING] From 003c
│   │   ├── ipfs_upload_worker.py     # [NEW] 140 LOC - Upload worker
│   │   └── reveal_worker.py          # [NEW] 150 LOC - Reveal worker
│   │
│   ├── repositories/
│   │   └── token.py                  # [MODIFIED] Add upload/reveal methods
│   │
│   ├── db/
│   │   └── models.py                 # [MODIFIED] Add schema fields
│   │
│   ├── core/
│   │   └── config.py                 # [MODIFIED] Add Pinata/keeper settings
│   │
│   └── main.py                       # [MODIFIED] Start 2 new workers
│
├── alembic/versions/
│   └── XXX_add_ipfs_reveal_fields.py # [NEW] Migration
│
├── tests/
│   ├── test_pinata_client.py         # [NEW] Unit tests
│   ├── test_keeper_service.py        # [NEW] Unit tests
│   ├── test_ipfs_worker_integration.py    # [NEW] Integration tests
│   ├── test_reveal_worker_integration.py  # [NEW] Integration tests
│   └── test_e2e_pipeline.py          # [NEW] End-to-end test
│
└── .env.example                      # [MODIFIED] Document new variables

CLAUDE.md                             # [MODIFIED] Add 003d documentation
```

**Structure Decision**: This feature affects **backend domain only**. Creates new services for IPFS and blockchain interactions, adds two new workers, extends existing database models, and adds comprehensive test coverage. No contracts or frontend changes required.

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

**Status**: No violations. Complexity tracking not required for this feature.

---

## Post-Design Constitution Re-Check

*GATE: Re-evaluate after Phase 1 design artifacts complete*

**Artifacts Generated**:
- ✅ research.md (Phase 0): Pinata vs alternatives, web3.py gas strategies, batch optimization
- ✅ data-model.md (Phase 1): Schema extensions, audit tables, state transitions
- ✅ contracts/internal-service-contracts.md (Phase 1): PinataClient, KeeperService, error hierarchy
- ✅ quickstart.md (Phase 1): Manual testing guide, monitoring, troubleshooting
- ✅ agent context updated: CLAUDE.md with new technologies

**Re-Evaluation**:

- [x] **Simplicity First** (CONFIRMED):
  - Metadata builder inlined (20 LOC in worker)
  - Two-query batch accumulation (no continuous polling)
  - Web3.py built-in methods (no custom gas monitoring)
  - Error classification explicit (TransientError, PermanentError)
  - ✅ Design maintains simplicity promise

- [x] **Seasonal MVP** (CONFIRMED):
  - 4-5 day timeline validated by design artifacts
  - Completes MVP pipeline (mint → generate → upload → reveal)
  - Defers admin APIs, health endpoints to 003e
  - No over-engineering (adaptive batching, dynamic gas, custom monitoring)
  - ✅ Design targets fast delivery

- [x] **Monorepo Structure** (CONFIRMED):
  - All new files in `backend/` domain
  - No contracts or frontend changes
  - Clear separation: services (reusable), workers (independent), repositories (data access)
  - ✅ Design respects monorepo boundaries

- [x] **Smart Contract Security** (CONFIRMED):
  - Uses existing `revealBatch()` function (audited in 001)
  - Keeper service validates inputs before submission
  - Gas buffer prevents underestimation failures
  - Transaction reverts handled gracefully
  - ✅ Design uses secure existing contracts

- [x] **Clear Over Clever** (CONFIRMED):
  - Internal service contracts clearly document all APIs
  - Error hierarchy with explicit classification
  - State transitions documented with diagrams
  - Quickstart guide provides step-by-step testing
  - Structured logging for observability
  - ✅ Design prioritizes clarity

**Backend Standards (v1.1.0) Compliance**:
- [x] UTC enforcement: Alembic migrations use server_default=CURRENT_TIMESTAMP (UTC)
- [x] Alembic workflow: 3 migrations generated, idempotency tested in quickstart
- [x] Repository pattern: Direct implementations (TokenRepository extended, new audit repos)
- [x] Testing focus: Integration tests with testcontainers, unit tests for services, E2E test for pipeline

**Result**: ✅ All principles satisfied. Design artifacts maintain constitutional compliance. No violations introduced during design phase.

**Phase Completion**: Phase 0 (Research) and Phase 1 (Design & Contracts) are complete. Ready for Phase 2 (/speckit.tasks command) to generate implementation tasks.
