# Quickstart Guide: Image Generation Worker

**Feature**: 003-003c-image-generation
**Date**: 2025-10-17
**Prerequisites**: 003a (backend foundation), 003b (event detection)

## Overview

This guide walks through setting up, testing, and operating the image generation worker. The worker automatically generates AI images for detected NFT mints using Replicate's API.

## Prerequisites

### Required Services

1. **PostgreSQL** (from 003a)
   - Running on localhost:5432 or via Docker
   - Database initialized with 003a/003b schema

2. **Replicate Account**
   - Sign up at https://replicate.com
   - Generate API token: https://replicate.com/account/api-tokens
   - Note: Free tier includes limited credits (~$5-10 worth)

### Existing Infrastructure

This feature builds on:
- **003a**: Database schema (`tokens_s0`, `authors` tables)
- **003b**: Event detection (populates tokens with status='detected')

## Setup

### 1. Install Dependencies

```bash
cd backend

# Add Replicate Python SDK
uv add replicate

# Verify installation
uv run python -c "import replicate; print(replicate.__version__)"
```

Expected output: `0.x.x` (current SDK version)

---

### 2. Configure Environment

Add Replicate configuration to `backend/.env`:

```bash
# Replicate Configuration (003c)
REPLICATE_API_TOKEN=r8_YourApiTokenHere123456789

# Optional: Model selection (defaults shown)
REPLICATE_MODEL_VERSION=black-forest-labs/flux-schnell
FALLBACK_CENSORED_PROMPT="Cute kittens and flowers in a peaceful garden, with text overlay saying 'Content moderated by AI service'"

# Optional: Worker tuning (defaults shown)
POLL_INTERVAL_SECONDS=1
WORKER_BATCH_SIZE=10
```

**Configuration Notes**:
- `REPLICATE_API_TOKEN`: Required. Get from https://replicate.com/account/api-tokens
- `REPLICATE_MODEL_VERSION`: Optional. `flux-schnell` is fast (~10-15s), `flux-pro` is higher quality (~30-60s)
- `FALLBACK_CENSORED_PROMPT`: Required. Used when content policy violations occur
- `POLL_INTERVAL_SECONDS`: Default 1 second (increase to 5-10 for lower CPU usage)
- `WORKER_BATCH_SIZE`: Default 10 concurrent tokens (reduce if hitting rate limits)

---

### 3. Apply Database Migration

```bash
cd backend

# Generate migration from SQLModel changes
uv run alembic revision --autogenerate -m "add_image_generation_fields"

# Verify generated migration (check SQL for 3 new columns)
cat alembic/versions/XXXX_add_image_generation_fields.py

# Apply migration
uv run alembic upgrade head

# Test idempotency (rollback and reapply)
uv run alembic downgrade -1
uv run alembic upgrade head
```

Expected migration output:
```
INFO  [alembic.runtime.migration] Running upgrade YYYY -> XXXX, add_image_generation_fields
```

Verify columns exist:
```bash
docker exec -it glisk-postgres-1 psql -U glisk -d glisk -c "\d tokens_s0"
```

Expected output should include:
```
 image_url           | text                        |           |
 generation_attempts | integer                     |           | not null default 0
 generation_error    | text                        |           |
```

---

### 4. Start the Application

```bash
cd backend

# Start FastAPI server with worker
uv run uvicorn glisk.main:app --reload --host 0.0.0.0 --port 8000
```

Expected output:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     worker.started poll_interval=1 batch_size=10
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Verify Worker is Running**:
Check logs for polling activity (should see periodic queries even if no tokens exist):
```bash
# In separate terminal
tail -f backend/logs/glisk.log | grep worker
```

Expected: No errors, periodic log entries showing worker is alive

---

## Testing

### Manual Testing

#### Test 1: Generate Image for Single Token

**Setup**: Insert a test token with status='detected'

```bash
docker exec -it glisk-postgres-1 psql -U glisk -d glisk <<EOF
-- Insert test author with prompt
INSERT INTO authors (wallet_address, prompt_text)
VALUES ('0xTEST', 'A majestic sunset over snow-capped mountains')
ON CONFLICT (wallet_address) DO NOTHING;

-- Insert test token
INSERT INTO tokens_s0 (contract_address, status, author_id)
VALUES (
    '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0',
    'detected',
    (SELECT author_id FROM authors WHERE wallet_address = '0xTEST')
)
RETURNING token_id, status;
EOF
```

