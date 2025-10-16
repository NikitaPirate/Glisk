# Quickstart Guide: Backend Foundation

**Feature**: 003a Backend Foundation
**Target Audience**: Developers implementing features 003b-003e
**Estimated Setup Time**: 15 minutes

## Prerequisites

Ensure these are installed on your system:

- **Python 3.14** - Standard GIL-enabled version
- **Docker** - For PostgreSQL and containerized backend
- **Docker Compose** - For orchestrating services
- **uv** - Python package manager (install: `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- **Git** - For cloning repository

**Verify Installation**:
```bash
python3 --version  # Should show 3.14.x
docker --version
docker compose version
uv --version
```

---

## Quick Start (5 minutes)

Get the backend running with default configuration:

```bash
# 1. Navigate to backend directory
cd backend

# 2. Copy environment template
cp .env.example .env

# 3. Start services (PostgreSQL + backend API)
docker compose up --build

# 4. Verify health check (in new terminal)
curl http://localhost:8000/health
# Expected: {"status":"healthy"}
```

**That's it!** Backend is running. Continue reading for detailed setup and development workflow.

---

## Detailed Setup

### 1. Environment Configuration

The `.env` file contains all configuration. Review and customize if needed:

```bash
# Edit backend/.env
nano .env  # or your preferred editor
```

**Key Variables**:
```env
# Database
DATABASE_URL=postgresql+psycopg://glisk:glisk@postgres:5432/glisk
DB_POOL_SIZE=200  # Connection pool size

# Application
APP_ENV=development  # development | production
LOG_LEVEL=INFO  # DEBUG | INFO | WARNING | ERROR
CORS_ORIGINS=http://localhost:3000  # Comma-separated

# Server
HOST=0.0.0.0
PORT=8000
```

**Defaults**: Suitable for local development. Only change if you have port conflicts or custom database setup.

---

### 2. Database Setup

#### Option A: Using Docker Compose (Recommended)

Docker Compose automatically starts PostgreSQL with correct configuration:

```bash
docker compose up -d postgres  # Start database only
```

**What it does**:
- Starts PostgreSQL 14 container
- Creates `glisk` database
- Configures user/password from `.env`
- Exposes port 5432 to host (for direct access if needed)

#### Option B: Local PostgreSQL

If you prefer local PostgreSQL installation:

```bash
# 1. Create database
createdb glisk

# 2. Update DATABASE_URL in .env
DATABASE_URL=postgresql+psycopg://YOUR_USER:YOUR_PASSWORD@localhost:5432/glisk

# 3. Run migrations (see next section)
```

---

### 3. Run Database Migrations

Apply schema migrations to create tables:

```bash
# Inside backend/ directory
uv run alembic upgrade head
```

**Expected Output**:
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 001, Initial schema
```

**Verify Migration**:
```bash
# Connect to database
docker exec -it backend-postgres-1 psql -U glisk -d glisk

# List tables
\dt

# Expected tables:
#  authors
#  tokens_s0
#  mint_events
#  image_generation_jobs
#  ipfs_upload_records
#  reveal_transactions
#  system_state
#  alembic_version

# Exit psql
\q
```

---

### 4. Start Backend API

#### Development Mode (with hot reload)

```bash
# Inside backend/ directory
uv run uvicorn glisk.app:app --reload --host 0.0.0.0 --port 8000
```

**Features**:
- Hot reload on code changes
- Detailed error messages
- Swagger UI at `http://localhost:8000/docs`

#### Production Mode (via Docker)

```bash
docker compose up --build backend-api
```

**Features**:
- Containerized deployment
- Managed by Docker Compose
- Automatic restart on failure

---

### 5. Verify Setup

Run these checks to ensure everything is working:

**Health Check**:
```bash
curl http://localhost:8000/health
# Expected: {"status":"healthy"}
```

**API Documentation**:
Open browser to `http://localhost:8000/docs` - should see Swagger UI

**Database Connection**:
```bash
docker exec -it backend-postgres-1 psql -U glisk -d glisk -c "SELECT COUNT(*) FROM authors;"
# Expected: count | 0
```

---

## Development Workflow

### Running Tests

```bash
# Inside backend/ directory

# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=glisk --cov-report=html

# Run specific test file
uv run pytest tests/test_repositories.py

# Run tests matching pattern
uv run pytest -k "test_concurrent_workers"
```

**Test Output** (expected):
```
========================= test session starts =========================
collected 15 items

tests/test_repositories.py ........                              [100%]

========================= 15 passed in 12.34s =========================
```

**Note**: First test run takes ~60s (testcontainer startup). Subsequent runs are faster.

---

### Code Formatting

```bash
# Format code with black
uv run black glisk/ tests/

# Check formatting without changes
uv run black --check glisk/ tests/

# Sort imports
uv run isort glisk/ tests/
```

---

### Type Checking

```bash
# Run mypy type checker
uv run mypy glisk/
```

---

### Database Migrations (Creating New)

When you modify SQLModel entities:

```bash
# Auto-generate migration
uv run alembic revision --autogenerate -m "Add new field to tokens"

# Review generated migration in alembic/versions/
# IMPORTANT: Verify SQL is correct (autogenerate may miss custom types)

# Apply migration
uv run alembic upgrade head
```

---

### Interactive Python Shell

Access backend objects in Python REPL:

```bash
uv run python

# Inside Python shell:
from glisk.core.database import setup_db_session
from glisk.uow import create_uow_factory
from glisk.core.config import Settings
import asyncio

settings = Settings()
session_factory = setup_db_session(settings.database_url)
uow_factory = create_uow_factory(session_factory)

# Use async wrapper
async def explore():
    async with uow_factory() as uow:
        authors = await uow.authors.list_all()
        print(f"Found {len(authors)} authors")

asyncio.run(explore())
```

---

### Debugging

#### Enable Debug Logging

Edit `.env`:
```env
LOG_LEVEL=DEBUG
```

Restart backend to see detailed logs:
```bash
docker compose restart backend-api
```

#### Attach Debugger (VS Code)

Add to `.vscode/launch.json`:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "FastAPI Backend",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": ["glisk.app:app", "--reload"],
      "cwd": "${workspaceFolder}/backend",
      "env": {
        "PYTHONPATH": "${workspaceFolder}/backend/src"
      }
    }
  ]
}
```

Set breakpoints and press F5.

---

## Common Tasks

### Reset Database

**Warning**: Destroys all data!

```bash
# Stop services
docker compose down

