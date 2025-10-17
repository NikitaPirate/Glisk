# Internal Service Contracts: Image Generation Worker

**Feature**: 003-003c-image-generation
**Date**: 2025-10-17
**Type**: Internal service interfaces (no external HTTP API)

## Overview

This feature is an internal background worker that processes tokens from the database. It does not expose external HTTP endpoints. This document defines the internal service contracts between components.

## Service Interfaces

### ImageGenerationService

**Purpose**: Orchestrates image generation for a single token

**File**: `backend/src/glisk/services/image_generation/replicate_client.py`

#### Method: `generate_image`

**Signature**:
```python
async def generate_image(prompt: str, model_version: str | None = None) -> str:
    """
    Generate an image using Replicate API.

    Args:
        prompt: Text prompt for image generation (validated, ≤1000 chars)
        model_version: Optional Replicate model identifier
                      (defaults to REPLICATE_MODEL_VERSION env var)

    Returns:
        str: URL of generated image (Replicate CDN link)

    Raises:
        TransientError: Network timeout, rate limit, service unavailable
        ContentPolicyError: Content filter violation
        PermanentError: Invalid API token, malformed prompt
    """
```

**Behavior**:
- Calls Replicate API using official Python SDK (sync wrapped in asyncio)
- Validates prompt length before API call
- Classifies exceptions into error categories
- Returns first URL from Replicate's output array

**Error Contract**:
```python
class ReplicateError(Exception):
    """Base exception for Replicate API errors."""
    retryable: bool = False

class TransientError(ReplicateError):
    """Temporary failure, retry with same prompt."""
    retryable = True

class ContentPolicyError(ReplicateError):
    """Content filter violation, retry with fallback prompt."""
    retryable = True

class PermanentError(ReplicateError):
    """Permanent failure, do not retry."""
    retryable = False
```

---

### PromptValidator

**Purpose**: Validate prompt text before generation

**File**: `backend/src/glisk/services/image_generation/prompt_validator.py`

#### Method: `validate_prompt`

**Signature**:
```python
def validate_prompt(prompt: str) -> None:
    """
    Validate prompt text for image generation.

    Args:
        prompt: Text prompt from author

    Raises:
        ValueError: If prompt is empty or exceeds 1000 characters

    Validation Rules:
        - Must be non-empty after stripping whitespace
        - Maximum length: 1000 characters
        - No sanitization (trust upstream access control)
    """
```

**Examples**:
```python
# Valid prompts
validate_prompt("A sunset over mountains")  # OK
validate_prompt("  A sunset  ")             # OK (strips whitespace)

# Invalid prompts
validate_prompt("")                         # ValueError: Prompt is empty
validate_prompt("   ")                      # ValueError: Prompt is empty
validate_prompt("A" * 1001)                 # ValueError: Prompt exceeds 1000 character limit
```

---

### TokenRepository (Extended)

**Purpose**: Database operations for token lifecycle

**File**: `backend/src/glisk/repositories/token_repository.py`

#### Method: `find_for_generation`

**Signature**:
```python
async def find_for_generation(self, limit: int = 10) -> List[Token]:
    """
    Find tokens ready for image generation with row-level locking.

    Args:
        limit: Maximum number of tokens to return (default 10)

    Returns:
        List[Token]: Locked tokens ready for generation (status='detected')

    Locking Behavior:
        - Uses FOR UPDATE SKIP LOCKED (PostgreSQL-specific)
        - Locked rows are invisible to other transactions
        - Lock released on commit/rollback
        - FIFO ordering by detected_at

    Query:
        SELECT * FROM tokens_s0
        WHERE status = 'detected'
          AND generation_attempts < 3
        ORDER BY detected_at ASC
        LIMIT {limit}
        FOR UPDATE SKIP LOCKED
    """
```

#### Method: `update_image_url`

**Signature**:
```python
async def update_image_url(self, token: Token, image_url: str) -> None:
    """
    Mark token as successfully generated with image URL.

    Args:
        token: Token instance (must be locked by current transaction)
        image_url: Replicate CDN URL

    Side Effects:
        - Updates token.image_url
        - Sets token.status = 'uploading'
        - Commits transaction
        - Refreshes token instance from database
    """
```