**Expected Behavior**:
1. Worker detects token (within 1 second)
2. Status changes: `detected` → `generating` → `uploading`
3. `image_url` field populated with Replicate CDN URL
4. Log entry: `token.generation.succeeded`

**Verify Results**:
```bash
# Check token status (should be 'uploading' within ~15-60 seconds)
docker exec -it glisk-postgres-1 psql -U glisk -d glisk <<EOF
SELECT token_id, status, image_url, generation_attempts, generation_error
FROM tokens_s0
WHERE contract_address = '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0'
ORDER BY token_id DESC
LIMIT 1;
EOF
```

Expected output:
```
 token_id | status    | image_url                                  | generation_attempts | generation_error
----------+-----------+--------------------------------------------+---------------------+-----------------
      123 | uploading | https://replicate.delivery/pbxt/abc123/... |                   0 |
```

**Test Image URL**:
```bash
# Copy image_url from above query and open in browser
# Should display generated image of mountains at sunset
```

---

#### Test 2: Simulate Transient Failure (Network Timeout)

**Setup**: Temporarily break Replicate API connectivity

```bash
# Option A: Set invalid API token (simulates auth timeout)
# Edit backend/.env:
REPLICATE_API_TOKEN=invalid_token_for_testing

# Restart server
# Ctrl+C in server terminal, then:
cd backend
uv run uvicorn glisk.main:app --reload

# Insert test token (same as Test 1)
# Worker will fail with PermanentError (invalid token)
```

**Expected Behavior**:
1. Worker attempts generation
2. Receives authentication error (PermanentError)
3. Status: `generating` → `failed`
4. `generation_error` populated with error message
5. Log entry: `token.generation.failed`

**Verify**:
```bash
docker exec -it glisk-postgres-1 psql -U glisk -d glisk <<EOF
SELECT token_id, status, generation_attempts, generation_error
FROM tokens_s0
WHERE contract_address = '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0'
ORDER BY token_id DESC
LIMIT 1;
EOF
```

Expected:
```
 token_id | status | generation_attempts | generation_error
----------+--------+---------------------+-------------------
      124 | failed |                   0 | Invalid API token
```

**Cleanup**: Restore valid `REPLICATE_API_TOKEN` in `.env` and restart server

---

#### Test 3: Content Policy Violation (Fallback Prompt)

**Setup**: Insert token with potentially flagged content

```bash
docker exec -it glisk-postgres-1 psql -U glisk -d glisk <<EOF
-- Insert author with edgy prompt
INSERT INTO authors (wallet_address, prompt_text)
VALUES ('0xTEST2', 'Violent medieval battle with blood and gore')
ON CONFLICT (wallet_address) DO UPDATE SET prompt_text = EXCLUDED.prompt_text;

-- Insert token
INSERT INTO tokens_s0 (contract_address, status, author_id)
VALUES (
    '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0',
    'detected',
    (SELECT author_id FROM authors WHERE wallet_address = '0xTEST2')
)
RETURNING token_id;
EOF
```

**Expected Behavior**:
1. Worker attempts generation with original prompt
2. Replicate rejects due to content policy (may or may not trigger—depends on service)
3. If rejected: Worker retries with fallback prompt
4. Status: `generating` → `uploading`
5. `image_url` contains fallback image (kittens/flowers)
6. Log entry: `token.censored` with original prompt

**Note**: Content policy detection is probabilistic. If Replicate accepts the prompt, you'll get the requested image instead of fallback.

---

### Automated Testing

#### Run Unit Tests

```bash
cd backend

# Test prompt validator
uv run pytest tests/services/image_generation/test_prompt_validator.py -v

# Test Replicate client (requires mocked API)
uv run pytest tests/services/image_generation/test_replicate_client.py -v
```

Expected: All tests pass (8-10 tests total)

---

#### Run Integration Tests

```bash
cd backend

# Test worker with real PostgreSQL (testcontainers)
TZ=America/Los_Angeles uv run pytest tests/workers/test_image_generation_worker.py -v
```

Expected output:
```
test_process_batch_success PASSED
test_process_batch_concurrent PASSED
test_process_single_token_retry PASSED
test_recover_orphaned_tokens PASSED
```

**Note**: Integration tests use testcontainers (Docker required). Tests mock Replicate API calls.

---

## Operations

### Monitoring

#### Check Worker Health

**Log Events to Monitor**:
```bash
# Worker startup/shutdown
tail -f backend/logs/glisk.log | grep "worker\.(started|stopped|error)"

# Token processing
tail -f backend/logs/glisk.log | grep "token\.generation"

# Censorship events (audit trail)
tail -f backend/logs/glisk.log | grep "token\.censored"
```

