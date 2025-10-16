# Tasks: 003a Backend Foundation - Shared Infrastructure

**Input**: Design documents from `/specs/003-003a-backend-foundation/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests ARE required per GLISK constitution for complex logic (FOR UPDATE SKIP LOCKED, state transitions). Tests for simple CRUD are explicitly skipped.

**Organization**: Tasks are grouped by developer story (foundation has no end-user stories, so "users" are developers building 003b-003e).

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which developer story this task belongs to (DS1, DS2, DS3, DS4, DS5)
- Include exact file paths in descriptions

## Path Conventions
- **Backend domain**: `backend/src/glisk/`, `backend/tests/`
- All work in this feature is backend-only (no contracts/, no frontend/)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] **T001** [P] [SETUP] Create backend directory structure: `backend/src/glisk/{core,models,repositories}/`, `backend/tests/`, `backend/alembic/versions/`
- [ ] **T002** [P] [SETUP] Initialize Python project with uv:
  - Run `cd backend && uv init`
  - Run `uv add fastapi sqlmodel "psycopg[binary]" alembic pydantic pydantic-settings structlog alembic-postgresql-enum`
  - Run `uv add --dev pytest pytest-asyncio testcontainers[postgres] httpx ruff pyright`
  - Add to pyproject.toml [tool.ruff]: line-length=100, select=["E", "F", "I"], fix=true
  - Add to pyproject.toml [tool.pyright]: typeCheckingMode="basic", venvPath="."
- [ ] **T003** [P] [SETUP] Create `/.env.example` at REPO ROOT (not backend/) with all configuration variables documented (DATABASE_URL=postgresql+psycopg://glisk:glisk@localhost:5432/glisk, DB_POOL_SIZE=200, APP_ENV=development, LOG_LEVEL=INFO, CORS_ORIGINS=http://localhost:3000, HOST=0.0.0.0, PORT=8000)
- [ ] **T004** [P] [SETUP] **[USER ACTION REQUIRED]** Copy `/.env.example` to `/.env` at repo root and customize if needed (default values work for development)
- [ ] **T005** [SETUP] Create `backend/Dockerfile` with layer caching optimization:
  - FROM python:3.14-slim
  - RUN pip install uv
  - WORKDIR /app
  - COPY pyproject.toml uv.lock ./
  - RUN uv sync --frozen
  - COPY src/ ./src/
  - COPY alembic/ ./alembic/
  - COPY alembic.ini ./
  - CMD ["uv", "run", "uvicorn", "glisk.app:app", "--host", "0.0.0.0", "--port", "8000"]
- [ ] **T006** [SETUP] Create `backend/docker-compose.yml` with detailed service configuration:
  - Service postgres: image postgres:14, container_name backend-postgres-1, environment (POSTGRES_DB=glisk, POSTGRES_USER=glisk, POSTGRES_PASSWORD=glisk), command ["postgres", "-c", "max_connections=200"], ports ["5432:5432"], volumes postgres_data:/var/lib/postgresql/data, healthcheck (pg_isready -U glisk, interval 5s, timeout 3s, retries 5)
  - Service backend-api: build ., container_name backend-api-1, depends_on postgres (condition: service_healthy), env_file ../.env (root .env file), ports ["8000:8000"], restart unless-stopped
  - volumes: postgres_data (named volume)
- [ ] **T007** [P] [SETUP] Configure Alembic: Create `backend/alembic.ini` and `backend/alembic/env.py` with async engine support
- [ ] **T008** [P] [SETUP] Create `backend/.gitignore` (exclude .env, __pycache__, .pytest_cache, *.pyc, .coverage, htmlcov/)
- [ ] **T008b** [P] [SETUP] Create `backend/.dockerignore` (exclude .env, .git, tests/, __pycache__/, *.pyc, .pytest_cache, htmlcov/, .coverage, .mypy_cache, .ruff_cache)
- [ ] **T009** [SETUP] Create `.pre-commit-config.yaml` at repo root with hooks: ruff (lint+format), pyright (type check), trailing-whitespace, check-yaml

**Checkpoint**: Project structure and configuration files ready

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY developer story can be implemented

**⚠️ CRITICAL**: No developer story work can begin until this phase is complete

- [ ] **T010** [P] [FOUNDATION] Create `backend/src/glisk/__init__.py` (empty module marker)
- [ ] **T011** [P] [FOUNDATION] Implement `backend/src/glisk/core/timezone.py`: Set TZ=UTC environment variable, import on app startup
- [ ] **T012** [P] [FOUNDATION] Implement `backend/src/glisk/core/config.py`: Pydantic BaseSettings class with all environment variables (database_url, db_pool_size, app_env, log_level, cors_origins, host, port)
- [ ] **T013** [FOUNDATION] Implement `backend/src/glisk/core/database.py`: `setup_db_session(db_url, pool_size)` function returning `async_sessionmaker[AsyncSession]`
- [ ] **T014** [P] [FOUNDATION] Configure structlog in `backend/src/glisk/core/config.py`: JSON output for production, console for development, INFO level for transactions, ERROR level for database errors
- [ ] **T015** [FOUNDATION] Create `backend/src/glisk/core/dependencies.py`: FastAPI dependency functions for UoW factory injection (will be implemented later, placeholder for now)
- [ ] **T016** [FOUNDATION] Create `backend/src/glisk/app.py`: FastAPI application factory with lifespan context manager, CORS middleware, **timezone import**, health endpoint (placeholder)

**Checkpoint**: Foundation ready - developer story implementation can now begin in parallel

---

## Phase 3: Developer Story 1 - Database Schema Ready (Priority: P1) 🎯 CRITICAL PATH

**Goal**: Developers can run `alembic upgrade head` and have all 7 tables with correct columns, indexes, constraints

**Independent Test**: Run `alembic upgrade head`, connect to database, verify all 7 tables exist (authors, tokens_s0, mint_events, image_generation_jobs, ipfs_upload_records, reveal_transactions, system_state)

**Why P1**: Without schema, no feature can be built. This is the critical path blocker.

### Implementation for Developer Story 1

- [ ] **T017** [P] [DS1] Create `backend/src/glisk/models/__init__.py` with all model imports for Alembic metadata
- [ ] **T018** [P] [DS1] Create `backend/src/glisk/models/author.py`: Author SQLModel entity with fields (id UUID, wallet_address VARCHAR(42) UNIQUE, twitter_handle, farcaster_handle, prompt_text TEXT, created_at), Pydantic validators for wallet_address pattern
- [ ] **T019** [P] [DS1] Create `backend/src/glisk/models/token.py`: Token SQLModel entity with fields (id UUID, token_id INT UNIQUE, author_id FK, minter_address, status ENUM, mint_timestamp, image_cid, metadata_cid, error_data JSONB, created_at), TokenStatus enum (detected, generating, uploading, ready, revealed, failed)
- [ ] **T020** [P] [DS1] Create `backend/src/glisk/models/mint_event.py`: MintEvent SQLModel entity with fields (id UUID, tx_hash, log_index, block_number, block_timestamp, token_id, detected_at), UNIQUE constraint on (tx_hash, log_index)
- [ ] **T021** [P] [DS1] Create `backend/src/glisk/models/image_job.py`: ImageGenerationJob SQLModel entity with fields (id UUID, token_id FK, service, status, external_job_id, retry_count, error_data JSONB, created_at, completed_at)
- [ ] **T022** [P] [DS1] Create `backend/src/glisk/models/ipfs_record.py`: IPFSUploadRecord SQLModel entity with fields (id UUID, token_id FK, record_type, cid, status, retry_count, error_data JSONB, created_at, completed_at)
- [ ] **T023** [P] [DS1] Create `backend/src/glisk/models/reveal_tx.py`: RevealTransaction SQLModel entity with fields (id UUID, token_ids UUID[], tx_hash, block_number, gas_price_gwei DECIMAL, status, created_at, confirmed_at)
- [ ] **T024** [P] [DS1] Create `backend/src/glisk/models/system_state.py`: SystemState SQLModel entity with fields (key VARCHAR PRIMARY KEY, state_value JSONB, updated_at)
- [ ] **T025** [DS1] Create initial Alembic migration using autogenerate:
  - Ensure all models imported in `backend/src/glisk/models/__init__.py`
  - Run `cd backend && uv run alembic revision --autogenerate -m "Initial schema"`
  - Open generated migration in `alembic/versions/`
  - Manually verify: enum types use alembic-postgresql-enum operations (sync_enum_values), indexes on (status, mint_timestamp) and (tx_hash, log_index), foreign keys have appropriate ON DELETE actions (RESTRICT for authors, CASCADE for jobs/records)
  - Test idempotency: `uv run alembic upgrade head && uv run alembic downgrade base && uv run alembic upgrade head`
- [ ] **T026** [DS1] **[USER ACTION REQUIRED]** Start PostgreSQL: Run `docker compose up -d postgres` from `backend/` directory and wait 5 seconds for startup
- [ ] **T027** [DS1] **[USER ACTION REQUIRED]** Apply migrations: Run `cd backend && uv run alembic upgrade head` to create schema
- [ ] **T028** [DS1] **[USER ACTION REQUIRED]** Verify schema: Connect to database with `docker exec -it backend-postgres-1 psql -U glisk -d glisk` and run `\dt` to list tables, then `\q` to exit

**Checkpoint**: Database schema is complete and verified. Developers can now query tables and start writing repository methods.

---

## Phase 4: Developer Story 2 - Repository Layer Available (Priority: P2)

**Goal**: Developers can instantiate repositories, call methods like `TokenRepository.get_pending_for_generation(limit=10)`, and workers receive non-overlapping sets via FOR UPDATE SKIP LOCKED

**Independent Test**: Instantiate TokenRepository, insert 20 test tokens with status=detected, call get_pending_for_generation from two concurrent contexts, verify zero overlap

**Why P2**: Repository layer abstracts database complexity and ensures worker coordination. Required immediately after schema.

### Tests for Developer Story 2 (TDD - Write FIRST, Ensure FAIL)

- [ ] **T029** [P] [DS2] Create `backend/tests/conftest.py`: Session-scoped `postgres_container` fixture (testcontainers, 60s timeout), session-scoped `utc_timezone` autouse fixture (set TZ=UTC), function-scoped `session` fixture (table truncation between tests via DELETE FROM), function-scoped `uow_factory` fixture
- [ ] **T030** [P] [DS2] Create `backend/tests/test_repositories.py`: Test `test_concurrent_workers_receive_non_overlapping_tokens` - Create 20 tokens with status=detected, launch two async workers calling get_pending_for_generation(limit=10) concurrently, assert worker A gets 10 tokens, worker B gets 10 different tokens, assert zero overlap (set intersection is empty)
- [ ] **T031** [P] [DS2] In `backend/tests/test_repositories.py`: Test `test_case_insensitive_wallet_lookup` - Create author with wallet "0xABC...", call AuthorRepository.get_by_wallet("0xabc..."), assert author found (case-insensitive)
- [ ] **T032** [P] [DS2] In `backend/tests/test_repositories.py`: Test `test_mint_event_duplicate_detection` - Create mint event with (tx_hash, log_index), call MintEventRepository.exists(tx_hash, log_index), assert True
- [ ] **T033** [P] [DS2] In `backend/tests/test_repositories.py`: Test `test_system_state_upsert` - Call SystemStateRepository.set_state("key", "value1"), call set_state("key", "value2"), get_state("key") returns "value2" (UPSERT behavior)

**Run tests now - they should all FAIL (models/repositories not implemented yet)**

### Implementation for Developer Story 2

- [ ] **T034** [P] [DS2] Create `backend/src/glisk/repositories/__init__.py` (empty module marker)
- [ ] **T035** [P] [DS2] Implement `backend/src/glisk/repositories/author.py`: AuthorRepository with methods (get_by_id, get_by_wallet with LOWER() case-insensitive, add, list_all with pagination). Docstrings explain query purpose.
- [ ] **T036** [P] [DS2] Implement `backend/src/glisk/repositories/token.py`: TokenRepository with methods (get_by_id, get_by_token_id, add, get_pending_for_generation with FOR UPDATE SKIP LOCKED + ORDER BY mint_timestamp ASC, get_pending_for_upload with FOR UPDATE SKIP LOCKED, get_ready_for_reveal with FOR UPDATE SKIP LOCKED, get_by_author, get_by_status). Add explicit comments above FOR UPDATE queries.
- [ ] **T037** [P] [DS2] Implement `backend/src/glisk/repositories/mint_event.py`: MintEventRepository with methods (add, exists with SELECT EXISTS query, get_by_block_range). Docstrings for duplicate detection purpose.
- [ ] **T038** [P] [DS2] Implement `backend/src/glisk/repositories/image_job.py`: ImageGenerationJobRepository with methods (add, get_by_id, get_by_token, get_latest_by_token)
- [ ] **T039** [P] [DS2] Implement `backend/src/glisk/repositories/ipfs_record.py`: IPFSUploadRecordRepository with methods (add, get_by_id, get_by_token with optional record_type filter)
- [ ] **T040** [P] [DS2] Implement `backend/src/glisk/repositories/reveal_tx.py`: RevealTransactionRepository with methods (add, get_by_id, get_by_tx_hash, get_by_status, get_pending)
- [ ] **T041** [P] [DS2] Implement `backend/src/glisk/repositories/system_state.py`: SystemStateRepository with methods (get_state deserializes JSON, set_state UPSERT with INSERT ... ON CONFLICT DO UPDATE, delete_state idempotent)
- [ ] **T042** [DS2] **[USER ACTION REQUIRED]** Run tests: Execute `cd backend && uv run pytest tests/test_repositories.py` and verify all repository tests pass

**Checkpoint**: Repository layer is complete and tested. Workers can now fetch tokens with proper coordination.

---

## Phase 5: Developer Story 3 - Unit of Work Pattern (Priority: P2)

**Goal**: Developers can use `async with uow:` context manager, perform multiple repository operations, and changes automatically commit on success or rollback on exception

**Independent Test**: Create UoW context, modify token via `uow.tokens.get_by_id(42)`, exit successfully, verify changes persisted. Raise exception within context, verify rollback.

**Why P2**: Transaction boundaries are critical for data integrity. Autocommit ensures changes persist without manual calls.

### Tests for Developer Story 3 (TDD - Write FIRST, Ensure FAIL)

- [ ] **T043** [P] [DS3] Create `backend/tests/test_state_transitions.py`: Test `test_valid_state_transitions` - Create token with status=detected, call token.mark_generating(), assert status=generating. Call mark_uploading("path"), assert status=uploading. Call mark_ready("cid"), assert status=ready and metadata_cid set. Call mark_revealed("0xabc"), assert status=revealed.
- [ ] **T044** [P] [DS3] In `backend/tests/test_state_transitions.py`: Test `test_invalid_state_transition_raises_exception` - Create token with status=detected, call token.mark_revealed("0xabc"), assert raises InvalidStateTransition with descriptive message "Cannot mark revealed from detected. Token must be in ready state."
- [ ] **T045** [P] [DS3] In `backend/tests/test_state_transitions.py`: Test `test_mark_failed_from_any_non_terminal_state` - Create tokens in each non-terminal state (detected, generating, uploading, ready), call mark_failed({"error": "test"}), assert all transition to failed with error_data populated
- [ ] **T046** [P] [DS3] Create `backend/tests/test_uow.py`: Test `test_uow_commits_on_successful_exit` - async with uow: create author, exit successfully. In new uow: get_by_id returns same author (changes persisted).
- [ ] **T047** [P] [DS3] In `backend/tests/test_uow.py`: Test `test_uow_rollback_on_exception` - async with uow: create author, raise exception. Verify author does not exist in database (rollback occurred).

**Run tests now - they should all FAIL (state transitions and UoW not implemented yet)**

### Implementation for Developer Story 3

- [ ] **T048** [DS3] Add state transition methods to `backend/src/glisk/models/token.py`: Implement mark_generating(), mark_uploading(image_path), mark_ready(metadata_cid), mark_revealed(tx_hash), mark_failed(error_dict). Each method validates current status and raises InvalidStateTransition with clear error message if invalid. Create InvalidStateTransition exception class in same file.
- [ ] **T049** [DS3] Implement `backend/src/glisk/uow.py`: Create UnitOfWork class as async context manager with __aenter__ (create session, instantiate all 7 repositories), __aexit__ (commit if no exception, rollback if exception raised), repository properties (authors, tokens, mint_events, image_jobs, ipfs_records, reveal_txs, system_state). Add INFO level logging for "transaction.committed" and "transaction.rolled_back" events.
- [ ] **T050** [DS3] Implement `create_uow_factory(session_factory)` function in `backend/src/glisk/uow.py`: Returns callable that produces UoW instances from session factory
- [ ] **T051** [DS3] Update `backend/src/glisk/core/dependencies.py`: Implement FastAPI dependency `get_uow()` that yields UoW from app.state.uow_factory
- [ ] **T052** [DS3] **[USER ACTION REQUIRED]** Run tests: Execute `cd backend && uv run pytest tests/test_state_transitions.py tests/test_uow.py` and verify all UoW and state transition tests pass

**Checkpoint**: UoW pattern is complete. Developers can now manage transactions declaratively with automatic commit/rollback.

---

## Phase 6: Developer Story 4 - Test Infrastructure Ready (Priority: P3)

**Goal**: Developers can run `pytest` and have testcontainer automatically provision PostgreSQL, apply migrations, provide working UoW factory

**Independent Test**: Write test for TokenRepository.get_pending_for_generation(), run pytest, test passes using real PostgreSQL

**Why P3**: TDD is part of constitution for complex logic. Test infrastructure enables this. Lower priority because it can be added after core infrastructure.

### Implementation for Developer Story 4

**NOTE**: Test infrastructure was already created in T029 (conftest.py). This phase validates it works end-to-end.

- [ ] **T053** [DS4] Verify `backend/tests/conftest.py` implements all fixtures correctly: postgres_container (session-scoped, 60s timeout), utc_timezone (autouse, sets TZ=UTC), session (function-scoped with table truncation via DELETE FROM all tables), uow_factory (function-scoped, applies migrations via alembic.command.upgrade)
- [ ] **T054** [DS4] **[USER ACTION REQUIRED]** Run full test suite: Execute `cd backend && uv run pytest` and verify all tests pass (<60 seconds including testcontainer startup)
- [ ] **T055** [DS4] **[USER ACTION REQUIRED]** Verify UTC enforcement: Run tests in different timezone `TZ=America/Los_Angeles uv run pytest` and verify results identical (UTC autouse fixture works)
- [ ] **T056** [DS4] **[USER ACTION REQUIRED]** Verify test isolation: Run pytest twice, verify same results (table truncation between tests working)

**Checkpoint**: Test infrastructure validated. Developers can write tests with confidence using real database.

---

## Phase 7: Developer Story 5 - FastAPI Application Starts (Priority: P3)

**Goal**: Developers can run `docker compose up`, call `GET /health`, receive `200 OK` response

**Independent Test**: Run `docker compose up`, wait for services, curl http://localhost:8000/health, verify {"status":"healthy"}

**Why P3**: Validates end-to-end infrastructure (Docker, database connection, FastAPI app) works. Lower priority because it's integration-focused, not feature-critical.

### Implementation for Developer Story 5

- [ ] **T057** [DS5] Complete `backend/src/glisk/app.py`: Implement create_app() factory function with lifespan context manager (startup: setup database session factory, create UoW factory, store in app.state; shutdown: close connections), add CORS middleware (origins from config), mount health endpoint
- [ ] **T058** [DS5] Implement health check endpoint in `backend/src/glisk/app.py`: GET /health returns {"status":"healthy"} if database SELECT 1 succeeds, returns 503 with {"status":"unhealthy", "error": {...}} if database connection fails, logs errors at ERROR level
- [ ] **T059** [DS5] **[USER ACTION REQUIRED]** Build and start services: Run `cd backend && docker compose up --build` from backend directory
- [ ] **T060** [DS5] **[USER ACTION REQUIRED]** Verify health check: In new terminal, run `curl http://localhost:8000/health` and verify response is `{"status":"healthy"}`
- [ ] **T061** [DS5] **[USER ACTION REQUIRED]** Verify Swagger UI: Open browser to `http://localhost:8000/docs` and verify API documentation loads
- [ ] **T062** [DS5] **[USER ACTION REQUIRED]** Test database connection failure: Stop postgres with `docker compose stop postgres`, curl health endpoint, verify 503 response with error message, restart postgres with `docker compose start postgres`