#### Method: `mark_failed`

**Signature**:
```python
async def mark_failed(self, token: Token, error_message: str) -> None:
    """
    Mark token as permanently failed.

    Args:
        token: Token instance (must be locked by current transaction)
        error_message: Error description (truncated to 1000 chars)

    Side Effects:
        - Sets token.status = 'failed'
        - Updates token.generation_error (truncated)
        - Commits transaction
        - Refreshes token instance from database
    """
```

#### Method: `increment_attempts`

**Signature**:
```python
async def increment_attempts(self, token: Token, error_message: str) -> None:
    """
    Increment retry counter for transient failure.

    Args:
        token: Token instance (must be locked by current transaction)
        error_message: Error description (truncated to 1000 chars)

    Side Effects:
        - Increments token.generation_attempts
        - Sets token.status = 'detected' (ready for retry)
        - Updates token.generation_error
        - Commits transaction
        - Refreshes token instance from database
    """
```

---

### ImageGenerationWorker

**Purpose**: Background polling loop for image generation

**File**: `backend/src/glisk/workers/image_generation_worker.py`

#### Method: `run_image_generation_worker`

**Signature**:
```python
async def run_image_generation_worker() -> None:
    """
    Main worker loop (runs in background asyncio task).

    Behavior:
        1. Poll database for tokens with status='detected'
        2. Process up to WORKER_BATCH_SIZE tokens concurrently
        3. Sleep for POLL_INTERVAL_SECONDS
        4. Repeat until CancelledError

    Configuration:
        - POLL_INTERVAL_SECONDS: Polling interval (default 1)
        - WORKER_BATCH_SIZE: Max concurrent tokens (default 10)

    Lifecycle:
        - Started by FastAPI lifespan context manager
        - Graceful shutdown on asyncio.CancelledError
        - Auto-recovery on startup (reset orphaned tokens)

    Error Handling:
        - Individual token failures don't stop the batch
        - Worker errors logged and retried after 5s backoff
    """
```

#### Method: `process_batch`

**Signature**:
```python
async def process_batch() -> None:
    """
    Process one batch of tokens concurrently.

    Steps:
        1. Lock tokens via find_for_generation()
        2. Process each token in parallel (asyncio.gather)
        3. Return (no explicit commit, handled by individual token processing)

    Concurrency:
        - asyncio.gather with return_exceptions=True
        - Individual token errors don't fail entire batch
    """
```

#### Method: `process_single_token`

**Signature**:
```python
async def process_single_token(token: Token) -> None:
    """
    Process a single token through generation workflow.

    Args:
        token: Token instance (locked by FOR UPDATE SKIP LOCKED)

    Steps:
        1. Update status: detected → generating
        2. Validate prompt text
        3. Call Replicate API
        4. Handle success: update_image_url()
        5. Handle failure: classify error, retry or mark failed

    Error Handling:
        - TransientError: increment_attempts(), status → detected
        - ContentPolicyError: retry with fallback prompt
        - PermanentError: mark_failed()
        - Max retries (3): mark_failed()
    """
```

#### Method: `recover_orphaned_tokens`

**Signature**:
```python
async def recover_orphaned_tokens(session: AsyncSession) -> None:
    """
    Reset tokens stuck in 'generating' status (called once on startup).

    Query:
        UPDATE tokens_s0
        SET status = 'detected'
        WHERE status = 'generating'
          AND generation_attempts < 3

    Rationale:
        - Worker crashes leave tokens in 'generating' status
        - Only reset if retry budget remains
        - Tokens at max attempts stay 'failed'
    """
```

---

## Configuration Contract

**File**: `backend/src/glisk/core/config.py` (extended)

**New Environment Variables**:

| Variable | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `REPLICATE_API_TOKEN` | `str` | Yes | N/A | Replicate API authentication token |
| `REPLICATE_MODEL_VERSION` | `str` | No | `"black-forest-labs/flux-schnell"` | Model identifier for image generation |
| `FALLBACK_CENSORED_PROMPT` | `str` | Yes | N/A | Fallback prompt for content policy violations |
| `POLL_INTERVAL_SECONDS` | `int` | No | `1` | Worker polling interval |
| `WORKER_BATCH_SIZE` | `int` | No | `10` | Max concurrent tokens per batch |

