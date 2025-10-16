# Feature Specification: 003a Backend Foundation - Shared Infrastructure

**Feature Branch**: `003-003a-backend-foundation`
**Created**: 2025-10-16
**Status**: Draft
**Input**: User description: "003a Backend Foundation - Shared Infrastructure"

## Clarifications

### Session 2025-10-16

- Q: What should the worker polling interval be when zero rows are returned? → A: 1 second (low latency, higher DB load)
- Q: When `token.mark_failed(error_dict)` is called, should the system automatically retry the operation, or is retry logic handled by workers? → A: Token state tracks failure, workers decide retry (foundation scope only)
- Q: For structured logging (FR-030), which log levels should be used for repository operations and database queries? → A: No query logging (only errors), INFO for transactions
- Q: When the database connection pool is exhausted, what should happen to new requests? → A: Configure pool size to 200 connections to ensure adequate capacity for all workers and API requests
- Q: When testcontainer fails to start within the default timeout, what should the timeout duration be before pytest fails? → A: 60 seconds (fast feedback for CI)

## User Scenarios & Testing *(mandatory)*

This foundation spec has no direct user-facing scenarios since it establishes infrastructure for future features (003b-003e). Instead, we define **developer scenarios** as the primary users are developers building features on this foundation.

### Developer Story 1 - Database Schema Ready for Feature Development (Priority: P1)

A developer starting work on 003b (Event Detection) needs to store mint event data and token records. They should be able to query the database schema, understand the data model, and start writing repository methods without creating migrations.

**Why this priority**: Without a complete schema, no feature can be built. This is the critical path blocker.

**Independent Test**: Developer can run `alembic upgrade head` successfully, inspect database tables, and verify all 7 tables exist with correct columns, indexes, and constraints.

**Acceptance Scenarios**:

1. **Given** a fresh PostgreSQL database, **When** developer runs `alembic upgrade head`, **Then** all 7 tables are created (authors, tokens_s0, mint_events, image_generation_jobs, ipfs_upload_records, reveal_transactions, system_state)
2. **Given** database migrations applied, **When** developer inspects `tokens_s0` table, **Then** status column is an enum with values: detected, generating, uploading, ready, revealed, failed
3. **Given** database schema is ready, **When** developer attempts to insert duplicate mint event (same tx_hash + log_index), **Then** database constraint prevents duplicate and raises unique violation error

---

### Developer Story 2 - Repository Layer Available for Data Access (Priority: P2)

A developer implementing the image generation worker (003c) needs to fetch tokens with status="detected" and update their status to "generating". They should be able to use repository methods without writing raw SQL or worrying about concurrent access from multiple workers.

**Why this priority**: Repository layer abstracts database complexity and ensures worker coordination through `FOR UPDATE SKIP LOCKED`. Required immediately after schema is ready.

**Independent Test**: Developer can instantiate a TokenRepository, call `get_pending_for_generation(limit=10)`, and receive a list of Token objects. When two workers call this method simultaneously, they receive different non-overlapping sets of tokens.

**Acceptance Scenarios**:

1. **Given** 20 tokens with status="detected" exist in database, **When** developer calls `TokenRepository.get_pending_for_generation(limit=10)`, **Then** method returns exactly 10 Token objects ordered by mint_timestamp (oldest first)
2. **Given** Worker A and Worker B both call `get_pending_for_generation(limit=5)` at the same time, **When** queries execute concurrently, **Then** Worker A gets tokens 1-5, Worker B gets tokens 6-10 (no overlap due to `FOR UPDATE SKIP LOCKED`)
3. **Given** a Token object with status="detected", **When** developer calls `token.mark_generating()`, **Then** token status transitions to "generating" and method validates the transition is legal

---

### Developer Story 3 - Unit of Work Pattern for Transaction Management (Priority: P2)