**Checkpoint**: FastAPI application is running and healthy. Backend foundation is complete.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple developer stories

- [ ] **T063** [P] [POLISH] Update `backend/README.md`: Add project overview, setup instructions (link to quickstart.md), architecture diagram, technology stack, development workflow (testing, migrations, debugging)
- [ ] **T064** [P] [POLISH] Code review pass: Verify all docstrings present on repository methods, state transition methods have clear error messages, FOR UPDATE queries have explanatory comments, no TODO markers remaining
- [ ] **T065** [P] [POLISH] Verify `.env.example` documentation: All variables have comments explaining purpose and valid values, DB_POOL_SIZE=200 documented, defaults provided for all optional variables
- [ ] **T066** [POLISH] **[USER ACTION REQUIRED]** Run quickstart validation: Follow `specs/003-003a-backend-foundation/quickstart.md` step-by-step on fresh clone to verify onboarding experience works
- [ ] **T067** [POLISH] **[USER ACTION REQUIRED]** Verify success criteria from spec.md: docker compose up completes in <30s (SC-001), alembic upgrade head completes in <5s (SC-002), pytest completes in <60s (SC-003), GET /health responds in <100ms (SC-004), concurrent worker test shows zero overlap (SC-005), invalid state transition raises exception (SC-006), timezone tests identical across timezones (SC-007)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all developer stories
- **Developer Stories (Phase 3-7)**: All depend on Foundational phase completion
  - DS1 (Database Schema) → Must complete before DS2-DS5
  - DS2 (Repository Layer) → Can start after DS1 completion
  - DS3 (Unit of Work) → Can start after DS2 completion (needs repositories)
  - DS4 (Test Infrastructure) → Already created in DS2, validated after DS3
  - DS5 (FastAPI App) → Can start after DS3 completion (needs UoW for dependency injection)