**Key Metrics** (extract from logs):
- `token.generation.succeeded` count → Success rate
- `token.generation.failed` count → Permanent failure rate
- `token.generation.retry` count → Transient failure rate
- `duration_seconds` field → Generation latency (P50, P95, P99)

---

#### Query Token Status

**Count Tokens by Status**:
```bash
docker exec -it glisk-postgres-1 psql -U glisk -d glisk <<EOF
SELECT status, COUNT(*) as count
FROM tokens_s0
GROUP BY status
ORDER BY status;
EOF
```

Expected output (example):
```
  status   | count
-----------+-------
 detected  |     5  -- Pending generation
 uploading |    42  -- Ready for IPFS (003d)
 failed    |     3  -- Permanent failures
```

**Check Queue Depth** (tokens waiting for generation):
```bash
docker exec -it glisk-postgres-1 psql -U glisk -d glisk <<EOF
SELECT COUNT(*) as queue_depth
FROM tokens_s0
WHERE status = 'detected';
EOF
```

---

#### Inspect Failed Tokens

**View Recent Failures**:
```bash
docker exec -it glisk-postgres-1 psql -U glisk -d glisk <<EOF
SELECT token_id, generation_attempts, generation_error, detected_at
FROM tokens_s0
WHERE status = 'failed'
ORDER BY detected_at DESC
LIMIT 10;
EOF
```

**Common Failure Reasons**:
- `Invalid API token` → Check `REPLICATE_API_TOKEN` in `.env`
- `Network timeout` → Transient network issue (should auto-retry)
- `Rate limit exceeded` → Hitting API quota (reduce `WORKER_BATCH_SIZE` or increase `POLL_INTERVAL_SECONDS`)
- `Max retries exceeded` → Persistent transient errors (check Replicate service status)

---

### Manual Recovery

#### Reset Failed Token

If a token failed due to temporary issues (API outage, bad deployment), reset it manually:

```bash
docker exec -it glisk-postgres-1 psql -U glisk -d glisk <<EOF
-- Reset specific token
UPDATE tokens_s0
SET status = 'detected',
    generation_attempts = 0,
    generation_error = NULL
WHERE token_id = 123;
EOF
```

Worker will pick it up in next polling cycle (within 1 second).

---

#### Bulk Reset After Outage

If Replicate had a multi-hour outage and many tokens failed:

```bash
docker exec -it glisk-postgres-1 psql -U glisk -d glisk <<EOF
-- Reset all failed tokens that haven't exceeded retry limit
UPDATE tokens_s0
SET status = 'detected',
    generation_error = NULL
WHERE status = 'failed'
  AND generation_attempts < 3;

-- Return count of reset tokens
SELECT COUNT(*) as reset_count
FROM tokens_s0
WHERE status = 'detected'
  AND generation_attempts > 0;
EOF
```

---

### Performance Tuning

#### Reduce CPU Usage (Idle Polling)

If worker is consuming too much CPU during idle periods:

```bash
# Edit backend/.env
POLL_INTERVAL_SECONDS=5  # Increase from 1 to 5 seconds
```

**Tradeoff**: Tokens take up to 5 seconds to be detected instead of 1 second.

---

#### Reduce Concurrent Load (Rate Limits)

If hitting Replicate rate limits (429 errors):

```bash
# Edit backend/.env
WORKER_BATCH_SIZE=3  # Reduce from 10 to 3 concurrent tokens
```

**Tradeoff**: Lower throughput (3 tokens per polling cycle instead of 10).

---

#### Increase Throughput (High Volume)

If processing >100 tokens/hour and queue depth is growing:

```bash
# Option 1: Increase batch size
WORKER_BATCH_SIZE=20  # Process 20 tokens per cycle

# Option 2: Decrease polling interval
POLL_INTERVAL_SECONDS=0.5  # Poll twice per second

# Option 3: Run multiple workers (requires separate deployments)
# Deploy additional backend instances with same config
# PostgreSQL FOR UPDATE SKIP LOCKED prevents duplicate processing
```

**Note**: Multi-worker deployment is out of scope for MVP. Single worker should handle 500+ tokens/hour.

---

## Troubleshooting

### Issue: Worker Not Starting

**Symptom**: No `worker.started` log entry on startup

**Diagnosis**:
```bash
# Check FastAPI startup logs
cd backend
uv run uvicorn glisk.main:app --log-level debug
```