A developer implementing the reveal worker (003d) needs to update multiple records atomically: mark token as "revealed", insert reveal transaction record, and update system state. If any step fails, all changes should rollback. They should be able to manage this through a simple UoW pattern with automatic commit on context exit.

**Why this priority**: Transaction boundaries are critical for data integrity. Autocommit on successful context exit ensures changes persist without manual commit calls, while exceptions trigger automatic rollback.

**Independent Test**: Developer creates a UoW context, performs multiple repository operations, and exits context successfully. Changes are automatically persisted. If an exception occurs, changes are automatically rolled back.

**Acceptance Scenarios**:

1. **Given** a UoW context manager, **When** developer calls `uow.tokens.get_by_id(42)`, modifies the token, and exits context successfully (no exceptions), **Then** changes are automatically committed to database
2. **Given** a UoW context with pending changes, **When** an exception is raised within the context, **Then** transaction is automatically rolled back and database state is unchanged
3. **Given** a UoW factory is configured in FastAPI app, **When** developer uses dependency injection to get UoW in a route handler, **Then** UoW is automatically created for the request scope and commits on successful completion

---

### Developer Story 4 - Test Infrastructure Ready for TDD (Priority: P3)

A developer writing tests for TokenRepository needs a real PostgreSQL database (not mocks) to verify `FOR UPDATE SKIP LOCKED` behavior. They should be able to run `pytest` and have a test database automatically provisioned, migrations applied, and cleaned between tests.

**Why this priority**: TDD is part of the constitution for complex logic. Test infrastructure enables this. Lower priority because it can be added after core infrastructure.

**Independent Test**: Developer writes a test for `TokenRepository.get_pending_for_generation()`, runs `pytest`, and test passes using a real PostgreSQL instance via testcontainers.

**Acceptance Scenarios**:

1. **Given** a test file imports `uow_factory` fixture, **When** developer runs `pytest`, **Then** testcontainer starts PostgreSQL, applies migrations, and provides a working UoW factory
2. **Given** multiple tests in a test suite, **When** pytest runs them sequentially, **Then** each test gets a clean database state (tables truncated between tests)
3. **Given** tests run in CI environment, **When** pytest executes, **Then** UTC timezone is enforced (TZ=UTC) via autouse fixture

---

### Developer Story 5 - FastAPI Application Starts Successfully (Priority: P3)

A developer running the full stack needs to start the backend API service and verify it's healthy before implementing webhook routes (003b). They should be able to run `docker compose up` and see the API respond to health checks.

**Why this priority**: Validates end-to-end infrastructure (Docker, database connection, FastAPI app) works. Lower priority because it's integration-focused, not feature-critical.

**Independent Test**: Developer runs `docker compose up`, waits for services to start, calls `GET /health`, and receives `200 OK` response.

**Acceptance Scenarios**:

1. **Given** Docker Compose configuration exists, **When** developer runs `docker compose up --build`, **Then** both `postgres` and `backend-api` services start without errors
2. **Given** backend-api service is running, **When** developer sends `GET http://localhost:8000/health`, **Then** API returns `200 OK` with JSON response `{"status": "healthy"}`
3. **Given** database connection fails, **When** developer starts the API, **Then** startup fails with clear error message indicating database connection issue

---

### Edge Cases

- **What happens when migrations are run twice?** Alembic detects current schema version and skips already-applied migrations (idempotent)
- **What happens when a worker crashes mid-transaction?** PostgreSQL automatically rolls back uncommitted transactions; token remains in previous status and can be reprocessed
- **What happens when FOR UPDATE SKIP LOCKED returns zero rows?** Worker receives empty list and sleeps for poll interval (1 second) before retrying
- **What happens when testcontainer fails to start in CI?** pytest fails fast with clear error message indicating Docker availability issue
- **What happens when UTC timezone is not enforced?** Tests may pass locally but fail in CI or production with different timezones; autouse fixture prevents this
- **What happens when invalid state transition is attempted?** (e.g., `token.mark_revealed()` when status is "detected") Domain method raises `InvalidStateTransition` exception with descriptive error message