**Example `.env`**:
```bash
# Replicate Configuration (003c)
REPLICATE_API_TOKEN=r8_abc123xyz789
REPLICATE_MODEL_VERSION=black-forest-labs/flux-schnell
FALLBACK_CENSORED_PROMPT="Cute kittens and flowers in a peaceful garden, with text overlay saying 'Content moderated by AI service'"
POLL_INTERVAL_SECONDS=1
WORKER_BATCH_SIZE=10
```

---

## Logging Contract

**Structured Log Events**:

All log events use JSON format with consistent event naming: `entity.action.outcome`

### Worker Lifecycle Events

```python
# Worker startup
logger.info("worker.started", poll_interval=1, batch_size=10)

# Worker shutdown
logger.info("worker.stopped", reason="graceful_shutdown")

# Worker error (non-fatal)
logger.error("worker.error", exc_info=exc, backoff_seconds=5)

# Startup recovery
logger.info("worker.recovery", orphaned_tokens_reset=5)
```

### Token Processing Events

```python
# Generation start
logger.info(
    "token.generation.started",
    token_id=123,
    attempt_number=1,
    prompt_length=42
)

# Generation success
logger.info(
    "token.generation.succeeded",
    token_id=123,
    image_url="https://replicate.delivery/...",
    duration_seconds=45.2,
    attempt_number=1
)

# Generation failure (transient)
logger.warning(
    "token.generation.retry",
    token_id=123,
    error_type="TransientError",
    error_message="Network timeout",
    attempt_number=1,
    max_attempts=3
)

# Generation failure (permanent)
logger.error(
    "token.generation.failed",
    token_id=123,
    error_type="PermanentError",
    error_message="Invalid API token",
    attempt_number=1
)

# Retry exhausted
logger.error(
    "token.generation.exhausted",
    token_id=123,
    attempts=3,
    last_error="Rate limit exceeded"
)
```

### Censorship Events

```python
# Content policy violation
logger.warning(
    "token.censored",
    token_id=789,
    original_prompt="[redacted]",
    fallback_prompt="Cute kittens and flowers...",
    reason="content_policy_violation"
)
```

---

## Testing Contracts

### Unit Test Interfaces

**File**: `backend/tests/services/image_generation/test_replicate_client.py`

Tests for `ImageGenerationService`:
- `test_generate_image_success()` - Happy path with mocked Replicate API
- `test_generate_image_timeout()` - Raises TransientError
- `test_generate_image_rate_limit()` - Raises TransientError
- `test_generate_image_content_policy()` - Raises ContentPolicyError
- `test_generate_image_invalid_token()` - Raises PermanentError

**File**: `backend/tests/services/image_generation/test_prompt_validator.py`

Tests for `PromptValidator`:
- `test_validate_prompt_valid()` - Accepts valid prompts
- `test_validate_prompt_empty()` - Raises ValueError
- `test_validate_prompt_too_long()` - Raises ValueError (1001 chars)

**File**: `backend/tests/workers/test_image_generation_worker.py`

Integration tests with testcontainers (real PostgreSQL):
- `test_process_batch_success()` - Locks tokens, generates images
- `test_process_batch_concurrent()` - Multiple workers don't duplicate processing
- `test_process_single_token_retry()` - Transient error increments attempts
- `test_process_single_token_exhausted()` - Max retries marks failed
- `test_recover_orphaned_tokens()` - Startup recovery resets generating status

---

## Summary

**External APIs**: None (internal worker only)

**Internal Contracts**:
- `ImageGenerationService.generate_image()` - Replicate API integration
- `PromptValidator.validate_prompt()` - Input validation
- `TokenRepository` extensions - Database operations
- `ImageGenerationWorker` - Background processing loop

**Configuration**: 5 environment variables (2 required, 3 optional)

**Logging**: Structured JSON events with consistent naming

**Testing**: Unit tests (mocked Replicate) + integration tests (testcontainers)
