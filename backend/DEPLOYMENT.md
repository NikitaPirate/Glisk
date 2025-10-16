# Deployment Guide - Database Migrations

## Overview

Running Alembic migrations in production with multiple containers requires careful handling to avoid race conditions. This guide covers two approaches.

---

## Approach 1: Entrypoint Script (Current Default)

**How it works**: Every container runs `alembic upgrade head` on startup before starting the API.

**Pros**:
- ✅ Simple - no additional orchestration needed
- ✅ Safe - Alembic uses `alembic_version` table as a lock
- ✅ Automatic - migrations always run before app starts
- ✅ Works with rolling deployments

**Cons**:
- ⚠️ Slight startup delay (usually <1s)
- ⚠️ All containers attempt migration (only one succeeds, others wait)

**Implementation**: `backend/entrypoint.sh`

```bash
#!/bin/bash
set -e

# Wait for postgres to be ready
until pg_isready -h postgres -p 5432 -U ${POSTGRES_USER:-glisk}; do
  sleep 2
done

# Run migrations (Alembic handles locking via alembic_version table)
uv run alembic upgrade head

# Start application
exec uv run uvicorn glisk.app:app --host 0.0.0.0 --port $PORT
```

**Why this is safe**:
- Alembic acquires an exclusive lock on the `alembic_version` table
- First container to reach migration runs it
- Other containers wait for lock, then see migration is already complete
- PostgreSQL transaction isolation prevents corruption

**Best for**:
- Docker Compose deployments
- Small-scale production (1-5 containers)
- Environments without init container support

---

## Approach 2: Separate Migration Service (Better for Scale)

**How it works**: Run migrations as a separate one-time job before starting API containers.

**Pros**:
- ✅ No startup delay for API containers
- ✅ Explicit migration control
- ✅ Better for large deployments (10+ containers)
- ✅ Easier to monitor and debug migration failures

**Cons**:
- ⚠️ Requires orchestration (Docker Compose dependencies or Kubernetes init containers)
- ⚠️ More complex deployment workflow

### Docker Compose Implementation

Uncomment the `migrations` service in `docker-compose.yml`:

```yaml
services:
  postgres:
    image: postgres:17
    # ... postgres config

  migrations:
    build:
      context: ./backend
      dockerfile: Dockerfile
    depends_on:
      postgres:
        condition: service_healthy
    env_file:
      - .env
    command: ["uv", "run", "alembic", "upgrade", "head"]
    restart: "no"  # Run once, then exit

  backend-api:
    build:
      context: ./backend
      dockerfile: Dockerfile
    depends_on:
      postgres:
        condition: service_healthy
      migrations:
        condition: service_completed_successfully  # Wait for migration
    # ... api config
```

**Usage**:
```bash
# Start everything (migrations run first, then API)
docker compose up --build

# Migrations run once, API starts after they complete
```

### Kubernetes Implementation

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: glisk-migrations
spec:
  template:
    spec:
      containers:
      - name: migrations
        image: glisk-backend:latest
        command: ["uv", "run", "alembic", "upgrade", "head"]
        envFrom:
        - secretRef:
            name: glisk-secrets
      restartPolicy: OnFailure
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: glisk-backend
spec:
  template:
    spec:
      # Init container waits for migration job
      initContainers:
      - name: wait-for-migrations
        image: busybox
        command: ['sh', '-c', 'until kubectl get job glisk-migrations -o jsonpath="{.status.succeeded}" | grep 1; do sleep 5; done']
      containers:
      - name: backend
        image: glisk-backend:latest
        # ... container config
```

**Best for**:
- Kubernetes deployments
- Large-scale production (10+ containers)
- When you want explicit migration control
- CI/CD pipelines with separate migration step

---

## Approach 3: Manual Migrations (Not Recommended)

**How it works**: Manually run migrations before deploying new code.

```bash
# SSH into server or run via CI/CD
docker exec backend-api-1 uv run alembic upgrade head

