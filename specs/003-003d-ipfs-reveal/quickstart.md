# Quickstart Guide: IPFS Upload and Batch Reveal

**Feature**: 003-003d-ipfs-reveal
**Date**: 2025-10-17
**Prerequisites**: 003a (backend foundation), 003b (event detection), 003c (image generation)

## Overview

This guide walks through setting up, testing, and operating the IPFS upload and batch reveal workers. The IPFS upload worker automatically uploads generated images and metadata to IPFS via Pinata, while the reveal worker batches tokens and reveals them on-chain.

## Prerequisites

### Required Services

1. **PostgreSQL** (from 003a)
   - Running on localhost:5432 or via Docker
   - Database initialized with 003a/003b/003c schema

2. **Pinata Account** (IPFS Pinning Service)
   - Sign up at https://pinata.cloud
   - Generate JWT token: https://app.pinata.cloud/keys
   - Note: Free tier supports up to 500 pins (need paid tier for 1000+ tokens)

3. **Alchemy Account** (Blockchain RPC)
   - Already configured from 003b
   - API key provides access to Base L2 network

4. **Keeper Wallet** (On-Chain Transactions)
   - Generate new Ethereum wallet for keeper operations
   - Fund with Base Sepolia ETH (~0.1 ETH recommended for testing)
   - Never use personal wallet (keeper private key stored in .env)

### Existing Infrastructure

This feature builds on:
- **003a**: Database schema (`tokens_s0`, `authors` tables)
- **003b**: Event detection (populates tokens with status='detected')
- **003c**: Image generation (populates `image_url` for status='uploading')

## Setup

### 1. Install Dependencies

```bash
cd backend

# Add web3.py (already installed from 003b)
# Add requests library for Pinata API
uv add requests

# Verify installation
uv run python -c "import requests; print(requests.__version__)"
```

Expected output: `2.x.x` (current requests version)

---

### 2. Configure Environment

Add IPFS and keeper configuration to `backend/.env`:

```bash
# IPFS Upload (Pinata) - 003d
PINATA_JWT=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...  # Your JWT from Pinata
PINATA_GATEWAY=gateway.pinata.cloud  # Default: public gateway

# Blockchain Keeper - 003d
KEEPER_PRIVATE_KEY=0x1234567890abcdef...  # DO NOT use personal wallet
KEEPER_GAS_STRATEGY=medium  # Options: slow, medium, fast (unused for EIP-1559)
REVEAL_GAS_BUFFER=1.2  # 20% safety buffer (float, e.g., 1.2 = 20%)
TRANSACTION_TIMEOUT_SECONDS=180  # Wait up to 3 minutes for confirmation

# Workers - 003d
BATCH_REVEAL_WAIT_SECONDS=5  # Wait 5 seconds to accumulate batch
BATCH_REVEAL_MAX_TOKENS=50  # Maximum tokens per batch

# Existing from 003b (required for keeper)
ALCHEMY_API_KEY=your_alchemy_api_key
NETWORK=BASE_SEPOLIA
GLISK_NFT_CONTRACT_ADDRESS=0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0
```

**Configuration Notes**:
- `PINATA_JWT`: Required. Get from https://app.pinata.cloud/keys (select "Admin" permissions)
- `KEEPER_PRIVATE_KEY`: Required. Generate dedicated wallet: `cast wallet new` (Foundry) or use MetaMask
- `KEEPER_GAS_STRATEGY`: Unused for EIP-1559 (Base L2), kept for compatibility
- `REVEAL_GAS_BUFFER`: Default 1.2 (20%). Increase to 1.5 (50%) if transactions fail due to gas
- `BATCH_REVEAL_WAIT_SECONDS`: Trade-off between latency (5s default) and gas efficiency
- `BATCH_REVEAL_MAX_TOKENS`: Default 50. Reduce if transactions fail due to size

---

### 3. Fund Keeper Wallet