## Requirements *(mandatory)*

### Functional Requirements

#### Database Schema

- **FR-001**: System MUST create 7 database tables: `authors`, `tokens_s0`, `mint_events`, `image_generation_jobs`, `ipfs_upload_records`, `reveal_transactions`, `system_state`
- **FR-002**: `authors` table MUST enforce UNIQUE constraint on `wallet_address` column
- **FR-003**: `tokens_s0` table MUST have index on `(status, mint_timestamp)` for efficient worker polling queries
- **FR-004**: `tokens_s0` table MUST have `status` column as enum with values: `detected`, `generating`, `uploading`, `ready`, `revealed`, `failed`
- **FR-005**: `mint_events` table MUST have UNIQUE constraint on `(tx_hash, log_index)` to prevent duplicate event processing
- **FR-006**: `system_state` table MUST support jsonb storage for `state_value` column to store arbitrary structured data
- **FR-007**: All timestamp columns MUST store UTC timestamps (no timezone-aware types, enforce UTC at application level)

#### Repository Layer

- **FR-008**: System MUST provide `TokenRepository.get_pending_for_generation(limit)` method using `FOR UPDATE SKIP LOCKED` to prevent concurrent worker conflicts. Workers MUST poll with 1 second interval when zero rows returned.
- **FR-009**: System MUST provide `TokenRepository.get_pending_for_upload(limit)` method using `FOR UPDATE SKIP LOCKED`. Workers MUST poll with 1 second interval when zero rows returned.
- **FR-010**: System MUST provide `TokenRepository.get_ready_for_reveal(limit)` method using `FOR UPDATE SKIP LOCKED`. Workers MUST poll with 1 second interval when zero rows returned.
- **FR-011**: System MUST provide `AuthorRepository.get_by_wallet(wallet_address)` method returning single author or None
- **FR-012**: System MUST provide `MintEventRepository.exists(tx_hash, log_index)` method for duplicate detection
- **FR-013**: System MUST provide `SystemStateRepository.get_state(key)` and `set_state(key, value)` for singleton operational state
- **FR-014**: Repository methods MUST return SQLModel domain objects, not raw query results or dictionaries

#### Token State Transitions

- **FR-015**: `Token` model MUST provide `mark_generating()` method that validates current status is "detected" before transitioning to "generating"
- **FR-016**: `Token` model MUST provide `mark_uploading(image_path)` method that validates current status is "generating" before transitioning to "uploading"
- **FR-017**: `Token` model MUST provide `mark_ready(metadata_cid)` method that validates current status is "uploading" before transitioning to "ready"
- **FR-018**: `Token` model MUST provide `mark_revealed(tx_hash)` method that validates current status is "ready" before transitioning to "revealed"
- **FR-019**: `Token` model MUST provide `mark_failed(error_dict)` method that accepts current status from any non-terminal state and stores error in jsonb field. This method only records failure state; retry logic is handled by workers (out of foundation scope).
- **FR-020**: Invalid state transitions MUST raise `InvalidStateTransition` exception with descriptive error message

#### Unit of Work Pattern

- **FR-021**: System MUST provide `setup_db_session(db_url)` function returning `async_sessionmaker[AsyncSession]`
- **FR-022**: System MUST provide `create_uow_factory(session_factory)` function returning callable that produces UoW instances
- **FR-023**: `UnitOfWork` class MUST expose repository properties: `authors`, `tokens`, `mint_events`, `image_jobs`, `ipfs_records`, `reveal_txs`, `system_state`
- **FR-024**: `UnitOfWork` MUST automatically commit pending changes on successful context exit (when `__aexit__` receives no exception)
- **FR-025**: `UnitOfWork` MUST automatically rollback pending changes when exception occurs within context (when `__aexit__` receives exception)
- **FR-026**: `UnitOfWork` MAY provide optional explicit `commit()` and `rollback()` methods for manual transaction control if needed

