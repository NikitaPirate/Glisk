# Background Workers

Three workers process NFT tokens through their lifecycle. All auto-start with FastAPI application.

## Workers

### 1. Image Generation Worker

**File:** `image_generation_worker.py`

**Purpose:** Generate AI images for detected tokens

**Flow:**
```
detected → generating → uploading
```

**Process:**
1. Polls for tokens with `status='detected'`
2. Fetches author prompt from database
3. Calls Replicate API (flux-schnell model)
4. Stores image URL in `image_url` field
5. Updates status to `uploading`

**Error Handling:**
- Transient errors: Retry with exponential backoff (3 attempts max)
- Content policy violations: Retry with fallback prompt
- Permanent errors: Mark as `failed` with error message

**Configuration:**
```env
REPLICATE_API_TOKEN=r8_your_token
REPLICATE_MODEL_VERSION=black-forest-labs/flux-schnell
FALLBACK_CENSORED_PROMPT="Cute kittens..."
POLL_INTERVAL_SECONDS=1
WORKER_BATCH_SIZE=10
```

---

### 2. IPFS Upload Worker

**File:** `ipfs_upload_worker.py`

**Purpose:** Upload images to IPFS and create metadata

**Flow:**
```
uploading → ready
```

**Process:**
1. Polls for tokens with `status='uploading'`
2. Downloads image from `image_url`
3. Uploads image to IPFS via Pinata → `image_cid`
4. Creates ERC-721 metadata JSON
5. Uploads metadata to IPFS → `metadata_cid`
6. Updates status to `ready`

**Error Handling:**
- Transient errors: Retry with exponential backoff (3 attempts max)
- Permanent errors: Mark as `failed` with error message

**Configuration:**
```env
PINATA_JWT=your_jwt_token
PINATA_GATEWAY=gateway.pinata.cloud
POLL_INTERVAL_SECONDS=1
WORKER_BATCH_SIZE=10
```

---

### 3. Reveal Worker

**File:** `reveal_worker.py`

**Purpose:** Batch-reveal tokens on blockchain

**Flow:**
```
ready → revealed
```

**Process:**
1. Polls for tokens with `status='ready'`
2. Batches tokens (up to 50) for gas efficiency
3. Calls `contract.batchRevealMultiple(tokenIds, metadataURIs)`
4. Waits for transaction confirmation
5. Updates status to `revealed` with `reveal_tx_hash`

**Error Handling:**
- Transient errors: Retry transaction with higher gas
- Permanent errors: Mark batch as `failed`, individual tokens remain `ready`

**Configuration:**
```env
KEEPER_PRIVATE_KEY=0xYOUR_KEY
KEEPER_GAS_STRATEGY=medium          # fast | medium | slow
REVEAL_GAS_BUFFER=1.2               # 20% safety buffer
TRANSACTION_TIMEOUT_SECONDS=180
BATCH_REVEAL_WAIT_SECONDS=5         # Wait time before batching
BATCH_REVEAL_MAX_TOKENS=50          # Max batch size
```

---

## Lifecycle

**Auto-start:** Workers start automatically with FastAPI application (in `app.py` lifespan)

**Auto-restart:** Workers automatically restart on crash (1 second delay)

**Graceful shutdown:** Workers cancel on FastAPI shutdown signal

---

## Monitoring

### View Logs

```bash
# All worker events
docker compose logs -f backend-api | grep "worker\."

# Specific worker
docker compose logs -f backend-api | grep "image_generation"

# Token processing events
docker compose logs -f backend-api | grep "token\."
```

### Check Token Status

```bash
# Status distribution
docker exec backend-postgres-1 psql -U glisk -d glisk -c \
  "SELECT status, COUNT(*) FROM tokens_s0 GROUP BY status"

# Recently updated tokens
docker exec backend-postgres-1 psql -U glisk -d glisk -c \
  "SELECT token_id, status, created_at FROM tokens_s0 ORDER BY created_at DESC LIMIT 10"
```

### Check Queue Depth

```bash
# Image generation queue (detected)
docker exec backend-postgres-1 psql -U glisk -d glisk -c \
  "SELECT COUNT(*) FROM tokens_s0 WHERE status='detected'"

# IPFS upload queue (uploading)
docker exec backend-postgres-1 psql -U glisk -d glisk -c \
  "SELECT COUNT(*) FROM tokens_s0 WHERE status='uploading'"

# Reveal queue (ready)
docker exec backend-postgres-1 psql -U glisk -d glisk -c \
  "SELECT COUNT(*) FROM tokens_s0 WHERE status='ready'"
```