```bash
# Get keeper wallet address
uv run python -c "from eth_account import Account; acc = Account.from_key('YOUR_KEEPER_PRIVATE_KEY'); print(acc.address)"

# Example output: 0x1234567890123456789012345678901234567890

# Fund wallet using Base Sepolia faucet
# Visit: https://www.alchemy.com/faucets/base-sepolia
# Or use Superchain faucet: https://app.optimism.io/faucet

# Verify balance
cast balance 0x1234567890123456789012345678901234567890 --rpc-url https://sepolia.base.org
```

Expected balance: >0.05 ETH (enough for ~500-1000 reveal transactions on testnet)

---

### 4. Apply Database Migrations

```bash
cd backend

# Generate migrations from SQLModel changes
uv run alembic revision --autogenerate -m "add_ipfs_reveal_fields"
uv run alembic revision --autogenerate -m "create_ipfs_upload_records"
uv run alembic revision --autogenerate -m "create_reveal_transactions"

# Verify generated migrations (check SQL for new columns and tables)
ls -la alembic/versions/

# Apply migrations
uv run alembic upgrade head

# Test idempotency (rollback and reapply)
uv run alembic downgrade -3  # Rollback 3 migrations
uv run alembic upgrade head
```

Expected migration output:
```
INFO  [alembic.runtime.migration] Running upgrade XXXX -> YYYY, add_ipfs_reveal_fields
INFO  [alembic.runtime.migration] Running upgrade YYYY -> ZZZZ, create_ipfs_upload_records
INFO  [alembic.runtime.migration] Running upgrade ZZZZ -> AAAA, create_reveal_transactions
```

Verify tables and columns exist:
```bash
# Check tokens_s0 columns
docker exec -it backend-postgres-1 psql -U glisk -d glisk -c "\d tokens_s0"

# Check new audit tables
docker exec -it backend-postgres-1 psql -U glisk -d glisk -c "\dt ipfs_upload_records"
docker exec -it backend-postgres-1 psql -U glisk -d glisk -c "\dt reveal_transactions"
```

Expected output should include:
```
# tokens_s0 columns (new)
 image_cid       | text                        |           |
 metadata_cid    | text                        |           |
 reveal_tx_hash  | text                        |           |

# New tables
 ipfs_upload_records  | table | glisk
 reveal_transactions  | table | glisk
```

---

### 5. Start the Application

```bash
cd backend

# Start FastAPI server with workers
uv run uvicorn glisk.main:app --reload --host 0.0.0.0 --port 8000
```

Expected output:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     worker.started worker=image_generation poll_interval=1 batch_size=10
INFO:     worker.started worker=ipfs_upload poll_interval=1 batch_size=10
INFO:     worker.started worker=reveal poll_interval=1 batch_wait=5 batch_max=50
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Verify Workers are Running**:
Check logs for polling activity (should see periodic queries):
```bash
# In separate terminal
tail -f backend/logs/glisk.log | grep worker
```

Expected: No errors, periodic log entries showing all 3 workers alive

---

## Testing

### Manual Testing

#### Test 1: IPFS Upload (Single Token)

**Setup**: Insert a test token with status='uploading' and image_url

```bash
docker exec -it backend-postgres-1 psql -U glisk -d glisk <<EOF
-- Insert test author
INSERT INTO authors (wallet_address, prompt_text)
VALUES ('0xTEST_IPFS', 'A majestic sunset over mountains')
ON CONFLICT (wallet_address) DO NOTHING;

-- Insert token with image (simulating 003c completion)
INSERT INTO tokens_s0 (contract_address, status, author_id, image_url)
VALUES (
    '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0',
    'uploading',
    (SELECT author_id FROM authors WHERE wallet_address = '0xTEST_IPFS'),
    'https://replicate.delivery/pbxt/abc123/output.png'
)
RETURNING token_id, status;
EOF
```

**Expected Behavior**:
1. IPFS upload worker detects token (within 1 second)
2. Downloads image from `image_url`
3. Uploads image to Pinata → receives `image_cid`
4. Builds metadata JSON with `ipfs://<image_cid>`
5. Uploads metadata to Pinata → receives `metadata_cid`
6. Status changes: `uploading` → `ready`
7. Log entries: `ipfs.image_uploaded`, `ipfs.metadata_uploaded`

