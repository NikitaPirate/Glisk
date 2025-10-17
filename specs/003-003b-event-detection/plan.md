# Implementation Plan: Mint Event Detection System

**Branch**: `003-003b-event-detection` | **Date**: 2025-10-17 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-003b-event-detection/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Build a real-time mint event detection system that receives Alchemy webhooks for NFT mint events, validates signatures using HMAC SHA256, and stores MintEvent and Token records in PostgreSQL. Includes a recovery mechanism using eth_getLogs to fetch missed historical events. Detection only - no event processing (image generation, IPFS upload) in this phase.

## Technical Context

**Language/Version**: Python 3.14 (standard GIL-enabled version)
**Primary Dependencies**: FastAPI, Alchemy SDK (py-alchemy-sdk), hmac (stdlib), SQLModel, psycopg3 (async), Pydantic BaseSettings
**Storage**: PostgreSQL 14+ with JSONB support (tables: mint_events, tokens_s0, authors, system_state from 003a)
**Testing**: pytest with testcontainers (real PostgreSQL), integration-first per constitution
**Target Platform**: Linux server with public webhook endpoint (ngrok for local dev)
**Project Type**: Backend web service (webhook receiver + CLI recovery tool)
**Performance Goals**: <500ms webhook processing latency, 1000 events/2min recovery throughput
**Constraints**: HMAC constant-time comparison (security), idempotent event storage (UNIQUE constraint), <3s webhook response time
**Scale/Scope**: ~400 LOC new code, 4 new files (webhooks.py, alchemy_signature.py, event_recovery.py, recover_events.py), 3 test files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with GLISK Constitution v1.1.0:

- [x] **Simplicity First**: Inline event parsing (25 lines) and storage logic per Indie Hacker wins. Only extract reusable security component (signature validation). No premature abstractions (parser class, web3 client abstraction, queue system) - defer with explicit triggers.
- [x] **Seasonal MVP**: 16-hour implementation targeting detection-only scope. No event processing logic. Leverages existing 003a foundation (UoW, repositories, tables). Uses battle-tested Alchemy SDK, no custom RPC abstraction.
- [x] **Monorepo Structure**: Backend domain only (`/backend/src/glisk/`). No cross-domain dependencies. Listens to contracts deployed by 001, but no code coupling.
- [ ] **Smart Contract Security**: N/A - No contract changes. Consumes events from existing GliskNFT contract.
- [x] **Clear Over Clever**: HMAC constant-time comparison clearly documented. Event parsing kept inline for clarity. Testcontainers for integration tests (real DB, no mocks). UTC enforcement from constitution v1.1.0.

**Additional Backend Standards (Constitution v1.1.0)**:
- [x] **UTC Enforcement**: Import `glisk.core.timezone` at startup, use UTC timestamps throughout
- [x] **Alembic Workflow**: No schema changes needed (tables from 003a), but recovery mechanism updates `system_state.last_processed_block`
- [x] **Repository Pattern**: Direct repository usage (AuthorRepository.get_by_wallet) without generic base classes
- [x] **Testing Focus**: Integration tests for webhook flow and recovery. Skip testing simple CRUD and framework basics.

*No constitutional violations. Complexity Tracking section left empty.*

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

**Structure Decision**: Backend domain only. This feature creates the webhook endpoint and recovery CLI for detecting mint events from the GliskNFT contract (deployed in 001-full-smart-contract).

**New Files Created**:
- `backend/src/glisk/api/routes/webhooks.py` - FastAPI route for POST /webhooks/alchemy
- `backend/src/glisk/services/blockchain/alchemy_signature.py` - HMAC signature validation
- `backend/src/glisk/services/blockchain/event_recovery.py` - eth_getLogs recovery mechanism
- `backend/src/glisk/cli/recover_events.py` - CLI command for manual recovery
- `backend/tests/test_webhook_signature.py` - Unit tests for signature validation
- `backend/tests/test_webhook_integration.py` - Integration tests for full webhook flow
- `backend/tests/test_event_recovery.py` - Integration tests for recovery mechanism

**Files Modified**:
- `backend/src/glisk/core/config.py` - Add Alchemy configuration (API key, webhook secret, contract address, network, default author wallet)
- `backend/.env.example` - Document new environment variables

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

**No violations** - All design decisions align with constitution.

**Post-Phase 1 Re-evaluation** (2025-10-17):
- ✅ Simplicity First: Confirmed inline parsing (25 lines in webhooks.py), extracted signature validation (20 lines, reusable)
- ✅ Seasonal MVP: ~400 LOC total, 16-hour estimate, detection-only scope maintained
- ✅ Clear Over Clever: API contracts, data model, and quickstart confirm straightforward implementation
- ✅ Backend Standards: web3.py chosen over Alchemy SDK (better docs), manual event decoding (no ABI overhead)

**Deferred Abstractions with Triggers** (per spec.md):
- Parser class → Trigger: webhook route > 80 lines
- Web3 client abstraction → Trigger: need multiple RPC providers
- Webhook tracking table → Trigger: Alchemy reliability issues
- Processing queue → Trigger: direct storage throughput insufficient