#### Core Infrastructure

- **FR-027**: System MUST load configuration from environment variables using Pydantic BaseSettings (validation + type coercion)
- **FR-028**: System MUST enforce UTC timezone by importing `core/timezone.py` on application startup
- **FR-029**: System MUST provide FastAPI dependency injection for UoW factory via `core/dependencies.py`
- **FR-030**: System MUST use structured logging via structlog. Log levels: INFO for transaction boundaries (commit/rollback), ERROR for database errors. No query-level logging (keep logs minimal for MVP).
- **FR-030a**: System MUST configure database connection pool with 200 connections to ensure adequate capacity for concurrent workers and API requests

#### Database Migrations

- **FR-031**: System MUST use Alembic for database migrations with async support
- **FR-032**: Initial migration MUST create all 7 tables with indexes, constraints, and enum types
- **FR-033**: Migration scripts MUST be idempotent (safe to run multiple times)
- **FR-034**: System MUST provide `alembic upgrade head` command to apply all pending migrations

#### Test Infrastructure

- **FR-035**: Test suite MUST use pytest as test runner
- **FR-036**: Test suite MUST use testcontainers to provision PostgreSQL instances for integration tests with 60 second startup timeout for fast CI feedback
- **FR-037**: Test suite MUST provide session-scoped `postgres_container` fixture
- **FR-038**: Test suite MUST provide function-scoped `session` fixture with table truncation between tests
- **FR-039**: Test suite MUST provide function-scoped `uow_factory` fixture for repository testing
- **FR-040**: Test suite MUST provide session-scoped autouse `utc_timezone` fixture that sets `TZ=UTC` environment variable
- **FR-041**: Test suite MUST test complex repository logic: `FOR UPDATE SKIP LOCKED` behavior, concurrent access, state transitions
- **FR-042**: Test suite MUST skip testing simple CRUD operations (add, get_by_id) per constitution guidelines

#### FastAPI Application

- **FR-043**: System MUST provide FastAPI application factory with lifespan context manager for startup/shutdown
- **FR-044**: FastAPI app MUST store UoW factory in `app.state` for request-scoped access
- **FR-045**: FastAPI app MUST provide `GET /health` endpoint returning `200 OK` with JSON `{"status": "healthy"}`
- **FR-046**: FastAPI app MUST enable CORS for development (configurable via environment variables)
- **FR-047**: FastAPI app MUST use structured logging for all HTTP requests and responses

#### Docker Infrastructure

- **FR-048**: System MUST provide `docker-compose.yml` with services: `postgres` and `backend-api`
- **FR-049**: System MUST provide Dockerfile using `python:3.14-slim` base image with uv package manager
- **FR-050**: System MUST provide `.env.example` documenting all required environment variables with comments, including database pool configuration (200 connections)
- **FR-051**: Docker Compose services MUST share single `.env` file at repository root

### Key Entities

- **Author**: Represents an NFT author/creator with wallet address, social handles (twitter, farcaster), and AI prompt text for image generation
- **Token**: Represents a minted NFT token with lifecycle status (detected → generating → uploading → ready → revealed), relationships to author and minter, and metadata CIDs
- **MintEvent**: Represents a blockchain mint event log entry for deduplication and recovery, identified by transaction hash and log index
- **ImageGenerationJob**: Tracks image generation attempts for a token including service used (replicate/selfhosted), status, and retry count
- **IPFSUploadRecord**: Tracks IPFS upload attempts for token images and metadata including CID, status, and retry count
- **RevealTransaction**: Tracks batch reveal transactions including array of token IDs revealed together, transaction hash, and gas price paid
- **SystemState**: Singleton key-value store for operational state like last processed blockchain block number and service health metrics

### Relationships

