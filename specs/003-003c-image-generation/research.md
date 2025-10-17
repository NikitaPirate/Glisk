# Research Notes: Image Generation Worker

**Feature**: 003-003c-image-generation
**Date**: 2025-10-17
**Phase**: 0 - Research & Technology Decisions

## Overview

This document consolidates research findings and technology decisions for implementing the image generation worker. All "NEEDS CLARIFICATION" items from the Technical Context have been resolved through architectural analysis and best practices research.

## Technology Decisions

### 1. Replicate Python SDK Integration

**Decision**: Use official `replicate` Python SDK with synchronous API calls wrapped in async context

**Rationale**:
- Official SDK provides stable API with proper error handling
- Synchronous SDK calls are acceptable because:
  - Replicate API has ~30-60s generation latency (network I/O bound)
  - Worker processes tokens concurrently using asyncio.gather()
  - Each token's generation happens in its own task context
- No need for custom HTTP client wrapper

**Alternatives considered**:
- Custom async HTTP client using httpx: Rejected due to maintenance burden and SDK stability
- Blocking synchronous worker: Rejected due to poor concurrency (can't process 10 tokens in parallel)

**Implementation approach**:
```python
import replicate
from asyncio import to_thread

async def generate_image(prompt: str) -> str:
    """Generate image using Replicate API (sync SDK wrapped in async)."""
    # Replicate SDK is sync, so run in thread pool to avoid blocking event loop
    output = await to_thread(
        replicate.run,
        "black-forest-labs/flux-schnell",
        input={"prompt": prompt}
    )
    return output[0]  # First URL from output list
```

**Configuration**:
- `REPLICATE_API_TOKEN` (required): API authentication token
- `REPLICATE_MODEL_VERSION` (optional): Model identifier, defaults to "black-forest-labs/flux-schnell"
- `FALLBACK_CENSORED_PROMPT` (required): Fallback prompt for content policy violations

---

### 2. Background Worker Lifecycle Management

**Decision**: Use FastAPI lifespan context manager with asyncio task for polling loop

**Rationale**:
- FastAPI provides `@asynccontextmanager` lifespan for clean startup/shutdown
- Allows graceful shutdown: cancel polling task, wait for in-flight generations
- No need for separate process manager (supervisor, systemd) for MVP
- Worker runs in same process as API server (shared database connection pool)

**Alternatives considered**:
- Separate systemd service: Rejected for MVP complexity (two deployment units)
- Celery/RQ message queue: Rejected as over-engineered (polling is simpler for low volume)
- Threading instead of asyncio: Rejected due to poor concurrency and GIL contention

**Implementation approach**:
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
import asyncio

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Launch worker task
    task = asyncio.create_task(run_image_generation_worker())
    yield
    # Shutdown: Cancel task and wait for cleanup
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

app = FastAPI(lifespan=lifespan)
```

**Worker loop pattern**:
```python
async def run_image_generation_worker():
    while True:
        try:
            await process_batch()
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
        except asyncio.CancelledError:
            logger.info("Worker shutdown requested")
            raise
        except Exception as e:
            logger.error("Worker error", exc_info=e)
            await asyncio.sleep(5)  # Back off on errors
```

---

### 3. Database Schema Changes (Alembic Migration)

**Decision**: Add 3 nullable columns to existing `tokens_s0` table via Alembic migration

**Schema changes**:
```sql
ALTER TABLE tokens_s0 ADD COLUMN image_url TEXT;
ALTER TABLE tokens_s0 ADD COLUMN generation_attempts INTEGER DEFAULT 0 NOT NULL;
ALTER TABLE tokens_s0 ADD COLUMN generation_error TEXT;
```

**Rationale**:
- Extend existing table rather than create new table (avoid JOIN overhead)
- Nullable `image_url` and `generation_error` (only populated after generation attempt)
- Default 0 for `generation_attempts` (all existing tokens start at 0)
- No index needed (queries filter on `status` which already has index from 003a)

**Alembic workflow** (per constitution):
1. Update SQLModel: Add fields to `Token` model in `backend/src/glisk/db/models.py`
2. Generate migration: `alembic revision --autogenerate -m "add_image_generation_fields"`
3. Manual verification: Check generated SQL for enum handling, defaults, nullability
4. Test idempotency: `alembic upgrade head && alembic downgrade -1 && alembic upgrade head`

**Alternatives considered**:
- Separate `token_images` table: Rejected as over-normalized (1:1 relationship)
- JSONB column for generation metadata: Rejected for query complexity and schema clarity

---

### 4. Retry Logic and Error Classification

**Decision**: Three-tier error classification with retry strategy per tier

**Error categories**:

| Category | Examples | Retry Strategy | Status Transition |
|----------|----------|----------------|-------------------|
| **Transient** | Network timeout, rate limit 429, service unavailable 503 | Retry with exponential backoff (1s, 2s, 4s) | `generating` → `detected` (increment attempts) |
| **Content Policy** | Content filter rejection, safety system block | Retry once with fallback prompt | `generating` → `detected` (use fallback) |
| **Permanent** | Invalid API token, malformed prompt, 401 auth error | No retry | `generating` → `failed` (store error) |

**Implementation approach**:
```python
class ReplicateError(Exception):
    """Base class for categorized errors."""
    retryable: bool = False

class TransientError(ReplicateError):
    retryable = True

class ContentPolicyError(ReplicateError):
    retryable = True  # Retry with fallback

class PermanentError(ReplicateError):
    retryable = False

def classify_error(exception: Exception) -> ReplicateError:
    """Classify exception into error category."""
    if isinstance(exception, httpx.TimeoutException):
        return TransientError("Network timeout")
    elif hasattr(exception, 'status_code'):
        if exception.status_code == 429:
            return TransientError("Rate limit exceeded")
        elif exception.status_code == 401:
            return PermanentError("Invalid API token")
        elif "content policy" in str(exception).lower():
            return ContentPolicyError("Content filter violation")
    return PermanentError(str(exception))
```

**Rationale**:
- Explicit classification prevents infinite retry loops
- Content policy errors get special handling (fallback prompt)
- Exponential backoff prevents thundering herd on rate limits
- Max 3 attempts keeps retry budget bounded

**Alternatives considered**:
- Single retry strategy for all errors: Rejected due to permanent error waste (401 will never succeed)
- Circuit breaker pattern: Rejected as over-engineered per constitution (rare multi-hour outages)

---

### 5. Concurrent Processing with Database Locking

**Decision**: Use PostgreSQL `FOR UPDATE SKIP LOCKED` for lock-free token selection

**Query pattern**:
```sql
SELECT * FROM tokens_s0
WHERE status = 'detected'
  AND generation_attempts < 3
ORDER BY detected_at ASC
LIMIT 10
FOR UPDATE SKIP LOCKED;
```

**Rationale**:
- `FOR UPDATE` locks selected rows, preventing duplicate processing by concurrent workers
- `SKIP LOCKED` skips already-locked rows (no blocking, immediate return)
- `LIMIT 10` implements batch size (configurable via `WORKER_BATCH_SIZE`)
- `ORDER BY detected_at ASC` ensures FIFO processing (oldest tokens first)

**Concurrency model**:
```python
async def process_batch():
    """Process up to BATCH_SIZE tokens concurrently."""
    tokens = await token_repo.find_for_generation(limit=WORKER_BATCH_SIZE)
    if not tokens:
        return  # No work available

    # Process tokens concurrently (asyncio.gather)
    await asyncio.gather(
        *[process_single_token(token) for token in tokens],
        return_exceptions=True  # Don't fail entire batch on single error
    )
```

**Alternatives considered**:
- Redis-based distributed lock: Rejected as over-engineered (adds dependency for MVP)
- Database advisory locks: Rejected due to manual lock management complexity
- Optimistic locking (version field): Rejected due to retry overhead on conflicts

---

### 6. Startup Recovery for Orphaned Tokens

**Decision**: Auto-recover tokens stuck in 'generating' status on worker startup

**Recovery query** (runs once on startup):
```sql
UPDATE tokens_s0
SET status = 'detected'
WHERE status = 'generating'
  AND generation_attempts < 3;
```

**Rationale**:
- Worker crashes/restarts leave tokens in 'generating' status (orphaned)
- Recovery respects retry budget: only reset if attempts < max_retries
- Tokens at max attempts remain 'failed' (require manual operator intervention)
- Simple and predictable behavior (no complex crash detection)

**Implementation approach**:
```python
async def recover_orphaned_tokens(db: AsyncSession):
    """Reset tokens stuck in 'generating' status on startup."""
    result = await db.execute(
        update(Token)
        .where(Token.status == "generating", Token.generation_attempts < 3)
        .values(status="detected")
    )
    await db.commit()
    logger.info("Recovered orphaned tokens", count=result.rowcount)
```

**Alternatives considered**:
- Reset all 'generating' tokens unconditionally: Rejected as it ignores retry budget
- Heartbeat mechanism: Rejected as over-engineered (adds polling overhead)
- No recovery (manual operator intervention): Rejected as unacceptable UX for common event

---

### 7. Prompt Validation and Sanitization

**Decision**: Length validation (≤1000 characters) + non-empty check, no content sanitization

**Validation rules**:
```python
def validate_prompt(prompt: str) -> None:
    """Validate prompt text before generation."""
    if not prompt or not prompt.strip():
        raise ValueError("Prompt is empty")
    if len(prompt) > 1000:
        raise ValueError(f"Prompt exceeds 1000 character limit (got {len(prompt)})")
```

**Rationale**:
- Length validation prevents Replicate API errors (service limit is ~1000 chars)
- No SQL injection risk (using parameterized queries via SQLModel)
- No XSS risk (prompts never rendered in HTML without escaping)
- Trust upstream: Smart contract controls who can mint (access control at source)
- Content policy handled by Replicate's service (not our responsibility)

**Alternatives considered**:
- HTML sanitization: Rejected as unnecessary (prompts not rendered in HTML)
- Profanity filtering: Rejected as out of scope (Replicate handles content policy)
- Unicode normalization: Rejected as over-engineered (no reported issues with Unicode)

---

### 8. Structured Logging Strategy

**Decision**: Use structlog with JSON formatting for all worker events

**Log events to track**:
- Worker lifecycle: `worker.started`, `worker.stopped`, `worker.error`
- Token processing: `token.generation.started`, `token.generation.succeeded`, `token.generation.failed`
- Retry events: `token.retry.transient`, `token.retry.content_policy`, `token.retry.exhausted`
- Censorship events: `token.censored` (audit trail for content policy violations)

**Example structured log**:
```python
logger.info(
    "token.generation.succeeded",
    token_id=token.token_id,
    image_url=image_url,
    duration_seconds=duration,
    attempt_number=token.generation_attempts + 1
)
```

**Rationale**:
- Structured logs enable metric extraction (success rate, latency percentiles)
- JSON format supports log aggregation tools (ELK, Datadog, CloudWatch)
- Consistent event naming (`entity.action.outcome`) aids searchability
- Audit trail for content policy violations (regulatory compliance)

**Alternatives considered**:
- Plain text logs: Rejected due to poor query/aggregation support
- Separate metrics endpoint: Deferred to production deployment (logs sufficient for MVP)

---

## Resolved Unknowns

All "NEEDS CLARIFICATION" items from Technical Context have been resolved:

1. ✅ **Replicate Integration**: Official Python SDK with sync-to-async wrapper
2. ✅ **Worker Lifecycle**: FastAPI lifespan context manager
3. ✅ **Database Changes**: 3 new columns via Alembic migration
4. ✅ **Retry Logic**: Three-tier error classification with categorized retry strategies
5. ✅ **Concurrency**: FOR UPDATE SKIP LOCKED with asyncio.gather()
6. ✅ **Startup Recovery**: Auto-reset orphaned tokens respecting retry budget
7. ✅ **Prompt Validation**: Length check + non-empty, no sanitization
8. ✅ **Logging**: Structlog with JSON formatting for all events

## Next Steps

Proceed to **Phase 1: Design & Contracts**:
- Generate `data-model.md` with entity definitions and state transitions
- Generate API contracts (none needed—internal worker, no external API)
- Generate `quickstart.md` with setup and testing instructions
- Update `CLAUDE.md` with Replicate SDK technology addition
