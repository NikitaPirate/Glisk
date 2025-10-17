# Quickstart: Mint Event Detection System

**Feature**: 003-003b-event-detection
**Created**: 2025-10-17
**Time to First Test**: 5 minutes

## Prerequisites

- Python 3.14 installed
- PostgreSQL 14+ running (via Docker Compose)
- Backend foundation from 003a deployed
- Alchemy account with API key
- ngrok installed (for local webhook testing)

---

## Quick Setup (5 Minutes)

### 1. Install Dependencies

```bash
cd backend
uv add web3 python-dotenv
```

**Dependencies Added**:
- `web3` - Ethereum JSON-RPC client for eth_getLogs
- `python-dotenv` - Already installed in 003a (load .env files)

---

### 2. Configure Environment

Add to `backend/.env`:

```bash
# Alchemy Integration (new)
ALCHEMY_API_KEY=your_alchemy_api_key_here
ALCHEMY_WEBHOOK_SECRET=your_signing_key_from_dashboard
GLISK_NFT_CONTRACT_ADDRESS=0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0
NETWORK=BASE_SEPOLIA
GLISK_DEFAULT_AUTHOR_WALLET=0x0000000000000000000000000000000000000001

# Existing from 003a
DATABASE_URL=postgresql+psycopg://glisk:glisk@localhost:5432/glisk
```

**Get Your Alchemy Credentials**:
1. Go to https://dashboard.alchemy.com
2. Create app: "Glisk Backend" on Base Sepolia
3. Copy API key → `ALCHEMY_API_KEY`
4. Navigate to Webhooks → Create Custom Webhook
5. Copy signing key → `ALCHEMY_WEBHOOK_SECRET`

---

### 3. Start Backend Server

```bash
cd backend
uv run uvicorn glisk.main:app --reload
```

**Expected Output**:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
```

---

### 4. Expose Webhook Endpoint (Local Dev)

**Terminal 2**:
```bash
ngrok http 8000
```

**Expected Output**:
```
Forwarding  https://abc123.ngrok.io -> http://localhost:8000
```

**Copy the ngrok URL** (e.g., `https://abc123.ngrok.io`) for next step.

---

### 5. Configure Alchemy Webhook

1. Go to Alchemy Dashboard → Webhooks
2. Click "Create Webhook" → "Custom Webhook"
3. Configure:
   - **Name**: Glisk Mint Events
   - **Network**: Base Sepolia
   - **Webhook URL**: `https://abc123.ngrok.io/webhooks/alchemy`
   - **Filters**:
     - Contract Address: `0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0`
     - Event Signature: `BatchMinted(address,address,uint256,uint256,uint256)`
4. Click "Create Webhook"
5. **Copy Signing Key** → Update `ALCHEMY_WEBHOOK_SECRET` in `.env`
6. Restart backend server (Ctrl+C, then `uv run uvicorn...` again)

---

## Test the System

### Test 1: Verify Webhook Endpoint (30 seconds)

```bash
# Generate test signature
WEBHOOK_SECRET="your_webhook_secret_here"
BODY='{"webhookId":"test","id":"test001","type":"CUSTOM","event":{"data":{"block":{"logs":[]}}}}'
SIGNATURE=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" | awk '{print $2}')

# Send test request
curl -X POST http://localhost:8000/webhooks/alchemy \
  -H "Content-Type: application/json" \
  -H "X-Alchemy-Signature: $SIGNATURE" \
  -d "$BODY"
```

**Expected Response**:
```json
{
  "status": "success",
  "message": "Event processed successfully"
}
```

---

### Test 2: Mint NFT on Testnet (2 minutes)

