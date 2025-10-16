# Research: 003a Backend Foundation

**Feature**: Backend Foundation - Shared Infrastructure
**Date**: 2025-10-16
**Phase**: 0 (Pre-implementation Research)

## Purpose

This document consolidates architectural decisions and best practices research for the backend foundation. Since this is foundational infrastructure, decisions here impact all future features (003b-003e).

## Key Architectural Decisions

### 1. Async SQLAlchemy + psycopg3 for Database Access

**Decision**: Use SQLModel (built on SQLAlchemy 2.0) with async psycopg3 driver

**Rationale**:
- SQLModel combines Pydantic validation with SQLAlchemy ORM (type safety + database)
- Async required for FastAPI application (avoid blocking event loop)
- psycopg3 is the modern async PostgreSQL driver (psycopg2 is sync-only)
- SQLModel reduces boilerplate compared to raw SQLAlchemy

**Alternatives Considered**:
- **Raw SQL with asyncpg**: More control, but verbose and error-prone. Rejected because SQLModel provides type safety and validation without significant overhead.
- **SQLAlchemy Core (no ORM)**: Lighter weight, but loses domain model benefits. Rejected because state transition methods on Token model require ORM.
- **Tortoise ORM**: Simpler async ORM, but less mature ecosystem. Rejected because SQLModel has better FastAPI integration and Pydantic compatibility.

**Implementation Notes**:
- Use `async_sessionmaker[AsyncSession]` for session factory
- All repository methods are async (`async def`)
- All queries use `await session.execute()`

---

### 2. Unit of Work Pattern for Transaction Management

**Decision**: Implement UoW pattern as async context manager with automatic commit/rollback

**Rationale**:
- Workers need atomic multi-repository updates (e.g., reveal worker: update token + insert reveal_tx + update system_state)
- Automatic commit on successful exit reduces developer error
- Automatic rollback on exception prevents orphaned transactions
- FastAPI dependency injection provides request-scoped UoW instances

**Alternatives Considered**:
- **Manual session management**: Developers pass session to every repository method. Rejected because error-prone (forget commit/rollback) and verbose.
- **Nested transactions with savepoints**: More complex, not needed for MVP. Rejected because simple commit/rollback is sufficient.
- **No transactions (autocommit)**: Dangerous for multi-step operations. Rejected because data integrity is critical.

**Implementation Notes**:
```python
async with uow:
    token = await uow.tokens.get_by_id(42)
    token.mark_revealed("0xabc...")
    await uow.reveal_txs.add(reveal_tx)
    # Automatic commit on exit (or rollback if exception raised)
```

---

### 3. FOR UPDATE SKIP LOCKED for Worker Coordination

**Decision**: Use PostgreSQL row-level locking with SKIP LOCKED to prevent concurrent workers from processing same tokens

**Rationale**:
- Multiple workers poll for pending tokens simultaneously
- SKIP LOCKED allows Worker A to get tokens 1-5 while Worker B gets tokens 6-10 (no overlap, no blocking)
- Database-level coordination is simpler than distributed locks (Redis, etc.)
- PostgreSQL native feature, no external dependencies

**Alternatives Considered**:
- **SELECT without locking + optimistic updates**: Race conditions possible, tokens processed multiple times. Rejected because waste of compute/API costs.
- **Redis distributed lock**: Requires Redis infrastructure, more complex. Rejected because PostgreSQL row locking is sufficient for MVP.
- **Single worker (no coordination)**: Doesn't scale to handle burst mints. Rejected because we need horizontal scaling.

**Implementation Notes**:
```sql
SELECT * FROM tokens_s0
WHERE status = 'detected'
ORDER BY mint_timestamp ASC
LIMIT 10
FOR UPDATE SKIP LOCKED
```

---

### 4. Testcontainers for Integration Testing

**Decision**: Use testcontainers-python to provision real PostgreSQL instances for tests

**Rationale**:
- FOR UPDATE SKIP LOCKED behavior cannot be mocked effectively
- State transition logic needs real database constraints
- Mocks give false confidence (tests pass, production fails)
- Testcontainers cleanup is automatic (no leftover test databases)

**Alternatives Considered**:
- **SQLite in-memory**: Fast, but doesn't support PostgreSQL-specific features (SKIP LOCKED, JSONB arrays). Rejected because test environment too different from production.
- **Shared test database**: Fast, but test pollution between runs. Rejected because parallel test execution breaks.
- **Mocks (unittest.mock)**: Fast, but doesn't test database integration. Rejected per constitution (focus on complex logic, not mocks).