- Token → Author (many-to-one): Each token has one author via `author_id` foreign key
- Token → ImageGenerationJob (one-to-many): Each token can have multiple generation attempts tracked
- Token → IPFSUploadRecord (one-to-many): Each token can have multiple upload attempts (image + metadata)
- Token → RevealTransaction (many-to-many): Tokens are revealed in batches, tracked via `token_ids` array in reveal transaction

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Developer can run `docker compose up` and both services start successfully within 30 seconds
- **SC-002**: Developer can run `alembic upgrade head` and all migrations apply successfully in under 5 seconds on an empty database
- **SC-003**: Developer can run `pytest` and all foundation tests pass within 60 seconds (including testcontainer provisioning)
- **SC-004**: Developer can call `GET /health` and receive `200 OK` response in under 100ms
- **SC-005**: Two concurrent workers calling `TokenRepository.get_pending_for_generation(limit=10)` receive zero overlapping tokens (100% coordination via FOR UPDATE SKIP LOCKED)
- **SC-006**: Attempting invalid state transition (e.g., detected → revealed) raises exception 100% of the time with descriptive error message
- **SC-007**: Running tests in any timezone produces identical results (UTC enforcement via autouse fixture)
- **SC-008**: Developer can implement a new repository method following existing patterns in under 15 minutes (measure of code clarity and pattern consistency)

## Assumptions

- **AS-001**: Developers implementing features (003b-003e) have basic familiarity with Python async/await patterns
- **AS-002**: Docker and Docker Compose are available in development and CI environments
- **AS-003**: PostgreSQL version 14 or higher is used (for improved JSONB support and performance)
- **AS-004**: Python 3.14 is available (standard GIL-enabled version, not free-threaded mode)
- **AS-005**: Development machines have sufficient resources to run testcontainers (Docker, 2GB+ RAM for test database)
- **AS-006**: Database connection pool sized at 200 connections is sufficient for MVP load (concurrent workers + API requests). Infrastructure and programs are self-managed; capacity planning ensures pool exhaustion never occurs.
- **AS-007**: No authentication/authorization is needed for this foundation phase (admin API is CLI-access only per MASTER_DESIGN.md)
- **AS-008**: Structured logging format (JSON vs text) will be configured via environment variables for different deployment environments

## Constraints

- **C-001**: Foundation scope explicitly excludes all feature implementations (no webhooks, workers, external API clients)
- **C-002**: No integration with external services (Alchemy, Pinata, Replicate) in this phase
- **C-003**: Repository pattern must NOT use generic base classes (per GLISK constitution: "simple direct repositories")
- **C-004**: Testing must focus on complex logic only; simple CRUD methods are skipped (per GLISK constitution)
- **C-005**: All implementation must follow "Seasonal MVP" philosophy: simple, direct, rebuild over maintain
- **C-006**: Timeline constraint: 4 days total for complete foundation implementation
- **C-007**: Tech stack is fixed: Python 3.14, FastAPI, PostgreSQL, SQLModel, psycopg (no substitutions)

## Dependencies

- **DEP-001**: External Python packages: fastapi, sqlmodel, psycopg (psycopg3 async), alembic, pydantic, structlog, pytest, testcontainers
- **DEP-002**: Docker and Docker Compose for local development and testing
- **DEP-003**: PostgreSQL 14+ for production database
- **DEP-004**: MASTER_DESIGN.md document defines data model schema and architectural decisions referenced in this spec
- **DEP-005**: GLISK Constitution (in CLAUDE.md) defines code style and testing philosophy
- **DEP-006**: Feature specs 003b-003e will build on this foundation (future dependencies)

## Scope

### In Scope

- Complete database schema with all 7 tables, indexes, constraints
- Repository layer for all entities with worker coordination via FOR UPDATE SKIP LOCKED
- Token state transition methods with validation
- Unit of Work pattern for transaction management
- Core infrastructure: configuration, database setup, timezone enforcement, FastAPI dependencies
- Alembic migrations with async support
- Test infrastructure with testcontainers and focused test coverage
- Minimal FastAPI application with health endpoint
- Docker Compose setup for local development