**Verify Results** (wait ~10-30 seconds):
```bash
# Check token status
docker exec -it backend-postgres-1 psql -U glisk -d glisk <<EOF
SELECT token_id, status, image_cid, metadata_cid
FROM tokens_s0
WHERE contract_address = '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0'
ORDER BY token_id DESC
LIMIT 1;
EOF
```

Expected output:
```
 token_id | status | image_cid                                  | metadata_cid
----------+--------+--------------------------------------------+--------------------------------------------
      123 | ready  | bafkreih5aznjvttude6c3wbvqeebb6rlx5wkbz... | bafkreihjk9abc123xyz456...
```

**Verify IPFS Upload Records**:
```bash
docker exec -it backend-postgres-1 psql -U glisk -d glisk <<EOF
SELECT upload_id, token_id, upload_type, status, ipfs_cid
FROM ipfs_upload_records
WHERE token_id = (SELECT token_id FROM tokens_s0 ORDER BY token_id DESC LIMIT 1)
ORDER BY upload_id;
EOF
```

Expected output:
```
 upload_id | token_id | upload_type | status  | ipfs_cid
-----------+----------+-------------+---------+--------------------------------------------
         1 |      123 | image       | success | bafkreih5aznjvttude6c3wbvqeebb6rlx5wkbz...
         2 |      123 | metadata    | success | bafkreihjk9abc123xyz456...
```

**Test IPFS URLs**:
```bash
# Copy image_cid from above query
curl -I https://gateway.pinata.cloud/ipfs/bafkreih5aznjvttude6c3wbvqeebb6rlx5wkbz...
# Should return HTTP 200 (image accessible)

# Copy metadata_cid
curl https://gateway.pinata.cloud/ipfs/bafkreihjk9abc123xyz456...
# Should return JSON metadata with "name", "description", "image" fields
```

---

#### Test 2: Batch Reveal (Multiple Tokens)

**Setup**: Insert 3 test tokens with status='ready' and metadata CIDs

```bash
docker exec -it backend-postgres-1 psql -U glisk -d glisk <<EOF
-- Create 3 tokens ready for reveal
DO \$\$
DECLARE
    author_id_var INTEGER;
BEGIN
    SELECT author_id INTO author_id_var FROM authors WHERE wallet_address = '0xTEST_IPFS';

    FOR i IN 1..3 LOOP
        INSERT INTO tokens_s0 (
            contract_address,
            status,
            author_id,
            image_url,
            image_cid,
            metadata_cid
        ) VALUES (
            '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0',
            'ready',
            author_id_var,
            'https://replicate.delivery/pbxt/test/image.png',
            'bafkreitest' || i,
            'bafkreimeta' || i
        );
    END LOOP;
END \$\$;

-- Verify tokens created
SELECT token_id, status, metadata_cid FROM tokens_s0 WHERE status = 'ready' ORDER BY token_id DESC LIMIT 3;
EOF
```

**Expected Behavior**:
1. Reveal worker polls and finds 3 ready tokens
2. Waits 5 seconds to accumulate more (batch_wait_time)
3. Estimates gas for batch of 3 tokens
4. Submits `revealBatch([id1, id2, id3], [uri1, uri2, uri3])` transaction
5. Waits for confirmation (up to 180 seconds)
6. Status changes: `ready` → `revealed` for all 3 tokens
7. `reveal_tx_hash` populated with transaction hash
8. Log entries: `reveal.gas_estimated`, `reveal.batch_submitted`, `reveal.batch_confirmed`

**Verify Results** (wait ~15-60 seconds):
```bash
# Check token status
docker exec -it backend-postgres-1 psql -U glisk -d glisk <<EOF
SELECT token_id, status, reveal_tx_hash
FROM tokens_s0
WHERE status = 'revealed'
ORDER BY token_id DESC
LIMIT 3;
EOF
```

Expected output:
```
 token_id | status   | reveal_tx_hash
----------+----------+------------------------------------------------------------------
      126 | revealed | 0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890
      125 | revealed | 0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890
      124 | revealed | 0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890
```