**Common Causes**:
1. Missing `REPLICATE_API_TOKEN` → Check `.env` file
2. Database connection failure → Verify PostgreSQL is running
3. Import error → Check `uv run python -c "import replicate"` succeeds

---

### Issue: Tokens Stuck in 'generating' Status

**Symptom**: Tokens remain in `status='generating'` for >5 minutes

**Diagnosis**:
```bash
# Check for orphaned tokens
docker exec -it glisk-postgres-1 psql -U glisk -d glisk <<EOF
SELECT token_id, status, generation_attempts, detected_at
FROM tokens_s0
WHERE status = 'generating'
  AND detected_at < NOW() - INTERVAL '5 minutes';
EOF
```

**Resolution**:
```bash
# Restart worker (triggers automatic recovery)
# Ctrl+C in server terminal, then restart
cd backend
uv run uvicorn glisk.main:app --reload
```

Worker will auto-recover orphaned tokens on startup (resets to 'detected' if attempts < 3).

---

### Issue: High Failure Rate (>10%)

**Symptom**: Many tokens with `status='failed'`

**Diagnosis**:
```bash
# Check error distribution
docker exec -it glisk-postgres-1 psql -U glisk -d glisk <<EOF
SELECT generation_error, COUNT(*) as count
FROM tokens_s0
WHERE status = 'failed'
GROUP BY generation_error
ORDER BY count DESC;
EOF
```

**Common Causes**:
1. **Invalid API token** (100% failure rate) → Fix `REPLICATE_API_TOKEN` in `.env`, reset tokens
2. **Rate limit exceeded** (>50% failure rate) → Reduce `WORKER_BATCH_SIZE`, increase `POLL_INTERVAL_SECONDS`
3. **Network timeouts** (~10% failure rate) → Normal transient errors, should auto-retry

---

### Issue: Generation Takes >2 Minutes

**Symptom**: Long delay between `detected` and `uploading` status

**Diagnosis**:
```bash
# Check generation duration from logs
grep "token.generation.succeeded" backend/logs/glisk.log | jq '.duration_seconds' | sort -n
```

**Common Causes**:
1. **Slow model** (`flux-pro` takes 30-60s) → Switch to `flux-schnell` (10-15s)
2. **Replicate service latency** → Check https://status.replicate.com
3. **High queue depth** → Increase `WORKER_BATCH_SIZE` to process more tokens concurrently

---

## Next Steps

After image generation is working:

1. **Verify end-to-end flow**:
   - Mint event detected (003b) → Token in `detected` status
   - Image generation (003c) → Token in `uploading` status with `image_url`
   - Ready for IPFS upload (003d)

2. **Production readiness checklist**:
   - [ ] Replicate API token configured
   - [ ] Database migration applied
   - [ ] Worker startup logs show `worker.started`
   - [ ] Test token generates successfully
   - [ ] Failed token recovery procedure documented
   - [ ] Monitoring logs for `token.generation.*` events

3. **Move to 003d**: IPFS Upload & Metadata
   - Read `image_url` from tokens with status='uploading'
   - Download image from Replicate CDN
   - Upload to IPFS (Lighthouse.storage)
   - Update token with permanent IPFS URI

---

## Reference

### File Locations

- **Configuration**: `backend/.env`
- **Migration**: `backend/alembic/versions/XXXX_add_image_generation_fields.py`
- **Worker**: `backend/src/glisk/workers/image_generation_worker.py`
- **Service**: `backend/src/glisk/services/image_generation/replicate_client.py`
- **Repository**: `backend/src/glisk/repositories/token_repository.py`
- **Tests**: `backend/tests/workers/test_image_generation_worker.py`

### Useful Commands

```bash
# Start worker
cd backend && uv run uvicorn glisk.main:app --reload

# Check queue depth
docker exec -it glisk-postgres-1 psql -U glisk -d glisk -c "SELECT COUNT(*) FROM tokens_s0 WHERE status='detected';"

# View recent tokens
docker exec -it glisk-postgres-1 psql -U glisk -d glisk -c "SELECT token_id, status, generation_attempts FROM tokens_s0 ORDER BY token_id DESC LIMIT 10;"

# Tail worker logs
tail -f backend/logs/glisk.log | grep worker

# Run tests
cd backend && TZ=America/Los_Angeles uv run pytest tests/workers/ -v
```

### External Links

- Replicate Docs: https://replicate.com/docs
- Replicate Status: https://status.replicate.com
- Flux Model Docs: https://replicate.com/black-forest-labs/flux-schnell
- GitHub Issues: [Your repo URL]
