# Implementation Plan: Image Generation Worker

**Branch**: `003-003c-image-generation` | **Date**: 2025-10-17 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-003c-image-generation/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement a background worker that polls for newly detected NFT mint events (status='detected'), generates AI images using the Replicate API with the author's text prompt, and updates token records with the generated image URL (status='uploading'). The worker handles retries for transient failures (network, rate limits), uses a fallback prompt for content policy violations, and supports concurrent batch processing with database-level locking.

## Technical Context

**Language/Version**: Python 3.14 (standard GIL-enabled version)
**Primary Dependencies**: FastAPI (lifecycle hooks), Replicate Python SDK, SQLModel, psycopg3 (async), structlog
**Storage**: PostgreSQL 14+ (extends existing schema: tokens_s0 table)
**Testing**: pytest, testcontainers (real PostgreSQL for integration tests)
**Target Platform**: Linux server (async background worker)
**Project Type**: Backend service (monorepo `/backend/` domain)
**Performance Goals**: Process up to 10 tokens concurrently per polling cycle, <60s generation latency (P95)
**Constraints**: <1% CPU utilization during idle polling, 3 retry attempts max, 1000 char prompt limit
**Scale/Scope**: ~100-500 mints per month initially (low volume, high reliability requirement)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with GLISK Constitution v1.1.0:

- [x] **Simplicity First**: Polling-based worker with direct API calls—no message queues, no complex orchestration
- [x] **Seasonal MVP**: Targets fast MVP delivery with acceptable tradeoffs (10-day URL expiration, manual recovery for rare outages)
- [x] **Monorepo Structure**: Extends `/backend/` domain, builds on existing 003a/003b foundation
- [x] **Smart Contract Security**: N/A - no contract changes
- [x] **Clear Over Clever**: Direct status field updates, simple retry counter, no circuit breakers for rare events
- [x] **UTC Enforcement**: Inherits UTC handling from 003a (glisk.core.timezone module)
- [x] **Alembic Workflow**: Database changes follow autogenerate → manual verification → test idempotency
- [x] **Repository Pattern**: Uses direct repository methods (no generic base classes)
- [x] **Testing Focus**: Tests complex logic (FOR UPDATE SKIP LOCKED, retry logic, state transitions), skips simple CRUD

*No violations detected. Solution aligns with constitution's emphasis on simplicity and MVP speed.*

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

```
backend/
├── src/glisk/
│   ├── workers/
│   │   ├── __init__.py
│   │   └── image_generation_worker.py    # NEW: Polling loop, lifecycle hooks
│   ├── services/
│   │   ├── blockchain/                    # Existing from 003b
│   │   └── image_generation/              # NEW
│   │       ├── __init__.py
│   │       ├── replicate_client.py        # NEW: Replicate API integration
│   │       └── prompt_validator.py        # NEW: Length validation
│   ├── repositories/
│   │   └── token_repository.py            # MODIFIED: Add find_for_generation(), update_image_url()
│   ├── db/
│   │   └── models.py                      # MODIFIED: Add image_url, generation_attempts, generation_error fields
│   └── core/
│       └── config.py                      # MODIFIED: Add Replicate env vars
├── alembic/
│   └── versions/
│       └── XXXX_add_image_generation_fields.py  # NEW: Migration for 3 new columns
└── tests/
    ├── workers/
    │   └── test_image_generation_worker.py      # NEW: Polling, locking, retry tests
    └── services/image_generation/
        ├── test_replicate_client.py             # NEW: API integration tests
        └── test_prompt_validator.py             # NEW: Validation rules tests
```

**Structure Decision**: This feature extends the `/backend/` domain. Builds on existing infrastructure from 003a (database, repositories, FastAPI) and 003b (token status workflow). No changes to contracts or frontend.

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