**Implementation Notes**:
- Session-scoped `postgres_container` fixture (starts once, shared across tests)
- Function-scoped `session` fixture (truncates tables between tests for isolation)
- 60 second startup timeout for fast CI feedback

---

### 5. Alembic for Schema Migrations (with PostgreSQL Enum Support)

**Decision**: Use Alembic with async support and `alembic-postgresql-enum` for database migrations

**Rationale**:
- Standard Python migration tool (SQLAlchemy ecosystem)
- Supports async engine initialization
- **Autogenerate migrations** from SQLModel definitions with manual verification (NOT manual creation)
- `alembic-postgresql-enum` handles PostgreSQL ENUM type changes properly (ADD/REMOVE values, renames)
- Version control for schema changes

**Alternatives Considered**:
- **Manual SQL scripts**: No version tracking, error-prone. Rejected because Alembic provides migration history.
- **SQLAlchemy create_all()**: No migration support, can't evolve schema. Rejected because we need migration tracking.
- **Manual migration writing**: Error-prone, especially for enums. Rejected because autogenerate + verification is faster and safer.
- **Django migrations**: Wrong framework. N/A.

**Implementation Notes**:
- **Workflow**: `alembic revision --autogenerate -m "description"` → manually verify → apply
- Use `alembic-postgresql-enum` operations (`sync_enum_values`) for enum migrations
- Verify generated migrations check: enum types, indexes, foreign key cascades
- Test idempotency: `upgrade head && downgrade base && upgrade head` must succeed

---

### 6. State Transition Methods on Token Model

**Decision**: Implement state changes as methods on Token domain model (not repository or service layer)

**Rationale**:
- Validation logic belongs with the entity (Token knows valid transitions)
- Prevents invalid state changes (e.g., detected → revealed without intermediate steps)
- Self-documenting code (method names explain intent: `mark_generating()`)
- Consistent error messages across codebase

**Alternatives Considered**:
- **Direct status field assignment**: No validation, easy to create invalid states. Rejected because state machine is critical business logic.
- **Service layer methods**: Token becomes anemic domain model (data bag). Rejected because violates domain-driven design principles.
- **Database triggers**: Hard to test, hides logic. Rejected because Python code is more maintainable.

**Implementation Notes**:
```python
# Token model (models/token.py)
def mark_generating(self) -> None:
    if self.status != TokenStatus.DETECTED:
        raise InvalidStateTransition(
            f"Cannot mark generating from {self.status}. Token must be in detected state."
        )
    self.status = TokenStatus.GENERATING
```

---

### 7. Minimal Logging Strategy

**Decision**: Log only transaction boundaries (commit/rollback) at INFO level and database errors at ERROR level. No query-level logging.

**Rationale**:
- MVP needs clean logs for debugging (not drowned in SELECT spam)
- Query logging creates high volume (200 connection pool × workers = many queries)
- Transaction boundaries are sufficient for debugging worker flows
- Structured logging (structlog) enables log aggregation if needed later

**Alternatives Considered**:
- **Log all queries at DEBUG**: Useful for development, but too verbose. Rejected because MVP prioritizes clean logs.
- **Log slow queries only (>100ms)**: Useful for optimization, but adds complexity. Rejected because performance tuning is post-MVP.
- **No logging**: Impossible to debug. Rejected because we need transaction visibility.

**Implementation Notes**:
- structlog configured in `core/config.py`
- UoW logs `transaction.committed` and `transaction.rolled_back` events
- Repository methods do not log (silent success, only errors logged)

---

### 8. 200 Connection Pool Size

**Decision**: Configure PostgreSQL connection pool with 200 connections

**Rationale**:
- Self-managed infrastructure (control both application and database)
- Adequate capacity ensures pool exhaustion never occurs in MVP
- Simpler than complex pool sizing math or dynamic scaling
- 200 connections is well within PostgreSQL default limits (default max_connections = 100, easily increased to 200+)

**Alternatives Considered**:
- **Small pool + queue**: Add complexity (timeout logic, backpressure handling). Rejected because we control infrastructure and can provision adequate capacity.
- **Dynamic pool scaling**: Overkill for MVP, adds latency. Rejected because static sizing is sufficient.
- **Connection-per-request**: Slow connection establishment overhead. Rejected because pooling is standard practice.