**Verify Reveal Transaction Record**:
```bash
docker exec -it backend-postgres-1 psql -U glisk -d glisk <<EOF
SELECT reveal_id, tx_hash, array_length(token_ids, 1) as token_count, status, gas_used
FROM reveal_transactions
ORDER BY reveal_id DESC
LIMIT 1;
EOF
```

Expected output:
```
 reveal_id | tx_hash                                                            | token_count | status    | gas_used
-----------+--------------------------------------------------------------------+-------------+-----------+---------
         1 | 0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef123456... |           3 | confirmed |  150000
```

**Verify On-Chain** (using Basescan):
```bash
# Copy tx_hash from above query
# Visit: https://sepolia.basescan.org/tx/0xabcdef123...
# Should show successful transaction calling "revealBatch" function
```

---

#### Test 3: IPFS Upload Failure (Rate Limit)

**Setup**: Temporarily set invalid Pinata JWT to simulate auth failure

```bash
# Edit backend/.env
PINATA_JWT=invalid_jwt_for_testing

# Restart server
# Ctrl+C in server terminal, then:
cd backend
uv run uvicorn glisk.main:app --reload

# Insert test token (same as Test 1)
```

**Expected Behavior**:
1. Worker attempts upload
2. Receives 401 Unauthorized (PermanentError)
3. Status: `uploading` → `failed`
4. `generation_error` populated with error message
5. IPFS upload record created with status='failed'
6. Log entry: `ipfs.permanent_error`

**Verify**:
```bash
docker exec -it backend-postgres-1 psql -U glisk -d glisk <<EOF
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
----------+--------+---------------------+---------------------------
      127 | failed |                   1 | IPFS upload failed: 401
```

**Cleanup**: Restore valid `PINATA_JWT` in `.env` and restart server

---

#### Test 4: Reveal Transaction Revert

**Setup**: Insert token with invalid metadata CID (will cause contract revert)

```bash
docker exec -it backend-postgres-1 psql -U glisk -d glisk <<EOF
-- Insert token with empty metadata CID (invalid)
INSERT INTO tokens_s0 (
    contract_address,
    status,
    author_id,
    image_url,
    image_cid,
    metadata_cid
) VALUES (
    '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0',
    'ready',
    (SELECT author_id FROM authors WHERE wallet_address = '0xTEST_IPFS'),
    'https://replicate.delivery/pbxt/test/image.png',
    'bafkreitest',
    ''  -- Empty string will cause contract to revert
)
RETURNING token_id;
EOF
```

**Expected Behavior**:
1. Reveal worker submits transaction
2. Transaction reverts on-chain (invalid metadata URI)
3. Receipt status: 0 (reverted)
4. Token remains in 'ready' status (available for investigation/retry)
5. Reveal transaction record marked as 'failed'
6. Log entry: `reveal.permanent_error` with revert reason

**Verify**:
```bash
# Check token status (should remain 'ready')
docker exec -it backend-postgres-1 psql -U glisk -d glisk <<EOF
SELECT token_id, status, metadata_cid
FROM tokens_s0
WHERE contract_address = '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0'
ORDER BY token_id DESC
LIMIT 1;
EOF
```

Expected:
```
 token_id | status | metadata_cid
----------+--------+-------------
      128 | ready  |             -- Token remains ready (investigation needed)
```

**Check Reveal Transaction Record**:
```bash
docker exec -it backend-postgres-1 psql -U glisk -d glisk <<EOF
SELECT reveal_id, tx_hash, status, error_message
FROM reveal_transactions
ORDER BY reveal_id DESC
LIMIT 1;
EOF
```

Expected:
```
 reveal_id | tx_hash                                          | status | error_message
-----------+--------------------------------------------------+--------+----------------------------
         2 | 0xfailed123...                                   | failed | Transaction reverted: ...
```

**Cleanup**: Delete invalid token or fix metadata_cid

---

### Automated Testing

#### Run Unit Tests

```bash
cd backend

# Test Pinata client
uv run pytest tests/services/ipfs/test_pinata_client.py -v

# Test keeper service
uv run pytest tests/services/blockchain/test_keeper_service.py -v
```