### Out of Scope

- Alchemy webhook integration (003b)
- Image generation service clients (003c)
- IPFS/Pinata integration (003c)
- Blockchain reveal transaction logic (003d)
- Worker implementations (image, IPFS, reveal workers in 003b-003d)
- Admin API routes beyond health check (003e)
- CLI tools for manual operations (003e)
- Production deployment configuration (separate ops spec)
- Authentication and authorization
- Rate limiting or API security headers
- Monitoring and alerting infrastructure
- Business logic services (event parsing, metadata building, etc.)

## Risks

- **RISK-001**: Async SQLAlchemy with psycopg complexity could cause integration issues
  - *Mitigation*: Test infrastructure validates async patterns early with real database via testcontainers

- **RISK-002**: Alembic autogenerate may miss custom types (enums, jsonb arrays)
  - *Mitigation*: Manual verification of initial migration, explicit testing that schema matches SQLModel definitions

- **RISK-003**: FOR UPDATE SKIP LOCKED behavior may not work as expected under high concurrency
  - *Mitigation*: Repository tests explicitly cover concurrent worker scenarios, validate no row overlap

- **RISK-004**: Timezone issues may surface in production despite UTC enforcement
  - *Mitigation*: Autouse fixture in tests, explicit UTC checks in CI, documentation for deployment

- **RISK-005**: State transition validation may be bypassed if developers directly set status field
  - *Mitigation*: Code review guidelines, linting rules to detect direct status assignment, comprehensive tests for transition methods

## Notes

### Implementation Sequence

Recommended order for building foundation components:

1. **Day 1 - Database Schema**
   - Define SQLModel entities with all fields, relationships, validators
   - Create initial Alembic migration (with manual verification of enums/jsonb)
   - Test migration applies cleanly to fresh PostgreSQL instance

2. **Day 2 - Repository Layer**
   - Implement all 7 repositories with required query methods
   - Add state transition methods to Token model
   - Write tests for FOR UPDATE SKIP LOCKED and state transitions (mandatory per constitution)

3. **Day 3 - Core Infrastructure + UoW**
   - Implement UnitOfWork pattern with repository coordination
   - Build core infrastructure: config, database setup, timezone enforcement
   - Create test infrastructure with testcontainers fixtures
   - Run full test suite to validate foundation

4. **Day 4 - FastAPI + Docker**
   - Build minimal FastAPI application with health endpoint
   - Create Dockerfile with python:3.14-slim and uv
   - Write docker-compose.yml with postgres + backend-api services
   - End-to-end validation: `docker compose up` → `GET /health` → `pytest`

### Code Quality Guidelines

- **Repository Methods**: Each method must have docstring explaining query purpose (e.g., "Get tokens ready for image generation. Uses FOR UPDATE SKIP LOCKED for worker coordination.")
- **State Transition Methods**: Include clear error messages in raised exceptions (e.g., "Cannot transition from 'uploading' to 'revealed'. Token must be in 'ready' state.")
- **Test Names**: Use descriptive names that explain what's being tested (e.g., `test_concurrent_workers_receive_non_overlapping_tokens`)
- **Configuration**: All environment variables must have defaults or fail fast with clear error if required value is missing

### Deferred Decisions

These architectural choices are explicitly deferred to future specs or iteration:

- **Value Objects for Wallet/CID**: Deferred until we hit 3 validation bugs (current: use Pydantic validators)
- **Domain Events**: Deferred until cross-module communication is needed (unlikely for seasonal MVP)
- **Generic Repository Base**: Deferred forever per constitution (use simple direct repositories)
- **Complex Aggregate Patterns**: Deferred until domain complexity increases significantly