- **Polish (Phase 8)**: Depends on all developer stories being complete

### Developer Story Dependencies

```
Setup → Foundational → DS1 (Schema) → DS2 (Repositories) → DS3 (UoW) → DS4 (Tests) → DS5 (FastAPI) → Polish
                            ↓
                        CRITICAL PATH (all other stories blocked until schema ready)
```

**Critical Path**: DS1 (Database Schema) must complete before any other developer story can proceed. This is the primary blocker.

### Within Each Developer Story

- Tests (TDD): Write FIRST, ensure FAIL, then implement
- Models before repositories
- Repositories before UoW
- UoW before FastAPI dependencies
- Core implementation before validation
- Story complete before moving to next

### Parallel Opportunities

**Phase 1 (Setup)**: Tasks T001-T003, T005-T008b can run in parallel (different files)

**Phase 2 (Foundational)**: Tasks T010-T012, T014 can run in parallel (different files)

**Phase 3 (DS1 - Models)**: Tasks T017-T024 can run in parallel (different model files)

**Phase 4 (DS2 - Tests)**: Tasks T029-T033 can run in parallel (different test functions)

**Phase 4 (DS2 - Repositories)**: Tasks T034-T041 can run in parallel (different repository files)

**Phase 5 (DS3 - Tests)**: Tasks T043-T047 can run in parallel (different test functions)

