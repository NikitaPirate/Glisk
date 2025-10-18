# Implementation Plan: Simplified Token Recovery via nextTokenId

**Branch**: `004-recovery-1-nexttokenid` | **Date**: 2025-10-18 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/004-recovery-1-nexttokenid/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Replace complex event-based token recovery (eth_getLogs parsing) with a simplified mechanism that queries the smart contract's `nextTokenId` counter, compares it with the database, and creates records for missing tokens. For each missing token, queries `tokenPromptAuthor(tokenId)` from contract to get actual author address (not default). Also removes unused `mint_timestamp` and `minter_address` fields from the database schema. Recovery runs automatically on application startup to ensure database consistency before workers start. This reduces code complexity by 200+ LOC while maintaining 100% accuracy (0% false positives/negatives, accurate author attribution) and improving performance (sub-5-second recovery for 100 tokens).

## Technical Context

**Language/Version**: Python 3.14 (backend), Solidity ^0.8.20 (smart contract)
**Primary Dependencies**: web3.py (blockchain interaction), SQLModel + psycopg3 (async database), Alembic (migrations)
**Storage**: PostgreSQL 14+ with UTC timestamps, JSONB support, existing tokens_s0 table
**Testing**: pytest with testcontainers for integration tests
**Target Platform**: Linux server (backend), Base Sepolia testnet → Base mainnet (smart contract)
**Project Type**: Monorepo (contracts + backend domains affected)
**Performance Goals**: <5s recovery for 100 missing tokens, <1s database query for gaps up to 100k tokens
**Constraints**: Must not create duplicate tokens (database UNIQUE constraint on token_id), must handle concurrent webhook execution during recovery
**Scale/Scope**: Expected token count: 1k-100k tokens, recovery runs: manual CLI or scheduled cron job

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with GLISK Constitution v1.1.0:

- [x] **Simplicity First**: Replaces complex eth_getLogs parsing with simple counter comparison. Removes unused fields instead of adding conditional logic.
- [x] **Seasonal MVP**: Fast delivery via deletion of 200+ LOC and single Alembic migration. No long-term maintenance burden (removes old recovery code).
- [x] **Monorepo Structure**: Changes affect `/contracts/` (add public nextTokenId getter) and `/backend/` (new recovery logic, remove old files). No frontend changes.
- [x] **Smart Contract Security**: Minimal contract change (public getter for existing private variable). No payment logic or state changes involved. No new attack vectors.
- [x] **Clear Over Clever**: Direct counter comparison logic. Leverages database UNIQUE constraint for idempotency instead of complex deduplication code.

*No constitutional violations identified.*

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

**Structure Decision**: This feature affects **contracts** and **backend** domains:

**Contracts Domain** (1 file modified):
- `contracts/src/GliskNFT.sol` - Add public `nextTokenId()` getter function

**Backend Domain** (files modified/created/deleted):

Modified:
- `backend/src/glisk/models/token.py` - Remove `mint_timestamp` and `minter_address` fields
- `backend/src/glisk/repositories/token.py` - Update queries to remove field references, add `get_missing_token_ids()` method
- `backend/src/glisk/workers/image_generation_worker.py` - Remove `mint_timestamp` reference from query
- `backend/alembic/versions/*_remove_recovery_fields.py` - New migration to drop fields

Created:
- `backend/src/glisk/services/blockchain/token_recovery.py` - New simplified recovery service
- `backend/src/glisk/cli/recover_tokens.py` - New CLI command for recovery

Deleted:
- `backend/src/glisk/services/blockchain/event_recovery.py` - Old event-based recovery
- `backend/src/glisk/cli/recover_events.py` - Old CLI command
- `backend/tests/unit/services/blockchain/test_event_recovery.py` - Old tests
- `backend/tests/unit/cli/test_recover_events.py` - Old tests

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
