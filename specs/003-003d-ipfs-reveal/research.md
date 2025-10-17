# Research Notes: IPFS Upload and Batch Reveal Mechanism

**Feature**: 003-003d-ipfs-reveal
**Date**: 2025-10-17
**Phase**: 0 - Research

## Overview

This document consolidates research findings for key technical decisions in the IPFS upload and batch reveal feature. All decisions are validated against industry standards, constitutional principles, and the existing codebase architecture.

---

## Research Area 1: IPFS Pinning Service Selection

### Decision: Pinata

### Rationale

1. **Immediate Availability & Simple Onboarding**: Unlike Infura IPFS (requires pre-qualification approval) and NFT.storage (stopped accepting uploads June 2024), Pinata offers immediate access with straightforward sign-up. Critical for MVP velocity.

2. **Proven NFT Metadata Workflow**: Widely recognized as most developer-friendly service for NFT metadata storage. The `pinJSONToIPFS` endpoint is purpose-built for this exact use case with extensive documentation.

3. **Mature Python Integration**: Simple REST API works with standard HTTP libraries (requests). Community-maintained `pinata-python` package available. Fits existing Python backend without complex dependencies.

### Alternatives Considered

**NFT.storage / web3.storage (Storacha)**
- ❌ **Dealbreaker**: NFT.storage classic stopped accepting new uploads June 30, 2024
- ✅ Free tier was attractive (previously unlimited for NFTs)
- ⚠️ Storacha uses new w3up API with UCAN authentication (more complex setup)
- ⚠️ Python SDK is unofficial/community-maintained
- **Verdict**: Too much migration risk and API complexity for MVP timeline

**Infura IPFS**
- ❌ **Dealbreaker**: Limited to "pre-qualified customers" requiring approval process
- ✅ Strong ConsenSys backing and Ethereum integration
- ✅ Enterprise-grade reliability
- **Verdict**: Access barriers unsuitable for rapid MVP development

**Lighthouse.storage**
- ✅ Official Python SDK (lighthouseweb3 v0.1.5)
- ✅ Pay-per-use model (pay once, store forever on Filecoin)
- ⚠️ Primarily Filecoin-focused vs IPFS hot storage
- ⚠️ Less established for NFT metadata use cases
- ⚠️ Pricing in attoFIL adds complexity vs USD-based pricing
- **Verdict**: Interesting for future long-term storage, overkill for MVP

### Integration Notes

**Authentication**:
- Method: Bearer token (JWT) via Authorization header
- Format: `Authorization: Bearer <PINATA_JWT>`
- Token management: Store in `.env` as `PINATA_JWT`

**Primary Endpoint: pinJSONToIPFS**
```http
POST https://api.pinata.cloud/pinning/pinJSONToIPFS
Content-Type: application/json
Authorization: Bearer <token>

{
  "pinataContent": {
    "name": "Token #123",
    "description": "...",
    "image": "ipfs://..."
  },
  "pinataMetadata": {
    "name": "token-123-metadata.json"
  },
  "pinataOptions": {
    "cidVersion": 1
  }
}
```

**Error Classification**:

*Transient Errors (RETRYABLE)*:
- `429 Too Many Requests` - Rate limit exceeded (check Retry-After header)
- `503 Service Unavailable` - Temporary service overload
- `500 Internal Server Error` - Transient server error (max 3 retries)

*Permanent Errors (NON-RETRYABLE)*:
- `400 Bad Request` - Malformed request (invalid JSON, missing fields)
- `401 Unauthorized` - Invalid/missing API key (configuration error)
- `403 Forbidden` - Access denied (quota exceeded, account suspended)

**Rate Limits**:
- Standard: 180 requests per minute (all tiers)
- Recommended: 3 requests/second with 333ms delay between requests
- On 429: Read Retry-After header, wait + jitter (0-5s)
- Exponential backoff: 1s → 2s → 4s → 8s for 5xx errors