**Phase 8 (Polish)**: Tasks T063-T065 can run in parallel (different files)

**USER ACTION TASKS**: Cannot be parallelized (require manual intervention, must wait for completion)

---

## Parallel Example: Developer Story 1 (Database Schema)

```bash
# Launch all model creation tasks together:
Task: "Create author.py SQLModel entity"
Task: "Create token.py SQLModel entity"
Task: "Create mint_event.py SQLModel entity"
Task: "Create image_job.py SQLModel entity"
Task: "Create ipfs_record.py SQLModel entity"
Task: "Create reveal_tx.py SQLModel entity"
Task: "Create system_state.py SQLModel entity"

# Wait for all to complete, then:
Task: "Create initial Alembic migration" (sequential - needs all models)
```

---

## Parallel Example: Developer Story 2 (Repository Layer)

```bash
# Launch all test creation tasks together:
Task: "Test concurrent workers non-overlapping"
Task: "Test case-insensitive wallet lookup"
Task: "Test mint event duplicate detection"
Task: "Test system state UPSERT"

# Launch all repository implementation tasks together:
Task: "Implement AuthorRepository"
Task: "Implement TokenRepository"
Task: "Implement MintEventRepository"
Task: "Implement ImageGenerationJobRepository"
Task: "Implement IPFSUploadRecordRepository"
Task: "Implement RevealTransactionRepository"
Task: "Implement SystemStateRepository"

# Wait for all to complete, then:
Task: "Run repository tests" (sequential - validates all implementations)
```