**Prerequisites**:
- MetaMask with Base Sepolia testnet
- Test ETH (get from https://www.coinbase.com/faucets/base-ethereum-sepolia-faucet)
- GliskNFT contract deployed on Base Sepolia (from 001-full-smart-contract)

**Steps**:
1. Open Etherscan for your contract: `https://sepolia.basescan.org/address/0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0`
2. Go to "Write Contract" tab
3. Connect MetaMask
4. Call `mint(yourAddress, yourAddress)` with 0.01 ETH
5. Confirm transaction

**Expected**:
- Transaction succeeds on-chain
- Within 5 seconds: Alchemy sends webhook to your ngrok URL
- Backend logs show: `INFO: Event processed successfully`
- Database has new records in `mint_events` and `tokens_s0`

**Verify in Database**:
```bash
docker exec -it glisk-postgres psql -U glisk -c "SELECT * FROM mint_events ORDER BY detected_at DESC LIMIT 1;"
docker exec -it glisk-postgres psql -U glisk -c "SELECT * FROM tokens_s0 ORDER BY created_at DESC LIMIT 1;"
```

---

### Test 3: Event Recovery CLI (1 minute)

```bash
# Recover events from block where contract was deployed
cd backend
python -m glisk.cli.recover_events --from-block 12345000 --to-block 12346000 --dry-run
```

**Expected Output**:
```
[timestamp] INFO: DRY RUN MODE - No database modifications
[timestamp] INFO: Starting event recovery from block 12345000 to 12346000
[timestamp] INFO: Found 3 events (would be stored):
  - MintEvent: tx=0x1234..., token_id=1
  - MintEvent: tx=0x5678..., token_id=2
  - MintEvent: tx=0x9abc..., token_id=3
[timestamp] INFO: DRY RUN COMPLETE
```

---

## Common Issues

### Issue: "Invalid webhook signature"

**Cause**: `ALCHEMY_WEBHOOK_SECRET` doesn't match Alchemy dashboard.

**Fix**:
1. Go to Alchemy Dashboard → Webhooks → Your Webhook
2. Click "View Signing Key"
3. Copy and update `.env`
4. Restart backend server

---

### Issue: "Contract address mismatch"

**Cause**: Webhook configured for wrong contract address.

**Fix**:
1. Verify contract address in `.env` matches deployed contract
2. Update Alchemy webhook filters to match
3. Re-test with new mint

---

### Issue: "Database connection failed"

**Cause**: PostgreSQL not running or wrong `DATABASE_URL`.

**Fix**:
```bash
# Start PostgreSQL
cd /Users/nikita/PycharmProjects/glisk
docker compose up -d postgres

# Verify connection
docker exec -it glisk-postgres psql -U glisk -c "SELECT 1;"
```

---

### Issue: "Author not found"

**Cause**: Author wallet not registered in `authors` table.

**Expected**: Uses default author from `GLISK_DEFAULT_AUTHOR_WALLET`.

**To Register Author**:
```bash
docker exec -it glisk-postgres psql -U glisk -c "
INSERT INTO authors (id, wallet_address, created_at, updated_at)
VALUES (
  gen_random_uuid(),
  '0xYourWalletAddress',
  NOW(),
  NOW()
);
"
```

---

## Development Workflow

### Local Development Loop

1. **Make code changes** in `backend/src/glisk/`
2. **Backend auto-reloads** (uvicorn --reload)
3. **Test with curl** or mint NFT on testnet
4. **Check logs** in terminal
5. **Verify database** with psql queries

---

### Testing Checklist

- [ ] Webhook signature validation (valid, invalid, missing)
- [ ] Event parsing (BatchMinted event structure)
- [ ] Author lookup (registered, unregistered)
- [ ] Duplicate event handling (409 Conflict)
- [ ] Database transaction rollback on error
- [ ] Recovery CLI (dry-run, actual recovery)
- [ ] Rate limit handling (reduce batch-size)

---

## Next Steps

### After Quickstart Works:

1. **Run Integration Tests**:
   ```bash
   cd backend
   TZ=America/Los_Angeles uv run pytest tests/test_webhook_integration.py -v
   ```

2. **Configure Production Webhook**:
   - Get production domain (e.g., `api.glisk.com`)
   - Update Alchemy webhook URL
   - Switch to `BASE_MAINNET` network

3. **Set Up Monitoring**:
   - Add structured logging (already using structlog from 003a)
   - Monitor webhook latency (<500ms target)
   - Track event processing rate

4. **Deploy to Production**:
   - Set environment variables on server
   - Run initial recovery: `python -m glisk.cli.recover_events --from-block <deployment_block>`
   - Verify webhook receiving events

---

## Architecture Overview

```
Alchemy Blockchain Indexer
  ↓ (webhook)
POST /webhooks/alchemy
  ↓
Signature Validation (HMAC-SHA256)
  ↓
Event Parsing (BatchMinted)
  ↓
Author Lookup (wallet → author_id)
  ↓
Database Transaction (UoW)
  ├─ INSERT mint_events
  └─ INSERT tokens_s0 (status='detected')
  ↓
200 OK Response
```

---

## File Structure

```
backend/
├── src/glisk/
│   ├── api/routes/
│   │   └── webhooks.py           # POST /webhooks/alchemy
│   ├── services/blockchain/
│   │   ├── alchemy_signature.py  # HMAC validation
│   │   └── event_recovery.py     # eth_getLogs logic
│   ├── cli/
│   │   └── recover_events.py     # CLI command
│   └── core/
│       └── config.py              # Add Alchemy settings
├── tests/
│   ├── test_webhook_signature.py
│   ├── test_webhook_integration.py
│   └── test_event_recovery.py
└── .env                           # Configuration
```

---

## Key Decisions

**From research.md**:
- ✅ Use **web3.py** instead of Alchemy Python SDK (better documentation)
- ✅ **Manual event decoding** (no ABI required for simple event)
- ✅ **UNIQUE constraint** for idempotency (database-level, not application-level)
- ✅ **Constant-time HMAC comparison** (`hmac.compare_digest()` for security)
- ✅ **Inline event parsing** (no parser class - follows Simplicity First)

**From constitution check**:
- ✅ Detection only - NO processing logic
- ✅ Uses existing 003a tables - NO schema changes
- ✅ Integration-first testing with testcontainers
- ✅ UTC timestamps enforced

---

## Resources

- [Alchemy Webhooks Documentation](https://docs.alchemy.com/docs/alchemy-notify)
- [web3.py Events Documentation](https://web3py.readthedocs.io/en/stable/web3.eth.html#web3.eth.Eth.get_logs)
- [HMAC Security Best Practices](https://docs.python.org/3/library/hmac.html)
- [Base Sepolia Testnet Faucet](https://www.coinbase.com/faucets/base-ethereum-sepolia-faucet)
- [ngrok Documentation](https://ngrok.com/docs)

---

## Support

**Debugging**:
1. Check backend logs (uvicorn output)
2. Check ngrok dashboard: http://localhost:4040
3. Check Alchemy dashboard webhook activity
4. Query database directly with psql

**Need Help?**:
- Review [research.md](./research.md) for implementation details
- Check [data-model.md](./data-model.md) for database schema
- See [contracts/webhook-api.md](./contracts/webhook-api.md) for API spec