**Implementation Notes**:
- Set in `core/database.py`: `pool_size=200`
- Document in `.env.example`: `DB_POOL_SIZE=200`
- PostgreSQL server must have `max_connections >= 200` (configure in docker-compose or cloud provider)

---

### 9. Direct Repository Pattern (No Base Class)

**Decision**: Each repository is a standalone class with explicit methods. No generic base class or inheritance.

**Rationale**:
- GLISK constitution principle: "simple direct repositories"
- Avoids premature abstraction (YAGNI)
- Each repository has unique query patterns (Token has FOR UPDATE SKIP LOCKED, Author has wallet lookup)
- Generic base classes add cognitive overhead for little benefit in MVP

**Alternatives Considered**:
- **Generic Repository<T>**: DRY for CRUD, but hides query complexity. Rejected per constitution.
- **Repository interfaces**: Useful for mocking, but adds boilerplate. Rejected because testcontainers give real database tests.

**Implementation Notes**:
- Each repository takes `AsyncSession` in `__init__`
- Common patterns copy-pasted across repositories (acceptable per seasonal MVP philosophy)
- Refactor to base class only if duplication becomes painful (measure: >3 identical methods across repos)

---

### 10. UTC Timezone Enforcement

**Decision**: Enforce UTC timezone at application startup and in test suite via autouse fixture

**Rationale**:
- Prevents timezone bugs (tests pass locally in PST, fail in CI in UTC)
- Database stores timestamps without timezone info (application-level enforcement)
- Explicit > implicit (Python default timezone is system-dependent)

**Alternatives Considered**:
- **Timezone-aware timestamps**: PostgreSQL `timestamptz` type. Rejected because UTC-only is simpler (no timezone conversions).
- **No enforcement, rely on system**: Dangerous, environment-dependent. Rejected because tests must be reproducible.

**Implementation Notes**:
- `core/timezone.py`: Sets `TZ=UTC` environment variable, imported by `app.py` on startup
- `conftest.py`: Session-scoped autouse fixture sets `TZ=UTC` for all tests
- All datetime objects use `datetime.utcnow()` or `datetime.now(timezone.utc)`

---

### 11. Code Quality Tools (Ruff + Pyright)

**Decision**: Use Ruff for linting/formatting and Pyright for type checking

**Rationale**:
- **Ruff**: 10-100x faster than Black+Flake8+isort combined, single tool for all checks
- **Pyright**: Fast, accurate Python type checker (used by VS Code Pylance)
- Pre-commit hooks ensure code quality before commits (repo-wide consistency)
- Minimal configuration needed (sensible defaults)

**Alternatives Considered**:
- **Black + Flake8 + isort**: Slower, multiple tools. Rejected because Ruff does all three.
- **mypy**: Slower than pyright, less accurate on complex types. Rejected for MVP speed.
- **pylint**: Too slow, too opinionated. Rejected because Ruff is sufficient.

**Implementation Notes**:
- `pyproject.toml` [tool.ruff]: line-length=100, select=["E", "F", "I"], fix=true
- `pyproject.toml` [tool.pyright]: typeCheckingMode="basic", venvPath="."
- `.pre-commit-config.yaml` at repo root with ruff (lint+format), pyright, trailing-whitespace

---

### 12. Environment Configuration Location

**Decision**: Store `.env` file at repository root (not `backend/.env`)

**Rationale**:
- Single source of truth for all environment variables across monorepo
- Docker Compose can reference `../.env` from backend service
- Pre-commit hooks and scripts can access config from consistent location
- Simpler for developers (one file to manage, not one per domain)

**Alternatives Considered**:
- **Per-domain .env files** (backend/.env, contracts/.env): More isolated, but creates duplication and sync issues. Rejected because we have one database, one deployment.
- **Environment-specific files** (.env.dev, .env.prod): More complex. Rejected because APP_ENV variable is sufficient for MVP.

**Implementation Notes**:
- `/.env.example` documents all variables
- `/.env` is gitignored
- Docker Compose services use `env_file: ../.env` to reference root config
- Update spec.md FR-051 to clarify "repository root" means literally `/` not `backend/`

---

### 13. PostgreSQL Database Initialization

**Decision**: Use Docker environment variables for database/user creation (no `initdb.sh` for MVP)

**Rationale**:
- PostgreSQL official image auto-creates database + user from `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` env vars
- Simpler than maintaining shell scripts
- No PostgreSQL extensions needed for MVP (UUID generated in Python, JSONB/arrays native)
- Can add `initdb.sh` later if extensions become necessary