Expected: All tests pass (~10-15 tests total)

---

#### Run Integration Tests

```bash
cd backend

# Test IPFS upload worker with testcontainers
TZ=America/Los_Angeles uv run pytest tests/workers/test_ipfs_upload_worker.py -v

# Test reveal worker with testcontainers
TZ=America/Los_Angeles uv run pytest tests/workers/test_reveal_worker.py -v

# Test end-to-end pipeline
TZ=America/Los_Angeles uv run pytest tests/test_e2e_pipeline.py -v
```

Expected output:
```
test_ipfs_upload_success PASSED
test_ipfs_upload_retry PASSED
test_reveal_batch_accumulation PASSED
test_reveal_batch_gas_estimation PASSED
test_e2e_mint_to_reveal PASSED
```

**Note**: Integration tests use testcontainers (Docker required). Tests mock Pinata and blockchain responses.

---

## Operations

### Monitoring

#### Check Worker Health

**Log Events to Monitor**:
```bash
# Worker startup/shutdown
tail -f backend/logs/glisk.log | grep "worker\.(started|stopped|error)"

# IPFS upload events
tail -f backend/logs/glisk.log | grep "ipfs\."

# Reveal batch events
tail -f backend/logs/glisk.log | grep "reveal\."
```

**Key Metrics** (extract from logs):
- `ipfs.image_uploaded` count → IPFS success rate
- `ipfs.permanent_error` count → Configuration/quota issues
- `reveal.batch_confirmed` count → On-chain reveal success rate
- `reveal.permanent_error` count → Contract revert rate
- `duration_seconds` field → Latency (IPFS upload, batch reveal)

---

#### Query Token Status

**Count Tokens by Status**:
```bash
docker exec -it backend-postgres-1 psql -U glisk -d glisk <<EOF
SELECT status, COUNT(*) as count
FROM tokens_s0
GROUP BY status
ORDER BY status;
EOF
```

Expected output (example):
```
  status    | count
------------+-------
 detected   |     5  -- Pending generation (003c)
 uploading  |    12  -- Pending IPFS upload (003d)
 ready      |     8  -- Pending batch reveal (003d)
 revealed   |   150  -- Successfully revealed on-chain
 failed     |     5  -- Permanent failures
```

**Check Queue Depth**:
```bash
# Tokens waiting for IPFS upload
docker exec -it backend-postgres-1 psql -U glisk -d glisk -c "SELECT COUNT(*) FROM tokens_s0 WHERE status='uploading';"

# Tokens waiting for reveal
docker exec -it backend-postgres-1 psql -U glisk -d glisk -c "SELECT COUNT(*) FROM tokens_s0 WHERE status='ready';"
```

---

#### Inspect Failed Tokens

**View Recent IPFS Upload Failures**:
```bash
docker exec -it backend-postgres-1 psql -U glisk -d glisk <<EOF
SELECT token_id, generation_attempts, generation_error, detected_at
FROM tokens_s0
WHERE status = 'failed'
  AND generation_error LIKE '%IPFS%'
ORDER BY detected_at DESC
LIMIT 10;
EOF
```

**View Recent Reveal Failures**:
```bash
docker exec -it backend-postgres-1 psql -U glisk -d glisk <<EOF
SELECT reveal_id, tx_hash, status, error_message, submitted_at
FROM reveal_transactions
WHERE status = 'failed'
ORDER BY submitted_at DESC
LIMIT 10;
EOF
```

---

#### Monitor Gas Usage

**Analyze Batch Efficiency**:
```bash
docker exec -it backend-postgres-1 psql -U glisk -d glisk <<EOF
SELECT
    array_length(token_ids, 1) as batch_size,
    gas_limit,
    gas_used,
    ROUND(100.0 * (gas_limit - gas_used) / gas_limit, 2) as buffer_unused_pct
FROM reveal_transactions
WHERE status = 'confirmed'
ORDER BY submitted_at DESC
LIMIT 10;
EOF
```

Expected output:
```
 batch_size | gas_limit | gas_used | buffer_unused_pct
------------+-----------+----------+-------------------
          3 |    180000 |   150000 |             16.67  -- 20% buffer sufficient
         10 |    450000 |   380000 |             15.56  -- Good utilization
```

