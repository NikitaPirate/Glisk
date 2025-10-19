# Token Recovery CLI

Command-line tool for recovering missing tokens from blockchain state.

## Overview

**Problem:** Tokens may be missing from database due to:
- Webhook delivery failures
- Backend downtime during mints
- Database inconsistencies

**Solution:** Query `contract.nextTokenId()` to identify gaps and create missing token records.

---

## Usage

### Basic Recovery

```bash
cd backend

# Recover all missing tokens
python -m glisk.cli.recover_tokens
```

**Output:**
```
2025-10-19 12:34:56 [info] recovery.started
2025-10-19 12:34:57 [info] recovery.completed recovered=15 duplicates_skipped=2 failed=0 total_on_chain=100
```

---

### Limit Recovery Batch Size

```bash
# Recover up to 100 tokens
python -m glisk.cli.recover_tokens --limit 100
```

**Use case:** Rate-limit blockchain RPC calls during recovery

---

### Dry Run (Preview)

```bash
# Preview missing tokens without persisting
python -m glisk.cli.recover_tokens --dry-run
```

**Output:**
```
[DRY RUN] Would recover 15 missing tokens: [1, 5, 12, 23, ...]
```

**Use case:** Verify which tokens are missing before actual recovery

---

### Verbose Logging

```bash
# Enable detailed logging
python -m glisk.cli.recover_tokens -v
```

**Output:**
```
2025-10-19 12:34:56 [debug] recovery.query_next_token_id next_token_id=100
2025-10-19 12:34:57 [debug] recovery.found_missing_tokens count=15 missing_ids=[1,5,12,...]
2025-10-19 12:34:58 [debug] token.created token_id=1 author_id=uuid...
...
```

---

## How It Works

### 1. Query On-Chain State

```python
next_token_id = contract.functions.nextTokenId().call()  # e.g., 100
```

**Meaning:** 100 tokens have been minted (IDs 0-99)

---

### 2. Find Gaps in Database

```sql
-- PostgreSQL generate_series to find missing IDs
SELECT gs.id AS missing_token_id
FROM generate_series(0, 99) AS gs(id)
LEFT JOIN tokens_s0 ON tokens_s0.token_id = gs.id
WHERE tokens_s0.token_id IS NULL
ORDER BY gs.id
```

**Example result:** `[1, 5, 12, 23, 45]` (5 missing tokens)

---

### 3. Create Token Records

For each missing token:

```python
# Query on-chain author attribution
prompt_author = contract.functions.tokenPromptAuthor(token_id).call()

# Look up author in database (or use default)
author = await uow.authors.get_by_wallet(prompt_author)

# Create token record with status='detected'
token = Token(
    token_id=token_id,
    author_id=author.id,
    status=TokenStatus.DETECTED,  # Will be picked up by workers
)
await uow.tokens.create(token)
```

**Note:** Uses `tokenPromptAuthor()` mapping for accurate attribution

---

### 4. Race Condition Handling

If webhook creates token during recovery:

```python
try:
    await uow.tokens.create(token)
except IntegrityError:
    # UNIQUE constraint violation on token_id
    # Skip duplicate, log as "skipped_duplicate_count"
    pass
```

**Safe:** Database UNIQUE constraint prevents duplicates

---

## Automatic Recovery (On Startup)

**Enabled by default:** Backend runs recovery automatically on app startup (before workers start)

**Implementation:** `app.py` lifespan hook

```python
# app.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ... setup ...

    # Run token recovery before starting workers
    recovery_service = TokenRecoveryService(w3, contract_address, settings)
    result = await recovery_service.recover_missing_tokens(
        uow=uow,
        limit=settings.recovery_batch_size,
    )

    # ... start workers ...
```

**Why?** Ensures database consistency before workers process tokens

**Disable:** Set `RECOVERY_BATCH_SIZE=0` in `.env` (feature not exposed yet)

---

## Configuration

```env
# Blockchain connection (required)
ALCHEMY_API_KEY=your_api_key
GLISK_NFT_CONTRACT_ADDRESS=0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0
NETWORK=BASE_SEPOLIA

# Default author for tokens with unregistered authors (required)
GLISK_DEFAULT_AUTHOR_WALLET=0x0000000000000000000000000000000000000001

# Recovery batch size (optional, default: 1000)
# Note: Not yet exposed in Settings, hardcoded in CLI
# RECOVERY_BATCH_SIZE=1000
```

---

## When to Run Manual Recovery

### 1. After Extended Downtime

**Scenario:** Backend was down for 24 hours, missed 50 mint events

**Action:**
```bash
python -m glisk.cli.recover_tokens
```

**Result:** Creates 50 token records with `status='detected'`, workers process them

---

### 2. After Webhook Misconfiguration

**Scenario:** Webhook URL was incorrect, no events delivered for 1 week

