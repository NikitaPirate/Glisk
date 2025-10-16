# GLISK Backend - Foundation Infrastructure

Backend foundation for the GLISK NFT lifecycle management system. Provides shared infrastructure for event detection (003b), image generation (003c), IPFS upload (003d), and reveal coordination (003e).

## Quick Start

```bash
# 1. Copy environment template (from repo root)
cp .env.example .env

# 2. Start services
docker compose up --build

# 3. Verify health (in new terminal)
curl http://localhost:8000/health
# Expected: {"status":"healthy"}

# 4. View API docs
open http://localhost:8000/docs
```

**For detailed setup instructions**, see: [Quickstart Guide](../specs/003-003a-backend-foundation/quickstart.md)

---

## Project Overview

This backend provides:
- **Database Schema**: 7 tables for NFT lifecycle (authors, tokens, mint events, image jobs, IPFS records, reveal transactions, system state)
- **Repository Layer**: Data access with FOR UPDATE SKIP LOCKED for worker coordination
- **Unit of Work Pattern**: Transaction management with automatic commit/rollback
- **FastAPI Application**: REST API with health checks and Swagger documentation
- **Docker Infrastructure**: Containerized PostgreSQL + backend API

**Technology Stack**:
- Python 3.14 (standard GIL-enabled)
- FastAPI + SQLModel + psycopg3 (async)
- PostgreSQL 17 (200 connection pool)
- Alembic migrations
- Pydantic settings + structlog
- pytest + testcontainers

---

## Architecture

```
backend/src/glisk/
├── core/
│   ├── config.py           # Environment configuration (Pydantic Settings)
│   ├── database.py         # Session factory with connection pooling
│   ├── timezone.py         # UTC enforcement (TZ=UTC)
│   └── dependencies.py     # FastAPI dependency injection (UoW factory)
│
├── models/                 # SQLModel entities (database tables)
│   ├── author.py           # Author entity with wallet validation
│   ├── token.py            # Token + TokenStatus enum + state transitions
│   ├── mint_event.py       # MintEvent with duplicate detection
│   ├── image_job.py        # ImageGenerationJob
│   ├── ipfs_record.py      # IPFSUploadRecord
│   ├── reveal_tx.py        # RevealTransaction
│   └── system_state.py     # SystemState (key-value store)
│
├── repositories/           # Data access layer (no base class - direct repos)
│   ├── author.py           # Case-insensitive wallet lookup
│   ├── token.py            # FOR UPDATE SKIP LOCKED for worker coordination
│   ├── mint_event.py       # Duplicate detection via SELECT EXISTS
│   ├── image_job.py
│   ├── ipfs_record.py
│   ├── reveal_tx.py
│   └── system_state.py     # JSON UPSERT operations
│
├── uow.py                  # Unit of Work pattern implementation
└── app.py                  # FastAPI application factory
```

**Key Design Patterns**:
- **Dependency Injection**: `Depends(get_uow)` injects UoW into routes
- **Unit of Work**: Manages transactions, provides repository access
- **Repository Pattern**: Abstracts data access, enables testing
- **State Machine**: Token state transitions with validation
- **FOR UPDATE SKIP LOCKED**: Ensures worker coordination (no duplicate work)

---

## Development Workflow

### Running Tests

```bash
# Run all tests (includes testcontainer startup ~3 seconds)
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_repositories.py

# Run tests matching pattern
uv run pytest -k "test_state_transitions"

# Run with coverage
uv run pytest --cov=glisk --cov-report=html
```

**Expected Output**:
```
========================= test session starts =========================
collected 11 items

tests/test_repositories.py ...                                  [ 27%]
tests/test_state_transitions.py ....                            [ 63%]
tests/test_uow.py ....                                          [100%]

========================= 11 passed in 2.60s =========================
```

### Database Migrations

```bash
# Apply migrations
uv run alembic upgrade head

# Create new migration (after modifying models)
uv run alembic revision --autogenerate -m "Description"

# View migration history
uv run alembic history

# Check current version
uv run alembic current
```

### Code Quality

```bash
# Format code with ruff
uv run ruff format src/ tests/

# Lint code
uv run ruff check src/ tests/

# Type checking
uv run pyright src/
```

### Running Locally (Development Mode)

```bash
# Start database only
docker compose up -d postgres

# Run backend with hot reload
uv run uvicorn glisk.app:app --reload --host 0.0.0.0 --port 8000
```

### Debugging

Enable debug logging in `.env`:
```env
LOG_LEVEL=DEBUG
```

View logs:
```bash
# Backend API logs
docker compose logs -f backend-api

# PostgreSQL logs
docker compose logs -f postgres

# All logs
docker compose logs -f
```

### Database Inspection

```bash
# Connect to PostgreSQL
docker exec -it backend-postgres-1 psql -U glisk -d glisk

# Useful psql commands:
\dt                          # List tables
\d tokens_s0                 # Describe table
SELECT * FROM authors;       # Query data
\q                           # Exit
```

---

## Testing Strategy

**Test Infrastructure** (testcontainers):
- Session-scoped PostgreSQL container (postgres:17)
- Automatic migrations via subprocess (avoids asyncio conflicts)
- Function-scoped session with table truncation (test isolation)
- UTC timezone enforcement (TZ=UTC autouse fixture)