**CID Format**:
- Support both v0 (legacy) and v1 (current standard)
- Specify in request: `"cidVersion": 1` (recommended)
- Gateway URLs: `https://gateway.pinata.cloud/ipfs/<CID>` (public) or `https://<subdomain>.mypinata.cloud/ipfs/<CID>` (dedicated)
- IPFS URI for metadata: `ipfs://<CID>`

**Pricing for 1000 Tokens MVP**:
- Free tier: 1 GB storage, **500 max pins** (❌ BLOCKER for 1000 tokens)
- Paid tier (Picnic): ~$20/month (1 TB storage, no file limits)
- Per-token cost: $0.02-0.06 per token
- Recommendation: Start free tier for dev/test, upgrade before production

**Reliability**:
- Uptime SLA: 99.9% (8.77 hours downtime/year)
- Decentralized IPFS nodes with CDN caching
- Best practices: Retry logic for transient failures, dedicated gateway URLs

---

## Research Area 2: Web3.py Gas Strategies for Base L2

### Decision: Use EIP-1559 (eth_maxPriorityFeePerGas + base fee) OR legacy eth_gasPrice with 20% buffer, plus built-in wait_for_transaction_receipt() with 180-second timeout

### Rationale

1. **Base L2 Supports Standard Ethereum JSON-RPC Methods**: Both `eth_gasPrice` and `eth_maxPriorityFeePerGas` confirmed to work on Base network (OP Stack, EVM-compatible).

2. **Web3.py Built-in Gas Strategies Are Legacy Only**: Official docs state: "Gas price strategy is only supported for legacy transactions. EIP-1559 introduced `maxFeePerGas` and `maxPriorityFeePerGas` which should be used over `gasPrice` whenever possible."

3. **20% Buffer Is Industry-Standard**: Research shows 20-25% buffer recommended for L2 networks to handle gas volatility. ERC-4337 operations recommend 25% on L2. Ethereum best practice: 10-20% minimum.

4. **Built-in wait_for_transaction_receipt() Sufficient**:
   - Default timeout: 120 seconds (configurable to 180s)
   - Raises TimeExhausted exception on timeout (catchable)
   - Polls every 0.1 seconds
   - No need for custom monitoring worker (aligns with Constitution)

5. **Simple Error Handling Matches Constitution Mandate**:
   - TransientError: Gas estimation failure → log, tokens remain 'ready', retry next poll
   - PermanentError: Transaction revert → log revert reason, tokens remain 'ready', investigation required
   - No complex retry logic at transaction level (polling loop handles naturally)

### Alternatives Considered

**Custom gas price monitoring worker**
- Rejected: Requires background worker polling gas prices continuously, database for price history, complex prediction logic (~200+ LOC)
- Why rejected: Constitution mandates simplicity. 20% buffer + polling loop provides sufficient reliability for MVP.

**Third-party gas estimation APIs (Blocknative, Alchemy Gas API)**
- Rejected: Additional API dependencies, network latency, failure mode if API down, potential costs at scale
- Why rejected: Web3.py RPC methods (`eth_gasPrice`, `eth_maxPriorityFeePerGas`) are free, reliable, provided by Alchemy node already in use.

**Transaction monitoring with pending state checks**
- Rejected: Requires separate pending transactions table, worker to poll status, complex state machine, nonce conflict resolution
- Why rejected: `wait_for_transaction_receipt()` with 180s timeout handles 95%+ cases. Timeout allows retry on next poll with fresh gas price.

**Database-backed nonce management**
- Deferred: Use `w3.eth.get_transaction_count(keeper_wallet, 'pending')` for now. Only needed for concurrent workers (not in scope).
- Evidence: 'pending' parameter sufficient for single-worker sequential processing. Upgrade to Redis-backed nonce only if conflicts observed in production.

### Implementation Notes