**Alternatives Considered**:
- **initdb.sh with extensions**: More control, but unnecessary for MVP. Deferred until we need extensions (uuid-ossp, pg_stat_statements, etc.).
- **Application-level database creation**: Requires elevated permissions, more complex. Rejected because Docker image handles it.

**Implementation Notes**:
```yaml
postgres:
  environment:
    POSTGRES_DB: glisk
    POSTGRES_USER: glisk
    POSTGRES_PASSWORD: glisk
  command: ["postgres", "-c", "max_connections=200"]
```

**Future**: Add `backend/postgres/initdb.sh` if we need extensions or custom permissions

---

### 14. Docker Build Optimization

**Decision**: Use `.dockerignore` to exclude unnecessary files from Docker build context

**Rationale**:
- Faster builds (smaller context sent to Docker daemon)
- Prevent sensitive files (.env) from being copied into images
- Layer caching efficiency (exclude frequently changing files like test artifacts)

**Implementation Notes**:
- Create `backend/.dockerignore` excluding: .env, .git, tests/, __pycache__/, *.pyc, .pytest_cache, htmlcov/, .coverage, .mypy_cache, .ruff_cache
- Keep pyproject.toml and uv.lock in context (needed for dependency installation)

---

## Technology Best Practices

### FastAPI with Async SQLAlchemy

**Best Practices**:
1. **Dependency injection for UoW**: Use FastAPI `Depends()` to inject UoW factory into routes
2. **Lifespan context manager**: Initialize database connection pool on startup, close on shutdown
3. **Store factories in app.state**: UoW factory accessible to routes via `request.app.state`

**Pitfalls to Avoid**:
- Don't mix sync and async code (no `asyncio.run()` inside async functions)
- Don't create session per route manually (use dependency injection)
- Don't forget to await repository methods (will return coroutine, not result)

### SQLModel + Alembic + alembic-postgresql-enum

**Best Practices**:
1. **Use `alembic revision --autogenerate`**: Let Alembic detect schema changes automatically
2. **Manual verification required**: Review generated migration for enum handling, indexes, cascades
3. **Import all models in alembic/env.py**: Ensures metadata is complete for autogenerate
4. **Use `alembic-postgresql-enum`**: Handles PostgreSQL ENUM changes properly (add/remove values)
5. **Test idempotency**: Run `upgrade → downgrade → upgrade` to verify migrations are reversible

**Pitfalls to Avoid**:
- Don't blindly trust autogenerate without reviewing SQL (especially for enums)
- Don't manually write migrations unless autogenerate fails (error-prone, slower)
- Don't use `cascade="all,delete"` without testing (can delete unintended rows)
- Don't forget to add `alembic-postgresql-enum` to dependencies

### Testcontainers

**Best Practices**:
1. **Session-scoped container**: Start once, reuse across tests (faster)
2. **Function-scoped session with truncation**: Isolation without recreating database
3. **Explicit timeout**: 60 seconds prevents hanging CI

**Pitfalls to Avoid**:
- Don't use `@pytest.mark.asyncio` without `pytest-asyncio` plugin
- Don't forget to close sessions (use fixtures with `yield`)
- Don't share sessions between tests (data pollution)

---

## Open Questions for Future Features

These questions are deferred to features 003b-003e:

1. **Worker retry logic**: How many retries? Exponential backoff? → 003b (Event Detection)
2. **Worker error handling**: What happens when Replicate API fails? → 003c (Image Generation)
3. **Batch reveal optimization**: How many tokens per batch? Gas cost analysis? → 003d (Reveal Worker)
4. **Admin API authentication**: JWT? API keys? → 003e (Admin API)

---

## References

- [SQLModel Documentation](https://sqlmodel.tiangolo.com/)
- [FastAPI Async SQL Databases Guide](https://fastapi.tiangolo.com/advanced/async-sql-databases/)
- [Alembic Async Support](https://alembic.sqlalchemy.org/en/latest/cookbook.html#using-asyncio-with-alembic)
- [alembic-postgresql-enum GitHub](https://github.com/Pogchamp-company/alembic-postgresql-enum)
- [PostgreSQL Row Locking](https://www.postgresql.org/docs/current/sql-select.html#SQL-FOR-UPDATE-SHARE)
- [testcontainers-python](https://testcontainers-python.readthedocs.io/)
- [structlog Documentation](https://www.structlog.org/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Pyright Documentation](https://microsoft.github.io/pyright/)
- [pre-commit Framework](https://pre-commit.com/)