---

## Implementation Strategy

### Sequential Delivery (Recommended for Foundation)

Foundation tasks are highly interdependent, so sequential execution is recommended:

1. **Day 1**: Complete Phase 1 (Setup) + Phase 2 (Foundational) + Phase 3 (DS1 - Database Schema)
   - Stop at T027 checkpoint: Verify schema in database

2. **Day 2**: Complete Phase 4 (DS2 - Repository Layer)
   - Write tests first (T028-T032)
   - Verify tests FAIL
   - Implement repositories (T033-T040)
   - Stop at T041 checkpoint: Verify repository tests pass

3. **Day 3**: Complete Phase 5 (DS3 - Unit of Work) + Phase 6 (DS4 - Test Infrastructure)
   - Write tests first (T042-T046)
   - Verify tests FAIL
   - Implement state transitions and UoW (T047-T051)
   - Stop at T055 checkpoint: Verify test infrastructure validated

4. **Day 4**: Complete Phase 7 (DS5 - FastAPI) + Phase 8 (Polish)
   - Implement FastAPI app (T056-T061)
   - Stop at T061 checkpoint: Verify health check working
   - Polish and validate (T062-T066)
   - Final validation: Run quickstart.md end-to-end

### Parallel Team Strategy

If multiple developers available:

1. **Day 1**: All together on Setup + Foundational + DS1 (critical path)
2. **Day 2**:
   - Developer A: DS2 tests (T028-T032)
   - Developer B: DS2 repositories (T034-T040) - starts after models ready