---

## Troubleshooting

### Tokens Stuck in Processing State

**Symptom:** Tokens remain in `generating` or `uploading` state for >5 minutes

**Diagnosis:**
```bash
# Check worker logs for errors
docker compose logs backend-api | grep "error"

# Check token error fields
docker exec backend-postgres-1 psql -U glisk -d glisk -c \
  "SELECT token_id, status, generation_attempts, generation_error FROM tokens_s0 WHERE status IN ('generating', 'uploading') ORDER BY created_at"
```

**Resolution:**
- Worker crash: Restart backend (`docker compose restart backend-api`)
- API rate limit: Wait for cooldown, worker will retry
- Invalid configuration: Check `.env` file for required variables

---

### High Failure Rate

**Symptom:** Many tokens with `status='failed'`

**Diagnosis:**
```bash
# Count failures
docker exec backend-postgres-1 psql -U glisk -d glisk -c \
  "SELECT COUNT(*) FROM tokens_s0 WHERE status='failed'"

# Inspect error messages
docker exec backend-postgres-1 psql -U glisk -d glisk -c \
  "SELECT token_id, generation_error FROM tokens_s0 WHERE status='failed' ORDER BY created_at DESC LIMIT 5"
```

**Common causes:**
- `REPLICATE_API_TOKEN` invalid/expired → Regenerate at replicate.com
- `PINATA_JWT` invalid/expired → Regenerate at pinata.cloud
- Keeper wallet insufficient funds → Fund wallet with ETH for gas
- Content policy violations → Prompts contain banned content

**Resolution:**
```bash
# Reset failed tokens after fixing root cause (e.g., API key)
docker exec backend-postgres-1 psql -U glisk -d glisk <<EOF
UPDATE tokens_s0
SET status = 'detected', generation_attempts = 0, generation_error = NULL
WHERE status = 'failed' AND generation_attempts < 3;
EOF
```

---

### Worker Not Starting

**Symptom:** No worker logs on startup

**Diagnosis:**
```bash
# Check application logs
docker compose logs backend-api | grep "application.startup"

# Check for startup errors
docker compose logs backend-api | grep "ERROR"
```

**Resolution:**
- Missing configuration: Verify all required env vars in `.env`
- Database not ready: Wait for postgres, restart backend
- Import errors: Check dependencies with `uv sync`

---

## Performance Tuning

### Reduce CPU Usage

```env
POLL_INTERVAL_SECONDS=5  # Default: 1 (increase polling interval)
WORKER_BATCH_SIZE=3      # Default: 10 (reduce batch size)
```

### Increase Throughput

```env
WORKER_BATCH_SIZE=20     # Default: 10 (process more tokens per poll)
```

### Optimize Gas Efficiency

```env
BATCH_REVEAL_WAIT_SECONDS=10  # Default: 5 (wait longer for fuller batches)
BATCH_REVEAL_MAX_TOKENS=50    # Default: 50 (maximize batch size)
```

---

## Implementation Notes

### Why Workers Don't Use Unit of Work Pattern

Workers use direct session management instead of UoW pattern.

**Reason:** UoW assumes "one context = one transaction = auto-commit on exit"

Workers require "one context = multiple decision points with conditional commits"

**Example:** Image generation worker needs to:
1. Rollback on transient error
2. Increment attempt counter
3. Commit that increment (must persist across retries)
4. Sleep for backoff
5. Continue (don't re-raise exception)

UoW would auto-commit on exit, which doesn't match these semantics.

**Pattern used:** Direct `session.commit()` and `session.rollback()` at decision points

---

## Additional Documentation

- **Backend Overview:** [../../README.md](../../README.md)
- **Quickstart Guides:**
  - [Image Generation](../../../../specs/003-003c-image-generation/quickstart.md)
  - [IPFS Upload & Reveal](../../../../specs/003-003d-ipfs-reveal/quickstart.md)
- **Internal Contracts:**
  - [Image Generation](../../../../specs/003-003c-image-generation/contracts/internal-service-contracts.md)
  - [IPFS & Reveal](../../../../specs/003-003d-ipfs-reveal/contracts/internal-service-contracts.md)