**Recommended Approach (EIP-1559)**:
```python
max_priority_fee = w3.eth.max_priority_fee
base_fee = w3.eth.get_block('latest')['baseFeePerGas']
buffer_multiplier = 1.2  # 20% buffer

maxPriorityFeePerGas = int(max_priority_fee * buffer_multiplier)
maxFeePerGas = int((base_fee * 2) + maxPriorityFeePerGas)

tx = contract.functions.revealBatch(token_ids, metadata_uris).build_transaction({
    'from': keeper_wallet_address,
    'maxFeePerGas': maxFeePerGas,
    'maxPriorityFeePerGas': maxPriorityFeePerGas,
    'nonce': w3.eth.get_transaction_count(keeper_wallet_address, 'pending'),
})

estimated_gas = w3.eth.estimate_gas(tx)
tx['gas'] = int(estimated_gas * 1.2)  # 20% buffer on gas limit

signed_tx = w3.eth.account.sign_transaction(tx, private_key=keeper_private_key)
tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)

try:
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
    # Check receipt.status (1 = success, 0 = reverted)
except TimeExhausted:
    logger.error("Transaction confirmation timeout", tx_hash=tx_hash.hex())
    # Token remains in 'ready' state, retry on next poll
```

**Error Handling Strategy**:

| Error Type | Classification | Action | Example |
|------------|---------------|---------|---------|
| Gas estimation failure | Transient | Log error, tokens remain 'ready', retry next poll | Network timeout, node RPC error |
| Transaction submission failure | Transient | Log error, tokens remain 'ready', retry next poll | Nonce conflict, insufficient gas funds |
| Confirmation timeout (180s) | Transient | Log warning with tx_hash, tokens remain 'ready', retry next poll | Network congestion, stuck in mempool |
| Transaction revert (status=0) | Permanent | Log revert reason, tokens remain 'ready', manual investigation | Invalid token IDs, contract logic error |

**Configuration Values**:
```python
GAS_BUFFER_PERCENTAGE: float = 0.20  # 20% safety margin
TRANSACTION_TIMEOUT_SECONDS: int = 180  # 3 minutes
```

**Nonce Management (Simple Approach)**:
```python
nonce = w3.eth.get_transaction_count(keeper_wallet, 'pending')
```

**Why Sufficient for MVP**:
- Single worker processes one batch at a time (no concurrent transactions)
- 'pending' parameter works reliably for sequential processing
- If nonce conflict occurs, submission fails → TransientError → retry with fresh nonce

**When to Upgrade**:
- Multiple reveal workers deployed (horizontal scaling)
- Nonce conflicts observed in production logs
- Upgrade path: Redis-backed nonce counter

**Key web3.py References**:
- Gas estimation: `w3.eth.estimate_gas(transaction)`
- Gas price (legacy): `w3.eth.gas_price` property (RPC: `eth_gasPrice`)
- Max priority fee (EIP-1559): `w3.eth.max_priority_fee` property (RPC: `eth_maxPriorityFeePerGas`)
- Transaction receipt: `w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)`
- Nonce: `w3.eth.get_transaction_count(address, 'pending')`

---

## Research Area 3: Batch Accumulation Patterns

### Decision: Hybrid Time-OR-Size Trigger ("5 seconds OR 50 tokens, whichever comes first")

### Rationale

1. **Industry Standards Validate Hybrid Approach**:
   - **Hyperledger Fabric**: BatchTimeout 2s + Max Message Count 10
   - **L2 Networks** (Arbitrum, Optimism, Base): Batch every 1-3 minutes OR size threshold
   - **Worker Queue Systems** (BullMQ, Azure Queue): Batch sizes 10-50 jobs optimal
   - **Spark Structured Streaming**: Time intervals 5-10 seconds OR size thresholds 50-100 records
   - **Pattern Consensus**: "Time OR size" hybrid is dominant industry pattern

2. **L2 Gas Optimization Research**:
   - **Base L2**: Transactions batched reduce fees to <$0.01 per transaction (10x cheaper than L1)
   - **ERC721A Batch Minting** (Azuki case study):
     - Minting 1 NFT: 93,704 gas
     - Minting 5 NFTs: 103,736 gas (~20k gas per NFT = 78% savings)
     - Pattern: Marginal cost decreases with batch size
   - **Optimal Batch Size**: 10-50 tokens (sweet spot)
     - Below 10: Gas savings insufficient
     - Above 100: Increased risk of failures, timeouts, revert costs
   - **Spec Target**: "Minimum 60% gas cost reduction for batches of 10+ tokens" - **validated by ERC721A data** (78% savings at 5 tokens)