# Remove database volume
docker volume rm backend_postgres_data

# Restart and re-run migrations
docker compose up -d postgres
uv run alembic upgrade head
```

---

### Inspect Database

```bash
# Connect to PostgreSQL
docker exec -it backend-postgres-1 psql -U glisk -d glisk

# Useful commands:
\dt                          # List tables
\d tokens_s0                 # Describe table
SELECT * FROM tokens_s0;     # Query data
\q                           # Exit
```

---

### View Logs

```bash
# All services
docker compose logs -f

# Backend API only
docker compose logs -f backend-api

# PostgreSQL only
docker compose logs -f postgres

# Last 100 lines
docker compose logs --tail=100 backend-api
```

---

### Stop Services

```bash
# Stop all services (keeps data)
docker compose down

# Stop and remove volumes (DELETES DATA)
docker compose down -v
```

---

## Troubleshooting

### Issue: Port 8000 already in use

**Solution**:
```bash
# Find process using port
lsof -i :8000

# Kill process
kill -9 <PID>

# Or change port in .env
PORT=8001
```

---

### Issue: Database connection refused

**Symptoms**: Health check returns 503, logs show "connection refused"

**Solution**:
```bash
# Check if PostgreSQL is running
docker compose ps

# If not running, start it
docker compose up -d postgres

# Wait 5 seconds for startup
sleep 5

# Retry health check
curl http://localhost:8000/health
```

---

### Issue: Migrations fail with "relation already exists"

**Symptoms**: `alembic upgrade head` fails with "relation already exists"

**Solution**:
```bash
# Check current migration version
uv run alembic current

# If out of sync, stamp database to current code state
uv run alembic stamp head

# Or reset database (destroys data)
docker compose down -v
docker compose up -d postgres
uv run alembic upgrade head
```

---

### Issue: Tests fail with "testcontainer timeout"

**Symptoms**: pytest hangs or fails with "Container startup failed"

**Solution**:
```bash
# Check Docker is running
docker ps

# Ensure Docker has sufficient resources (Settings > Resources)
# Recommended: 4GB RAM, 2 CPUs

# Pull PostgreSQL image manually
docker pull postgres:14

# Retry tests
uv run pytest
```

---

### Issue: Import errors "No module named glisk"

**Symptoms**: `ModuleNotFoundError: No module named 'glisk'`

**Solution**:
```bash
# Ensure you're in backend/ directory
pwd  # Should show .../glisk/backend

# Reinstall dependencies
uv sync

# Run with uv prefix
uv run python -m glisk.app
```

---

## Next Steps

After completing quickstart:

1. **Read data-model.md** - Understand database schema and entities
2. **Read repository-interfaces.md** - Learn repository method contracts
3. **Read http-api.md** - Understand API endpoints
4. **Explore tests/** - See examples of testing patterns
5. **Start implementing 003b** - Event detection feature builds on this foundation

---

## Architecture Overview

Quick reference for understanding the codebase:

```
backend/src/glisk/
├── core/
│   ├── config.py           # Environment configuration
│   ├── database.py         # Session factory setup
│   ├── timezone.py         # UTC enforcement
│   └── dependencies.py     # FastAPI dependency injection
│
├── models/                 # SQLModel entities
│   ├── author.py
│   ├── token.py           # + state transition methods
│   └── ...
│
├── repositories/           # Data access layer
│   ├── author.py          # Direct repositories (no base class)
│   ├── token.py           # + FOR UPDATE SKIP LOCKED queries
│   └── ...
│
├── uow.py                 # Unit of Work pattern
└── app.py                 # FastAPI application factory
```

**Key Patterns**:
- **Dependency Injection**: FastAPI `Depends()` injects UoW into routes
- **Unit of Work**: Transaction boundary management with automatic commit/rollback
- **Repository Pattern**: Data access abstraction over SQLModel
- **State Transitions**: Domain methods on Token model validate transitions

---

## Resources

- **API Documentation**: `http://localhost:8000/docs` (Swagger UI)
- **Research Document**: `specs/003-003a-backend-foundation/research.md`
- **Data Model**: `specs/003-003a-backend-foundation/data-model.md`
- **Repository Contracts**: `specs/003-003a-backend-foundation/contracts/repository-interfaces.md`
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **SQLModel Docs**: https://sqlmodel.tiangolo.com/
- **Alembic Docs**: https://alembic.sqlalchemy.org/

---

## Support

If you encounter issues not covered in troubleshooting:

1. Check Docker logs: `docker compose logs -f`
2. Check application logs: Look for ERROR level messages
3. Verify environment: `.env` file has correct values
4. Try clean start: `docker compose down -v && docker compose up --build`

For feature-specific questions, refer to the relevant spec document (003b-003e).