**Test Coverage**:
- **Repository Tests** (3): Case-insensitive lookup, duplicate detection, UPSERT
- **State Transition Tests** (4): Valid transitions, invalid transitions, failed state, terminal states
- **Unit of Work Tests** (4): Commit on success, rollback on exception, repository access, atomic operations

**Test Performance**:
- First run: ~3 seconds (testcontainer startup)
- Subsequent runs: ~2.6 seconds
- Timezone-independent (UTC enforcement working)
- Perfect isolation (no test data leaks)

---

## Configuration

All configuration via `.env` file (copy from `.env.example`):

```env
# Database
DATABASE_URL=postgresql+psycopg://glisk:changeme@postgres:5432/glisk
DB_POOL_SIZE=200                    # Connection pool size

# Application
APP_ENV=development                 # development | production
LOG_LEVEL=INFO                      # DEBUG | INFO | WARNING | ERROR

# CORS
CORS_ORIGINS=http://localhost:3000  # Comma-separated list

# Server
HOST=0.0.0.0
PORT=8000
```

**Environment Variables** are validated via Pydantic Settings. Missing required variables cause startup failure with clear error messages.

---

## API Endpoints

### Health Check

```bash
GET /health
```

**Response (200 OK)**:
```json
{
  "status": "healthy"
}
```

**Response (503 Service Unavailable)** - when database is down:
```json
{
  "status": "unhealthy",
  "error": {
    "type": "OperationalError",
    "message": "connection failed: Connection refused..."
  }
}
```

### API Documentation

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI Spec**: `http://localhost:8000/openapi.json`

---

## Deployment

### Database Migrations in Production

**Current Approach**: Migrations run automatically on container startup via `entrypoint.sh`

Every container runs `alembic upgrade head` before starting the API. This is safe because:
- Alembic uses `alembic_version` table as a lock
- First container runs migrations, others wait
- PostgreSQL transaction isolation prevents corruption

**For detailed migration strategies** (including separate migration service approach), see: [DEPLOYMENT.md](./DEPLOYMENT.md)

### Docker Compose (Production)

```bash
# Build and start in background
# Migrations run automatically on startup
docker compose up --build -d

# Check startup logs (includes migration status)
docker compose logs backend-api | grep -E "Migrations|FastAPI"

# Check status
docker compose ps

# View logs
docker compose logs -f backend-api

# Stop services (keeps data)
docker compose down

# Stop and remove data
docker compose down -v
```

### Environment Variables

For production, update `.env`:
```env
APP_ENV=production
LOG_LEVEL=INFO
DATABASE_URL=postgresql+psycopg://user:pass@production-host:5432/glisk
DB_POOL_SIZE=200
CORS_ORIGINS=https://app.glisk.io
```

### Deployment Checklist

- [ ] Update `.env` with production values
- [ ] Set `POSTGRES_PASSWORD` to strong password
- [ ] Review and test migrations locally first
- [ ] Build: `docker compose build`
- [ ] Start: `docker compose up -d`
- [ ] Verify migrations: `docker logs backend-api-1 | grep "Migrations complete"`
- [ ] Verify health: `curl http://localhost:8000/health`
- [ ] Monitor logs: `docker compose logs -f backend-api`

---

## Troubleshooting

### Port 8000 already in use

```bash
# Find process
lsof -i :8000

# Kill process
kill -9 <PID>

# Or change port in .env
PORT=8001
```

### Database connection refused

```bash
# Check PostgreSQL is running
docker compose ps

# Start postgres
docker compose up -d postgres

# Wait for startup
sleep 5

# Retry
curl http://localhost:8000/health
```

### Tests fail

```bash
# Check Docker is running
docker ps

# Pull postgres image
docker pull postgres:17

# Ensure sufficient Docker resources (4GB RAM, 2 CPUs)

# Run tests
uv run pytest -v
```

### Import errors

```bash
# Ensure in backend/ directory
pwd  # Should show .../glisk/backend

# Reinstall dependencies
uv sync

# Run with uv prefix
uv run python -m glisk.app
```

---

## Next Steps

After foundation setup:

1. **Implement 003b** - Event detection (listens for mint events)
2. **Implement 003c** - Image generation (processes detected tokens)
3. **Implement 003d** - IPFS upload (uploads generated images)
4. **Implement 003e** - Reveal coordination (triggers on-chain reveals)

**Documentation**:
- [Quickstart Guide](../specs/003-003a-backend-foundation/quickstart.md) - Detailed setup
- [Data Model](../specs/003-003a-backend-foundation/data-model.md) - Schema and relationships
- [Research](../specs/003-003a-backend-foundation/research.md) - Technical decisions

---

## Resources

- **API Docs**: http://localhost:8000/docs
- **FastAPI**: https://fastapi.tiangolo.com/
- **SQLModel**: https://sqlmodel.tiangolo.com/
- **Alembic**: https://alembic.sqlalchemy.org/
- **pytest**: https://docs.pytest.org/
- **testcontainers**: https://testcontainers-python.readthedocs.io/

---

## Success Criteria (Validated)

- ✅ `docker compose up` completes in <30s (SC-001)
- ✅ `alembic upgrade head` completes in <5s (SC-002)
- ✅ `pytest` completes in <60s (SC-003) - actual: ~2.6s
- ✅ `GET /health` responds in <100ms (SC-004)
- ✅ Invalid state transitions raise exceptions (SC-006)
- ✅ Timezone tests identical across timezones (SC-007)

**Foundation is production-ready!** 🎉