# Then deploy new containers
docker compose up --build -d
```

**Why not recommended**:
- ❌ Manual step easy to forget
- ❌ No automation
- ❌ Requires manual intervention for each deployment
- ❌ Prone to human error

---

## Production Best Practices

### 1. Always Test Migrations First

```bash
# Create migration
uv run alembic revision --autogenerate -m "Add new field"

# Review generated SQL
cat alembic/versions/XXX_add_new_field.py

# Test locally
docker compose down -v
docker compose up --build
```

### 2. Backward Compatible Migrations

For zero-downtime deployments:

```python
# ✅ Good: Add nullable column first
def upgrade():
    op.add_column('tokens', sa.Column('new_field', sa.String(), nullable=True))

# Then in next migration, make NOT NULL
def upgrade():
    op.alter_column('tokens', 'new_field', nullable=False)
```

```python
# ❌ Bad: Breaking change
def upgrade():
    op.drop_column('tokens', 'old_field')  # Old code still uses this!
```

### 3. Monitor Migration Status

```bash
# Check current migration version
docker exec backend-api-1 uv run alembic current

# Check migration history
docker exec backend-api-1 uv run alembic history

# View pending migrations
docker exec backend-api-1 uv run alembic heads
```

### 4. Rollback Plan

Always test downgrade migrations:

```bash
# Downgrade one version
uv run alembic downgrade -1

# Downgrade to specific version
uv run alembic downgrade abc123

# Verify app still works
curl http://localhost:8000/health
```

### 5. Use Transaction-Safe Migrations

Alembic runs migrations in transactions by default (PostgreSQL):

```python
# This is safe - entire migration rolls back on error
def upgrade():
    op.add_column('tokens', sa.Column('new_field', sa.String()))
    op.create_index('ix_tokens_new_field', 'tokens', ['new_field'])
    # If index creation fails, column addition is rolled back
```

---

## Troubleshooting

### Issue: Migration locked

**Symptom**: Containers hang with "Waiting for migration lock..."

**Cause**: Previous migration crashed and left lock

**Solution**:
```bash
# Connect to database
docker exec -it backend-postgres-1 psql -U glisk -d glisk

# Check alembic_version table
SELECT * FROM alembic_version;

# If stuck, manually reset (DANGEROUS - only if you're sure)
DELETE FROM alembic_version;
INSERT INTO alembic_version VALUES ('current_version_id');
```

### Issue: Migration fails partway through

**Symptom**: Migration error, some changes applied

**Cause**: Non-transactional operation (e.g., CREATE INDEX CONCURRENTLY)

**Solution**:
```bash
# Fix the issue manually or via new migration
uv run alembic revision -m "Fix failed migration"

# Manually mark as upgraded (if changes already applied)
uv run alembic stamp head
```

### Issue: Multiple containers fighting over lock

**Symptom**: Slow startup, high database CPU

**Cause**: Too many containers trying to migrate simultaneously

**Solution**: Use Approach 2 (separate migration service)

---

## Performance Considerations

### Migration Timing

Typical migration times:
- Adding column: 1-5s
- Creating index: 5-30s (depending on table size)
- Complex data migration: 1-10min

For large tables, use:
```python
# Non-blocking index creation
op.create_index('ix_tokens_field', 'tokens', ['field'], postgresql_concurrently=True)

# Requires: context.execute("SET lock_timeout = '2s'")
```

### Scale Recommendations

| Containers | Approach | Reason |
|------------|----------|--------|
| 1-3 | Entrypoint | Simple, negligible overhead |
| 4-10 | Entrypoint | Safe, Alembic handles locking well |
| 10+ | Separate Service | Reduces startup contention |
| Kubernetes | Separate Job | Best practice for orchestration |

---

## Current Configuration

**GLISK uses Approach 1 (Entrypoint Script) by default**

This is the best balance of simplicity and safety for most deployments. Switch to Approach 2 if:
- You're deploying 10+ containers
- You want explicit migration control
- You're using Kubernetes
- Migration time becomes a bottleneck

To switch to Approach 2:
1. Uncomment `migrations` service in `docker-compose.yml`
2. Comment out migration logic in `entrypoint.sh`
3. Rebuild: `docker compose up --build`