**Cost Analysis**:
```bash
# Calculate average gas cost per token
docker exec -it backend-postgres-1 psql -U glisk -d glisk <<EOF
SELECT
    AVG(gas_used * 1.0 / array_length(token_ids, 1)) as avg_gas_per_token,
    MIN(array_length(token_ids, 1)) as min_batch_size,
    MAX(array_length(token_ids, 1)) as max_batch_size
FROM reveal_transactions
WHERE status = 'confirmed';
EOF
```

---

### Manual Recovery

#### Reset Failed IPFS Upload

If a token failed due to temporary Pinata outage:

```bash
docker exec -it backend-postgres-1 psql -U glisk -d glisk <<EOF
-- Reset specific token
UPDATE tokens_s0
SET status = 'uploading',
    generation_attempts = 0,
    generation_error = NULL
WHERE token_id = 123;
EOF
```

Worker will pick it up in next polling cycle (within 1 second).

---

#### Retry Failed Reveal Transaction

If a batch failed due to temporary blockchain issue:

```bash
docker exec -it backend-postgres-1 psql -U glisk -d glisk <<EOF
-- Tokens from failed batch remain in 'ready' status
-- They will be automatically retried on next poll
-- No manual action needed (tokens never marked as failed for transient errors)

-- If you need to identify tokens from failed batch:
SELECT t.token_id, t.status
FROM tokens_s0 t
WHERE t.token_id = ANY(
    SELECT unnest(token_ids)
    FROM reveal_transactions
    WHERE status = 'failed'
    ORDER BY reveal_id DESC
    LIMIT 1
);
EOF
```

---

#### Bulk Reset After Service Outage

If Pinata or blockchain had multi-hour outage:

```bash
docker exec -it backend-postgres-1 psql -U glisk -d glisk <<EOF
-- Reset all failed tokens that haven't exceeded retry limit
UPDATE tokens_s0
SET status = 'uploading',
    generation_error = NULL
WHERE status = 'failed'
  AND generation_error LIKE '%IPFS%'
  AND generation_attempts < 3;

-- Return count of reset tokens
SELECT COUNT(*) as reset_count
FROM tokens_s0
WHERE status = 'uploading'
  AND generation_attempts > 0;
EOF
```

---

### Performance Tuning

#### Reduce IPFS Upload Load

If hitting Pinata rate limits (429 errors):

```bash
# Edit backend/.env
POLL_INTERVAL_SECONDS=2  # Increase from 1 to 2 seconds
WORKER_BATCH_SIZE=5  # Reduce from 10 to 5 concurrent uploads
```

**Tradeoff**: Lower throughput (5 tokens per 2 seconds vs 10 per 1 second)

---

#### Increase Reveal Batch Size

If gas costs are high and you want better batching:

```bash
# Edit backend/.env
BATCH_REVEAL_WAIT_SECONDS=10  # Wait longer to accumulate tokens
BATCH_REVEAL_MAX_TOKENS=100  # Allow larger batches
```

**Tradeoff**: Higher latency (tokens wait up to 10 seconds), risk of transaction size limits

---

#### Optimize for Low Latency

If you want faster reveals even with small batches:

```bash
# Edit backend/.env
BATCH_REVEAL_WAIT_SECONDS=2  # Reduce from 5 to 2 seconds
```

**Tradeoff**: Smaller average batch size, less gas optimization

---

## Troubleshooting

### Issue: IPFS Worker Not Starting

**Symptom**: No `worker.started worker=ipfs_upload` log entry

**Diagnosis**:
```bash
# Check configuration validation warnings
grep "config.validation.warning" backend/logs/glisk.log
```

**Common Causes**:
1. Missing `PINATA_JWT` → Check `.env` file, get token from https://app.pinata.cloud/keys
2. Invalid JWT format → Ensure no spaces or newlines, copy entire token
3. Import error → Check `uv run python -c "import requests"` succeeds

---

### Issue: Reveal Worker Not Starting