3. **Day 3**:
   - Developer A: DS3 UoW tests + implementation (T042-T051)
   - Developer B: DS4 test infrastructure validation (T052-T055)
4. **Day 4**:
   - Developer A: DS5 FastAPI implementation (T056-T061)
   - Developer B: Polish tasks (T062-T066)

---

## Notes

- **[P] tasks**: Different files, no dependencies, can run in parallel
- **[Story] label**: Maps task to specific developer story for traceability
- **USER ACTION REQUIRED tasks**: Stop and wait for user to execute command, then continue
- Each developer story should be independently completable and testable
- Verify tests fail before implementing (TDD)
- Commit after each task or logical group
- Stop at checkpoints to validate story independently
- Foundation is critical path: Features 003b-003e cannot start until this is complete

### User Action Tasks Summary

Tasks requiring manual user intervention (must stop and provide instructions):

- **T004**: Copy .env.example to .env
- **T026**: Start PostgreSQL with docker compose
- **T027**: Run Alembic migrations
- **T028**: Verify database schema
- **T042**: Run repository tests
- **T052**: Run UoW and state transition tests
- **T054**: Run full test suite
- **T055**: Verify UTC timezone enforcement
- **T056**: Verify test isolation
- **T059**: Build and start services with docker compose
- **T060**: Verify health check endpoint
- **T061**: Verify Swagger UI
- **T062**: Test database connection failure
- **T066**: Run quickstart validation
- **T067**: Verify all success criteria

**Total Tasks**: 67 (10 setup, 7 foundational, 50 developer story implementation, 5 polish)
**User Action Tasks**: 14 (marked with [USER ACTION REQUIRED])
**Parallelizable Tasks**: 37 (marked with [P])
**Estimated Duration**: 4 days (per plan.md constraint)