3. **Constitutional Alignment** (Seasonal MVP Principle):
   - **Simplicity First**: Hybrid trigger is simple (basic timer + counter logic)
   - **Seasonal MVP**: 5-second delay provides responsive UX for MVP testing
   - **Clear Over Clever**: Well-understood pattern, no novel algorithms
   - **Avoiding Over-Engineering**: No dynamic batch sizing, priority queuing, or complex prediction logic

4. **Database Pattern Validation**:
   - PostgreSQL `FOR UPDATE SKIP LOCKED` with `ORDER BY` prevents deadlocks
   - Pattern: "Sorting in INSERT necessary to reduce deadlock chance. Use explicit row-level locking in ordered subqueries with ORDER BY FOR UPDATE."
   - Existing image generation worker (003c) already implements this pattern correctly
   - **Reuse same approach** for reveal worker

### Alternatives Considered

**Option A: Pure Time-Based (Every 5 Seconds)**
- Rejected: Inefficient during high volume (small batches waste gas), doesn't leverage L2 batching benefits, fails to optimize gas costs (Spec SC-005: 60% savings)

**Option B: Pure Size-Based (Wait Until 50 Tokens)**
- Rejected: Unbounded latency (could wait indefinitely during low volume), poor UX for MVP, violates Spec SC-002 ("Tokens revealed within 10 seconds")

**Option C: Dynamic Adaptive Batching**
- Rejected: High complexity (gas price monitoring, prediction algorithms), violates "Simplicity First", harder to test (non-deterministic), deferred per plan.md ("No custom gas monitoring")

### Implementation Notes

**Recommended Configuration**:

| Parameter | Value | Source | Rationale |
|-----------|-------|--------|-----------|
| Batch Wait Time | 5 seconds | Spark Streaming, Hyperledger (2s default) | Responsive UX without sacrificing efficiency |
| Batch Max Size | 50 tokens | BullMQ (10-50), Azure Queue (50), NFT research | Gas savings plateau, transaction reliability |
| Gas Buffer | 20% | Spec FR-013 | Safety margin against price volatility |
| Retry Limit | 3 attempts | 003c worker, industry standard | Balance recovery vs infinite loops |
| Poll Interval | 1 second | 003c worker | Responsive without database load |

**Database Pattern: FOR UPDATE SKIP LOCKED with Ordered Locking**:

```python
async def get_ready_for_reveal(
    self,
    limit: int = 50
) -> list[Token]:
    """Get ready tokens for batch reveal with ordered locking.

    Uses FOR UPDATE SKIP LOCKED for safe concurrent worker processing.
    ORDER BY token_id ensures consistent lock ordering to prevent deadlocks.
    """
    result = await self.session.execute(
        select(Token)
        .where(Token.status == TokenStatus.READY)
        .order_by(Token.token_id)  # ← CRITICAL: Prevents deadlocks
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    return list(result.scalars().all())
```

**Key Insight**: Existing image generation worker already uses this pattern correctly (`get_pending_for_generation`). **Reuse same approach** for reveal worker.

**Batch Accumulation Logic (Simplified for MVP)**:

```python
async def get_batch(session_factory, settings) -> list[Token]:
    """Simple batch: immediate lock up to max size, no accumulation."""

    async with session_factory() as session:
        token_repo = TokenRepository(session)

        # Lock up to max_size tokens immediately
        tokens = await token_repo.get_ready_for_reveal(limit=settings.batch_max_size)

        # If we got tokens but batch is small, wait for more
        if 0 < len(tokens) < settings.batch_max_size:
            await asyncio.sleep(settings.batch_wait_time)

            # Poll once more for additional tokens
            remaining = settings.batch_max_size - len(tokens)
            more_tokens = await token_repo.get_ready_for_reveal(limit=remaining)
            tokens.extend(more_tokens)

        return tokens
```

**Trade-off**: Uses two queries (initial + after wait) vs continuous polling. For MVP, **simplicity wins** per Constitution.

**Graceful Shutdown Handling** (matches image_generation_worker.py):