**Symptom**: No `worker.started worker=reveal` log entry

**Diagnosis**:
```bash
# Check configuration validation warnings
grep "KEEPER_PRIVATE_KEY not set" backend/logs/glisk.log
```

**Common Causes**:
1. Missing `KEEPER_PRIVATE_KEY` → Generate dedicated wallet and add to `.env`
2. Invalid private key format → Must be 0x-prefixed, 66 characters (64 hex + 0x)
3. Web3 connection failure → Verify `ALCHEMY_API_KEY` is correct

---

### Issue: Tokens Stuck in 'uploading' Status

**Symptom**: Tokens remain in `status='uploading'` for >5 minutes

**Diagnosis**:
```bash
# Check IPFS upload errors
grep "ipfs.permanent_error\|ipfs.transient_error" backend/logs/glisk.log
```

**Common Causes**:
1. **401 Unauthorized** → Invalid `PINATA_JWT` (fix token in `.env`, reset tokens)
2. **403 Forbidden** → Pinata quota exceeded (upgrade plan or clear old pins)
3. **429 Rate Limit** → Too many concurrent uploads (reduce `WORKER_BATCH_SIZE`)
4. **Network timeout** → Image URL unreachable (check Replicate CDN status)

**Resolution**:
```bash
# Check specific token error
docker exec -it backend-postgres-1 psql -U glisk -d glisk <<EOF
SELECT token_id, generation_error, generation_attempts
FROM tokens_s0
WHERE status = 'uploading'
  AND detected_at < NOW() - INTERVAL '5 minutes';
EOF
```

---

### Issue: Tokens Stuck in 'ready' Status

**Symptom**: Tokens remain in `status='ready'` for >10 minutes

**Diagnosis**:
```bash
# Check reveal worker logs
grep "reveal.permanent_error\|reveal.transient_error" backend/logs/glisk.log
```

**Common Causes**:
1. **Keeper wallet unfunded** → Check balance: `cast balance <KEEPER_ADDRESS> --rpc-url https://sepolia.base.org`
2. **Gas estimation failure** → Smart contract not deployed or not accessible
3. **Transaction revert** → Invalid token IDs or metadata URIs (check reveal_transactions table)
4. **Nonce conflict** → Multiple workers running (ensure only one reveal worker active)

**Resolution**:
```bash
# Check keeper balance
KEEPER_ADDRESS=$(uv run python -c "from eth_account import Account; acc = Account.from_key('YOUR_KEY'); print(acc.address)")
cast balance $KEEPER_ADDRESS --rpc-url https://sepolia.base.org

# Fund if balance < 0.01 ETH
# Visit https://www.alchemy.com/faucets/base-sepolia
```

---

### Issue: High Gas Costs (Batch Inefficiency)

**Symptom**: Small batch sizes (1-3 tokens), high gas cost per token

**Diagnosis**:
```bash
# Check recent batch sizes
docker exec -it backend-postgres-1 psql -U glisk -d glisk <<EOF
SELECT
    reveal_id,
    array_length(token_ids, 1) as batch_size,
    submitted_at
FROM reveal_transactions
WHERE status = 'confirmed'
ORDER BY submitted_at DESC
LIMIT 10;
EOF
```

**Resolution**:
```bash
# Increase batch wait time to accumulate more tokens
# Edit backend/.env
BATCH_REVEAL_WAIT_SECONDS=10  # Increase from 5 to 10 seconds

# Restart server
```

---

### Issue: Reveal Transaction Failures (>10%)

**Symptom**: Many transactions with `status='failed'` in reveal_transactions table

**Diagnosis**:
```bash
# Check error distribution
docker exec -it backend-postgres-1 psql -U glisk -d glisk <<EOF
SELECT error_message, COUNT(*) as count
FROM reveal_transactions
WHERE status = 'failed'
GROUP BY error_message
ORDER BY count DESC;
EOF
```

**Common Causes**:
1. **Gas estimation error** (100% failure) → Contract issue, verify deployment
2. **Transaction revert** (~10-20% failure) → Invalid token data, check metadata_cid
3. **Timeout** (~5% failure) → Network congestion, increase `TRANSACTION_TIMEOUT_SECONDS`