**Action:**
```bash
# Preview missing tokens
python -m glisk.cli.recover_tokens --dry-run

# Recover all
python -m glisk.cli.recover_tokens
```

---

### 3. Database Restore from Backup

**Scenario:** Restored database from 3-day-old backup, lost recent mints

**Action:**
```bash
python -m glisk.cli.recover_tokens
```

**Result:** Fills gap between backup timestamp and current blockchain state

---

### 4. Manual Verification

**Scenario:** Suspect database inconsistencies, want to verify

**Action:**
```bash
# Check if any tokens are missing
python -m glisk.cli.recover_tokens --dry-run
```

**Result:** If output shows "0 missing tokens", database is consistent

---

## Monitoring

### Check for Missing Tokens

```bash
# Query expected vs actual token count
docker exec backend-postgres-1 psql -U glisk -d glisk <<EOF
SELECT
  (SELECT COUNT(*) FROM tokens_s0) AS db_count,
  'Compare with contract.nextTokenId()' AS note;
EOF
```

### View Recovery Logs

```bash
# Application startup logs
docker compose logs backend-api | grep "recovery"

# Manual CLI logs (if run separately)
tail -f backend/logs/glisk.log | grep "recovery"
```

---

## Troubleshooting

### "Contract not found"

**Error:**
```
ContractNotFoundError: Contract at 0x... not found on BASE_SEPOLIA
```

**Cause:** `GLISK_NFT_CONTRACT_ADDRESS` is incorrect or contract not deployed

**Resolution:**
1. Verify contract address in `.env`
2. Check contract deployment on block explorer (basescan.org)
3. Ensure `NETWORK` matches deployment network

---

### "Default author not found"

**Error:**
```
DefaultAuthorNotFoundError: Default author 0x0000...0001 not found in database
```

**Cause:** Default author record missing from `authors` table

**Resolution:**
```bash
# Create default author
docker exec backend-postgres-1 psql -U glisk -d glisk <<EOF
INSERT INTO authors (id, wallet_address, prompt_text, created_at)
VALUES (
  gen_random_uuid(),
  '0x0000000000000000000000000000000000000001',
  'Generic fallback prompt for unknown authors',
  NOW()
);
EOF
```

---

### "Blockchain connection failed"

**Error:**
```
BlockchainConnectionError: Failed to connect to Alchemy RPC
```

**Cause:** `ALCHEMY_API_KEY` invalid or network unreachable

**Resolution:**
1. Verify `ALCHEMY_API_KEY` in `.env`
2. Test RPC connection: `curl "https://base-sepolia.g.alchemy.com/v2/$ALCHEMY_API_KEY"`
3. Check network connectivity

---

### Recovery Takes Too Long

**Symptom:** Recovery stalls on large token counts (>10,000)

**Diagnosis:**
```bash
# Check token count
docker exec backend-postgres-1 psql -U glisk -d glisk -c \
  "SELECT COUNT(*) FROM tokens_s0"
```

**Resolution:**
```bash
# Batch recovery with limits
python -m glisk.cli.recover_tokens --limit 1000  # Batch 1
python -m glisk.cli.recover_tokens --limit 1000  # Batch 2
# ... repeat until complete
```

**Optimization:** Recovery processes 1 token per RPC call (slow for large gaps)

---

## Implementation Details

### Why `nextTokenId()` Instead of Event Logs?

**Alternative approach:** Parse `BatchMinted` events from historical logs

**Advantages of `nextTokenId()`:**
- ✅ Simpler: Single contract call vs block range pagination
- ✅ Faster: O(missing_tokens) RPC calls vs O(total_blocks)
- ✅ Accurate: Source of truth for total minted count
- ✅ Maintainable: ~60% less code than event-based recovery

**Trade-off:** Requires one RPC call per missing token to fetch author

---

### Author Attribution Accuracy

**Accurate source:** `contract.tokenPromptAuthor(tokenId)` mapping

**Why not infer from minter?** Minter ≠ Prompt Author

**Example:**
- Alice calls `contract.batchMint(bob_wallet, "prompt", quantity)`
- Minter: Alice
- Prompt Author: Bob ← This is what we store

**Recovery uses:** `tokenPromptAuthor()` for correct attribution

---

## Additional Documentation

- **Backend Overview:** [../../README.md](../../README.md)
- **Token Recovery Service:** [../services/blockchain/token_recovery.py](../services/blockchain/token_recovery.py)
- **Feature Spec:** [../../../../specs/004-recovery-1-nexttokenid/spec.md](../../../../specs/004-recovery-1-nexttokenid/spec.md)
- **Quickstart:** [../../../../specs/004-recovery-1-nexttokenid/quickstart.md](../../../../specs/004-recovery-1-nexttokenid/quickstart.md)