```python
async def run_reveal_worker(session_factory, settings):
    """Main worker loop with graceful shutdown."""

    logger.info("worker.started", batch_wait_time=settings.batch_wait_time, batch_max_size=settings.batch_max_size)

    try:
        while True:
            try:
                # Process batch (completes in-flight operation)
                await process_reveal_batch(session_factory, settings)

                # Wait for next polling interval
                await asyncio.sleep(settings.poll_interval_seconds)

            except asyncio.CancelledError:
                # Propagate cancellation for graceful shutdown
                raise

            except Exception as e:
                # Log and continue with backoff
                logger.error("worker.error", error=str(e), exc_info=True)
                await asyncio.sleep(5)  # Back off before retry

    except asyncio.CancelledError:
        # Graceful shutdown: log and re-raise to signal completion
        logger.info("worker.stopped")
        raise
```

**Key Decision: Complete Current Batch vs Drain Queue**:
- ✅ **Complete current batch**: `process_batch()` runs to completion before `CancelledError` propagates
- ✅ **No drain queue**: Remaining tokens stay in `ready` status, next worker startup picks them up
- ✅ **No orphan recovery needed for 'ready' state**: Unlike 'generating' (transient), 'ready' is stable

**Edge Cases**:

| Edge Case | Pattern | Source |
|-----------|---------|--------|
| Worker crashes mid-batch | Reset in-flight state on startup | 003c `recover_orphaned_tokens()` |
| Multiple workers race for same tokens | `FOR UPDATE SKIP LOCKED` prevents overlap | PostgreSQL research |
| Transaction stuck in mempool | Timeout after 180s, retry next poll | Ethereum research, Spec FR-016 |
| Batch partially fails (invalid tokens) | Entire batch reverts, all remain 'ready' | Smart contract atomicity |
| Gas price spike during accumulation | Re-estimate immediately before submission | web3.py handles, Spec FR-013 |
| Keeper wallet out of funds | Permanent error logged, manual intervention | Spec edge cases |

---

## Summary of Key Decisions

| Decision Area | Choice | Primary Justification |
|---------------|--------|----------------------|
| **IPFS Service** | Pinata | Immediate access, proven NFT workflow, simple REST API |
| **Gas Strategy** | EIP-1559 OR eth_gasPrice + 20% buffer | Web3.py built-ins sufficient, no custom monitoring needed |
| **Transaction Monitoring** | wait_for_transaction_receipt(180s) | Built-in method handles 95%+ cases, Constitution mandates simplicity |
| **Batch Trigger** | 5 seconds OR 50 tokens | Industry-validated hybrid, balances latency and gas efficiency |
| **Batch Accumulation** | Two-query approach (lock + wait + lock) | Simplest implementation, matches Constitution "Clear Over Clever" |
| **Graceful Shutdown** | Complete current batch, no drain | Matches 003c worker pattern, idempotent retries |
| **Nonce Management** | get_transaction_count('pending') | Sufficient for single worker, upgrade only if conflicts observed |

---

## Constitutional Compliance

All decisions validated against GLISK Constitution v1.1.0:

- ✅ **Simplicity First**: Pinata REST API (no SDK), web3.py built-ins (no custom monitoring), two-query batch logic (no continuous polling)
- ✅ **Seasonal MVP**: 5-second latency for responsive UX, 20% gas buffer for reliability, no over-engineered prediction algorithms
- ✅ **Clear Over Clever**: Industry-standard patterns (hybrid batching, FOR UPDATE SKIP LOCKED), reusable from 003c worker
- ✅ **Backend Standards (v1.1.0)**: UTC enforcement, Alembic workflow, repository pattern, testcontainers-first testing

---

## Next Steps (Phase 1: Design & Contracts)

1. Generate data-model.md with schema extensions (tokens_s0 fields, audit tables)
2. Generate contracts/internal-service-contracts.md (Pinata client API, keeper service API)
3. Generate quickstart.md with manual testing procedures
4. Update agent context with new technologies (Pinata API, web3.py batch patterns)

All research findings will inform Phase 1 design artifacts.