---

## Next Steps

After IPFS upload and reveal are working:

1. **Verify end-to-end flow**:
   - Mint event detected (003b) → Token in `detected` status
   - Image generation (003c) → Token in `uploading` status with `image_url`
   - IPFS upload (003d) → Token in `ready` status with `image_cid` and `metadata_cid`
   - Batch reveal (003d) → Token in `revealed` status with `reveal_tx_hash`

2. **Production readiness checklist**:
   - [ ] Pinata JWT configured and validated
   - [ ] Keeper wallet funded with sufficient ETH
   - [ ] Database migrations applied (3 new migrations)
   - [ ] All 3 workers starting successfully
   - [ ] Test token completes full pipeline (detected → revealed)
   - [ ] IPFS URLs accessible via gateway
   - [ ] Reveal transactions visible on Basescan
   - [ ] Monitoring logs for `ipfs.*` and `reveal.*` events

3. **MVP Complete!** 🎉
   - Full pipeline operational: mint → generate → upload → reveal
   - Users can see their NFTs with metadata on OpenSea/marketplaces
   - System handles errors gracefully with automatic retries
   - Audit tables provide full observability

4. **Optional 003e - Operations Tooling** (1 week):
   - Manual reveal API (admin trigger)
   - Admin API for token inspection
   - Health monitoring endpoints
   - Author management CLI
   - Transaction retry mechanism

---

## Reference

### File Locations

- **Configuration**: `backend/.env`
- **Migrations**: `backend/alembic/versions/XXXX_add_ipfs_reveal_fields.py` (3 files)
- **Workers**: `backend/src/glisk/workers/ipfs_upload_worker.py`, `backend/src/glisk/workers/reveal_worker.py`
- **Services**: `backend/src/glisk/services/ipfs/pinata_client.py`, `backend/src/glisk/services/blockchain/keeper.py`
- **Repositories**: `backend/src/glisk/repositories/token.py` (extended), `backend/src/glisk/repositories/ipfs_upload_record.py`, `backend/src/glisk/repositories/reveal_transaction.py`
- **Tests**: `backend/tests/workers/test_ipfs_upload_worker.py`, `backend/tests/workers/test_reveal_worker.py`, `backend/tests/test_e2e_pipeline.py`

### Useful Commands

```bash
# Start all workers
cd backend && uv run uvicorn glisk.main:app --reload

# Check token status distribution
docker exec -it backend-postgres-1 psql -U glisk -d glisk -c "SELECT status, COUNT(*) FROM tokens_s0 GROUP BY status;"

# Check IPFS upload queue depth
docker exec -it backend-postgres-1 psql -U glisk -d glisk -c "SELECT COUNT(*) FROM tokens_s0 WHERE status='uploading';"

# Check reveal queue depth
docker exec -it backend-postgres-1 psql -U glisk -d glisk -c "SELECT COUNT(*) FROM tokens_s0 WHERE status='ready';"

# View recent reveal transactions
docker exec -it backend-postgres-1 psql -U glisk -d glisk -c "SELECT reveal_id, tx_hash, array_length(token_ids, 1) as count, status FROM reveal_transactions ORDER BY reveal_id DESC LIMIT 5;"

# Tail worker logs
tail -f backend/logs/glisk.log | grep "worker\|ipfs\|reveal"

# Check keeper wallet balance
cast balance $(uv run python -c "from eth_account import Account; acc = Account.from_key('YOUR_KEY'); print(acc.address)") --rpc-url https://sepolia.base.org

# Run tests
cd backend && TZ=America/Los_Angeles uv run pytest tests/ -v
```

### External Links

- Pinata Docs: https://docs.pinata.cloud
- Pinata Dashboard: https://app.pinata.cloud
- Base Sepolia Explorer: https://sepolia.basescan.org
- Base Sepolia Faucet: https://www.alchemy.com/faucets/base-sepolia
- Alchemy Dashboard: https://dashboard.alchemy.com
- OpenSea Testnet: https://testnets.opensea.io
- GitHub Issues: [Your repo URL]
