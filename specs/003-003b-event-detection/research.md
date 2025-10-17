# Alchemy Webhook Integration Research

**Date**: 2025-10-17
**Feature**: 003-003b Event Detection System
**Purpose**: Technical research for implementing Alchemy webhook integration to detect GliskNFT mint events

---

## 1. Alchemy Webhook Payload Structure

### Official Documentation
- **NFT Activity Webhook**: https://www.alchemy.com/docs/reference/nft-activity-webhook
- **Custom Webhook**: https://www.alchemy.com/docs/reference/custom-webhook

### Webhook Types
Alchemy offers two webhook types relevant to our use case:

1. **NFT Activity Webhook** - Specialized for ERC-721/ERC-1155 transfers
2. **Custom Webhook (GraphQL)** - Flexible event filtering with GraphQL queries

**Decision**: Use **Custom Webhook** with GraphQL filters for better control and future extensibility.

**Rationale**:
- NFT Activity webhook only tracks standard Transfer events, not our custom BatchMinted event
- Custom webhooks allow filtering by specific contract address and event signature
- GraphQL structure provides richer transaction context (gas, block info, etc.)
- Better aligned with project's need for precise event detection

### Complete Payload Structure (NFT Activity Webhook)

```json
{
  "webhookId": "wh_5dzeea0ikdnzgq6w",
  "id": "whexs_awxsragnkmh182tl",
  "createdAt": "2024-05-31T21:38:13.912Z",
  "type": "NFT_ACTIVITY",
  "event": {
    "network": "ETH_MAINNET",
    "activity": [
      {
        "fromAddress": "0x715af6b6c6e3aefb97f1f6811ce52db563b38896",
        "toAddress": "0x29469395eaf6f95920e59f858042f0e28d98a20b",
        "contractAddress": "0xbc4ca0eda7647a8ab7c2061c2e118a18a936f13d",
        "blockNum": "0x1310fe1",
        "hash": "0xe6385e8896aa5de1147f8d324ebeb79640f7a0e6fc87f3685d5e39a531f14ea4",
        "erc721TokenId": "0x1eeb",
        "category": "erc721",
        "log": {
          "address": "0xbc4ca0eda7647a8ab7c2061c2e118a18a936f13d",
          "topics": [
            "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
          ],
          "data": "0x",
          "blockNumber": "0x1310fe1",
          "transactionHash": "0xe6385e8896aa5de1147f8d324ebeb79640f7a0e6fc87f3685d5e39a531f14ea4",
          "transactionIndex": "0x20",
          "blockHash": "0x...",
          "logIndex": "0x3a",
          "removed": false
        }
      }
    ]
  }
}
```

### Custom Webhook (GraphQL) Structure

```json
{
  "webhookId": "wh_a55wfsvq5h8n8u3z",
  "id": "whevt_rsdblc6zxi8a6ntl",
  "createdAt": "2024-05-31T21:38:13.912Z",
  "type": "GRAPHQL",
  "event": {
    "data": {
      "block": {
        "logs": [
          {
            "account": {
              "address": "0xbc4ca0eda7647a8ab7c2061c2e118a18a936f13d"
            },
            "topics": [
              "0x...",  // Event signature
              "0x...",  // Indexed parameter 1
              "0x..."   // Indexed parameter 2
            ],
            "data": "0x...",  // Non-indexed parameters (ABI-encoded)
            "index": 42,
            "transaction": {
              "hash": "0x...",
              "index": 32,
              "from": { "address": "0x..." },
              "to": { "address": "0x..." },
              "status": 1,
              "gasUsed": "123456",
              "effectiveGasPrice": "20000000000"
            }
          }
        ]
      }
    }
  }
}
```

### Key Fields for Our Use Case

**Top-Level Metadata**:
- `webhookId` - Webhook identifier (constant for our webhook)
- `id` - **Unique event ID** for deduplication (use as idempotency key)
- `createdAt` - ISO 8601 timestamp when Alchemy created the event
- `type` - Webhook type ("NFT_ACTIVITY" or "GRAPHQL")

**Event Data** (Custom Webhook):
- `event.data.block.logs[]` - Array of log entries
- `log.account.address` - Contract address (filter by GliskNFT address)
- `log.topics[]` - Indexed event parameters
- `log.data` - Non-indexed parameters (ABI-encoded hex string)
- `log.index` - Log index within transaction (for deduplication)
- `log.transaction.hash` - Transaction hash
- `log.transaction.status` - 1 = success, 0 = failure (filter only successful)

**Important Notes**:
- Transactions are returned in a list; multiple events in same block appear in same activity array
- All numeric values (blockNum, tokenId) are hex-encoded strings with "0x" prefix
- Log index is critical for deduplication alongside transaction hash

---

## 2. HMAC Signature Validation

### Official Documentation
- **Webhooks Quickstart**: https://www.alchemy.com/docs/reference/notify-api-quickstart

### Algorithm Specification

**Header Name**: `X-Alchemy-Signature`

**HMAC Algorithm**: `HMAC-SHA256`

**Message Construction**:
1. Obtain the **raw request body** (string, not JSON-parsed object)
2. Retrieve your **signing key** from Alchemy dashboard (per-webhook secret)
3. Concatenate: `signing_key + raw_body`
4. Compute: `HMAC-SHA256(signing_key, raw_body)`
5. Encode as hexadecimal digest

### Python Implementation

```python
import hmac
import hashlib

def validate_alchemy_signature(
    raw_body: bytes,
    signature: str,
    signing_key: str
) -> bool:
    """
    Validate Alchemy webhook signature using HMAC-SHA256.

    Args:
        raw_body: Raw request body bytes (NOT parsed JSON)
        signature: Value from X-Alchemy-Signature header
        signing_key: Webhook signing key from Alchemy dashboard

    Returns:
        True if signature is valid, False otherwise

    Security:
        - Uses hmac.compare_digest() for constant-time comparison
        - Prevents timing attacks by avoiding early-exit comparisons
    """
    # Compute expected signature
    expected = hmac.new(
        key=signing_key.encode('utf-8'),
        msg=raw_body,
        digestmod=hashlib.sha256
    ).hexdigest()

    # Constant-time comparison to prevent timing attacks
    return hmac.compare_digest(expected, signature)
```

### Constant-Time Comparison Best Practices

**Why Constant-Time Comparison is Critical**:
- Standard `==` comparison exits early on first mismatch
- Attackers can measure response time to gradually determine correct signature
- Each matching character increases comparison time slightly
- Eventually, attackers can brute-force the entire signature

**Python's `hmac.compare_digest()`**:
- Added in Python 3.3 (well-supported)
- Uses OpenSSL's `CRYPTO_memcmp()` when available
- Compares all bytes regardless of early mismatches
- Returns boolean (True/False) after comparing entire string
- **ALWAYS use this for signature validation, never `==`**

**Security Considerations**:
- Always validate signature BEFORE any processing logic
- Return 401 Unauthorized immediately on validation failure
- Use raw request body bytes, not JSON-transformed version
- Store signing key in environment variables, never in code
- Signing key is per-webhook (retrieve from Alchemy dashboard)

### Additional Security Measures

**IP Allowlist** (Optional):
Alchemy webhooks originate from these IP addresses:
- `54.236.136.17`
- `34.237.24.169`

Recommendation: Not required if HMAC validation is properly implemented, but can add defense-in-depth.

---

## 3. Alchemy SDK eth_getLogs Usage

### Python SDK Status

**Official Package**: `alchemy-sdk` (PyPI)
- **Installation**: `pip install alchemy-sdk`
- **GitHub**: https://github.com/alchemyplatform/alchemy-sdk-js (JavaScript primary)
- **Python Port**: Community-maintained, less documentation

**Alternative Approach**: Use `web3.py` with Alchemy RPC endpoint
- **Installation**: `pip install web3`
- **Maturity**: Production-ready, extensive documentation
- **Recommendation**: **Use web3.py** for better reliability and documentation

**Decision**: Use `web3.py` with Alchemy HTTP provider for `eth_getLogs` calls.

**Rationale**:
- web3.py is battle-tested with comprehensive documentation
- Alchemy Python SDK is less mature (primarily JavaScript-focused)
- web3.py provides full Ethereum JSON-RPC API, including eth_getLogs
- Easier migration to other RPC providers if needed
- Better typing support and IDE autocomplete

### web3.py Implementation

```python
from web3 import Web3
from eth_utils import to_checksum_address
import os

# Initialize Web3 with Alchemy provider
alchemy_url = f"https://base-sepolia.g.alchemy.com/v2/{os.getenv('ALCHEMY_API_KEY')}"
w3 = Web3(Web3.HTTPProvider(alchemy_url))

# Construct event filter for BatchMinted event
def get_mint_events(
    contract_address: str,
    from_block: int,
    to_block: int | str = "latest"
) -> list:
    """
    Fetch BatchMinted events from blockchain using eth_getLogs.

    Args:
        contract_address: GliskNFT contract address (checksummed)
        from_block: Starting block number (inclusive)
        to_block: Ending block number or "latest"

    Returns:
        List of event log dictionaries
    """
    # Calculate event signature: keccak256("BatchMinted(address,address,uint256,uint256,uint256)")
    event_signature = w3.keccak(text="BatchMinted(address,address,uint256,uint256,uint256)").hex()

    # Create filter parameters
    filter_params = {
        "address": to_checksum_address(contract_address),
        "fromBlock": hex(from_block),
        "toBlock": to_block if to_block == "latest" else hex(to_block),
        "topics": [event_signature]  # Topic[0] is always event signature
    }

    # Call eth_getLogs
    logs = w3.eth.get_logs(filter_params)

    return logs
```

### Event Signature Calculation

**GliskNFT BatchMinted Event** (from contracts/src/GliskNFT.sol:68-74):

```solidity
event BatchMinted(
    address indexed minter,       // Topic[1]
    address indexed promptAuthor, // Topic[2]
    uint256 indexed startTokenId, // Topic[3]
    uint256 quantity,             // Data
    uint256 totalPaid             // Data
);
```

**Signature Calculation**:
```python
from web3 import Web3

# Event signature: event_name(param_type1,param_type2,...)
# Parameter names and 'indexed' keyword are NOT included
signature_string = "BatchMinted(address,address,uint256,uint256,uint256)"

# Hash with keccak256
event_signature_hash = Web3.keccak(text=signature_string).hex()
# Result: 0x... (32-byte hex string)
```

**Important**:
- Only include parameter **types**, not names
- Do not include spaces between parameters
- Do not include `indexed` keyword
- Signature hash goes in `topics[0]`

### Pagination Strategies

**Alchemy Block Range Limits**:
- **Free tier**: 10 blocks per request OR 10,000 logs (whichever hits first)
- **Pay-As-You-Go / Enterprise**: 2,000 blocks OR 10,000 logs OR 150MB response
- **Batch requests**: 500 blocks max (when called via batch RPC)

**Recommended Pagination Strategy** (Adaptive Chunking):

```python
def fetch_events_with_pagination(
    contract_address: str,
    from_block: int,
    to_block: int,
    initial_chunk_size: int = 1000
) -> list:
    """
    Fetch events with adaptive block range chunking.

    Handles pagination by dynamically adjusting chunk size based on:
    - RPC timeouts (reduce chunk size)
    - Empty results (increase chunk size exponentially)
    - Event-rich blocks (reset to smaller chunks)
    """
    all_events = []
    current_block = from_block
    chunk_size = initial_chunk_size

    while current_block <= to_block:
        end_block = min(current_block + chunk_size - 1, to_block)

        try:
            events = get_mint_events(contract_address, current_block, end_block)
            all_events.extend(events)

            if len(events) == 0:
                # No events found, increase chunk size exponentially
                chunk_size = min(chunk_size * 2, 2000)
            else:
                # Events found, reset to conservative chunk size
                chunk_size = initial_chunk_size

            current_block = end_block + 1

        except Exception as e:
            # Timeout or rate limit - reduce chunk size and retry
            if "timeout" in str(e).lower() or "rate limit" in str(e).lower():
                chunk_size = max(chunk_size // 2, 10)
                continue  # Retry same range
            else:
                raise  # Re-raise unexpected errors

    return all_events
```

**Best Practices**:
1. **Start conservative**: 1000 blocks initially (well within all tier limits)
2. **Exponential backoff**: Reduce chunk size by half on timeout
3. **Exponential increase**: Double chunk size when no events found
4. **Cap maximum**: Never exceed 2000 blocks (tier-agnostic safety)
5. **Handle duplicates**: Database UNIQUE constraint handles overlaps

### Rate Limits

**Alchemy Compute Units (CU)**:
- `eth_getLogs` costs **75 CU** per request
- Rate limits measured in **Compute Units Per Second (CUPS)**

**Throughput by Tier**:
- **Free**: 500 CUPS (~6.67 eth_getLogs requests/second)
- **Pay-As-You-Go**: Higher CUPS (scales with usage)
- **Enterprise**: Custom limits

**Rate Limit Handling**:
```python
import time
from web3.exceptions import Web3Exception

def get_logs_with_retry(w3: Web3, filter_params: dict, max_retries: int = 3) -> list:
    """
    Call eth_getLogs with exponential backoff on rate limits.
    """
    for attempt in range(max_retries):
        try:
            return w3.eth.get_logs(filter_params)
        except Web3Exception as e:
            if "rate limit" in str(e).lower() and attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                time.sleep(wait_time)
                continue
            raise
```

**Best Practices**:
- Implement exponential backoff for rate limits
- Monitor usage in Alchemy dashboard
- For recovery CLI, no need for aggressive speed (prefer reliability)
- Webhook processing is real-time, recovery is batch (different performance profiles)

---

## 4. Event Log Parsing

### Log Structure

Ethereum event logs contain two data locations:

1. **Topics** (indexed parameters):
   - `topics[0]`: Event signature hash (always)
   - `topics[1-3]`: Indexed parameters (up to 3, since topics[0] is reserved)
   - Stored separately for efficient filtering
   - Cannot exceed 3 indexed params per event

2. **Data** (non-indexed parameters):
   - ABI-encoded hex string
   - All non-indexed parameters concatenated
   - Requires ABI decoding to extract values

### BatchMinted Event Decoding

**Event Definition**:
```solidity
event BatchMinted(
    address indexed minter,       // topics[1]
    address indexed promptAuthor, // topics[2]
    uint256 indexed startTokenId, // topics[3]
    uint256 quantity,             // data (offset 0)
    uint256 totalPaid             // data (offset 32)
);
```

**Manual Decoding (No ABI Required)**:

```python
from web3 import Web3
from eth_utils import to_checksum_address

def decode_batch_minted_event(log: dict) -> dict:
    """
    Decode BatchMinted event log without ABI.

    Args:
        log: Event log from eth_getLogs response

    Returns:
        Decoded event data dictionary
    """
    # Indexed parameters (topics)
    # topics[0] is event signature, skip it
    minter = to_checksum_address("0x" + log["topics"][1].hex()[-40:])
    prompt_author = to_checksum_address("0x" + log["topics"][2].hex()[-40:])
    start_token_id = int(log["topics"][3].hex(), 16)

    # Non-indexed parameters (data)
    # Each uint256 is 32 bytes (64 hex chars)
    data = log["data"].hex()[2:]  # Remove "0x" prefix
    quantity = int(data[0:64], 16)      # First 32 bytes
    total_paid = int(data[64:128], 16)  # Second 32 bytes

    return {
        "minter": minter,
        "prompt_author": prompt_author,
        "start_token_id": start_token_id,
        "quantity": quantity,
        "total_paid": total_paid,
        "tx_hash": log["transactionHash"].hex(),
        "block_number": log["blockNumber"],
        "log_index": log["logIndex"]
    }
```

**ABI-Based Decoding (Alternative)**:

```python
from web3 import Web3

# Define event ABI
BATCH_MINTED_ABI = {
    "anonymous": False,
    "inputs": [
        {"indexed": True, "name": "minter", "type": "address"},
        {"indexed": True, "name": "promptAuthor", "type": "address"},
        {"indexed": True, "name": "startTokenId", "type": "uint256"},
        {"indexed": False, "name": "quantity", "type": "uint256"},
        {"indexed": False, "name": "totalPaid", "type": "uint256"}
    ],
    "name": "BatchMinted",
    "type": "event"
}

def decode_with_abi(w3: Web3, log: dict) -> dict:
    """
    Decode event log using web3.py's built-in ABI decoder.
    """
    from web3._utils.events import get_event_data
    from web3._utils.abi import get_abi_output_types

    # Use web3's event data decoder
    event_data = get_event_data(w3.codec, BATCH_MINTED_ABI, log)

    return {
        "minter": event_data["args"]["minter"],
        "prompt_author": event_data["args"]["promptAuthor"],
        "start_token_id": event_data["args"]["startTokenId"],
        "quantity": event_data["args"]["quantity"],
        "total_paid": event_data["args"]["totalPaid"],
        "tx_hash": event_data["transactionHash"].hex(),
        "block_number": event_data["blockNumber"],
        "log_index": event_data["logIndex"]
    }
```

**Decision**: Use **manual decoding** for BatchMinted event.

**Rationale**:
- Event structure is fixed and simple (5 parameters)
- No dynamic types (arrays, strings) that complicate manual parsing
- Avoids ABI file dependency and maintenance
- More explicit and easier to debug
- Faster execution (no ABI lookup overhead)
- Keep it simple per project philosophy (defer abstraction until 80+ lines)

### Important Parsing Notes

**Hex Encoding**:
- All blockchain data is hex-encoded
- Addresses are 40 hex chars (20 bytes), topics store them as 64 hex chars (32 bytes, left-padded)
- Extract address from last 40 chars: `"0x" + topic.hex()[-40:]`
- `uint256` values are full 64 hex chars (32 bytes)

**Type Conversions**:
- Hex to int: `int(hex_string, 16)`
- Hex to address: `to_checksum_address("0x" + hex_string[-40:])`
- Always use checksummed addresses for database storage

**Edge Cases**:
- `removed: true` indicates log was removed due to chain reorg (filter these out)
- Transaction status: Only process logs from successful transactions (status == 1)
- Multiple events per transaction: Use `log_index` to distinguish

---

## 5. Alchemy Best Practices

### Official Resources
- **Webhooks FAQ**: https://www.alchemy.com/docs/reference/notify-api-faq
- **Deep Dive into eth_getLogs**: https://www.alchemy.com/docs/deep-dive-into-eth_getlogs

### Webhook Reliability

**Duplicate Event Handling**:
- Alchemy retries webhooks on non-200 responses or timeouts
- Most common cause: Slow endpoint response (>30s timeout)
- **Idempotency key**: Use `webhookId + sequenceNumber` (Alchemy's recommendation)
- Alternative: Use `tx_hash + log_index` (blockchain-level uniqueness)

**Deduplication Strategy**:
```python
# Option 1: Alchemy's idempotency keys
idempotency_key = f"{payload['webhookId']}:{payload.get('sequenceNumber', 0)}"

# Option 2: Blockchain-level uniqueness (RECOMMENDED)
# UNIQUE constraint on mint_events(tx_hash, log_index)
# Database handles deduplication automatically
# Return 409 Conflict if duplicate INSERT fails
```

**Decision**: Use **database UNIQUE constraint** on `(tx_hash, log_index)`.

**Rationale**:
- Blockchain-level uniqueness is more reliable than Alchemy metadata
- Works even if webhook system changes or events come from recovery
- Simpler application logic (database enforces constraint)
- Aligns with DDD philosophy: let infrastructure handle infrastructure concerns
- `sequenceNumber` may not be present in all webhook versions

### Idempotency Implementation

**HTTP Response Codes**:
```python
# Success - event processed
return 200 OK

# Duplicate - event already exists
return 409 Conflict

# Invalid signature
return 401 Unauthorized

# Malformed payload
return 400 Bad Request

# Temporary failure - Alchemy will retry
return 500 Internal Server Error

# Async processing accepted
return 202 Accepted
```

**Processing Time Limits**:
- Alchemy webhook timeout: ~30 seconds
- Target response time: <500ms (per success criteria)
- If processing takes >3s, return 202 Accepted and process async
- For MVP (detection only), synchronous processing is sufficient

**Transaction Handling**:
```python
async def process_webhook(payload: dict, db: AsyncSession):
    """
    Process webhook with proper transaction handling.
    """
    async with db.begin():
        # All operations in single transaction
        # Rollback on any failure (Alchemy retries)
        # Commit only on full success
        mint_event = create_mint_event(payload)
        token = create_token(payload)
        db.add(mint_event)
        db.add(token)
    # Auto-commit on context exit
```

### Error Handling

**Network Failures** (eth_getLogs):
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def fetch_logs_with_retry(w3: Web3, filter_params: dict):
    """
    Retry eth_getLogs with exponential backoff.
    """
    return w3.eth.get_logs(filter_params)
```

**Chain Reorganizations**:
- Events with `removed: true` indicate chain reorg
- Filter out removed events before processing
- For deep reorgs (>10 blocks), consider recovery from checkpoint
- Production monitoring: Alert on frequent reorgs

**Event Ordering**:
- Events from same block may arrive out of order
- Sort by `(block_number, log_index)` if order matters
- For BatchMinted events, each is independent (order doesn't matter for detection)

### Monitoring and Observability

**Key Metrics**:
- Webhook response time (target: <500ms)
- Duplicate event rate (should be low after retry convergence)
- Signature validation failures (should be zero in production)
- Recovery lag (blocks behind chain head)

**Logging**:
```python
import structlog

logger = structlog.get_logger()

# Webhook received
logger.info(
    "webhook.received",
    webhook_id=payload["webhookId"],
    event_id=payload["id"],
    tx_hash=tx_hash
)

# Duplicate detected
logger.warning(
    "webhook.duplicate",
    tx_hash=tx_hash,
    log_index=log_index
)

# Event stored
logger.info(
    "event.stored",
    tx_hash=tx_hash,
    token_id=token_id,
    author=author_wallet
)
```

**Health Checks**:
- Expose `/health` endpoint for uptime monitoring
- Check database connectivity
- Optionally check Alchemy API reachability
- Monitor last processed block timestamp (detect staleness)

---

## 6. Implementation Decisions Summary

### Technology Choices

| Component | Decision | Rationale |
|-----------|----------|-----------|
| Webhook Type | Custom (GraphQL) | Better filtering, future extensibility |
| Signature Validation | HMAC-SHA256 with `hmac.compare_digest()` | Constant-time comparison prevents timing attacks |
| RPC Library | `web3.py` | Mature, well-documented, production-ready |
| Event Decoding | Manual parsing | Simple event structure, no ABI dependency |
| Idempotency | DB UNIQUE constraint on `(tx_hash, log_index)` | Blockchain-level uniqueness, simpler logic |
| Pagination | Adaptive chunking (1000 blocks default) | Balance reliability and performance |

### Configuration Values

```python
# .env additions
ALCHEMY_API_KEY=your_api_key_here
ALCHEMY_WEBHOOK_SECRET=your_signing_key_here  # Per-webhook secret
GLISK_NFT_CONTRACT_ADDRESS=0x...  # Checksummed address
NETWORK=BASE_SEPOLIA  # or BASE_MAINNET
GLISK_DEFAULT_AUTHOR_WALLET=0x...  # Fallback for unknown authors

# Derived values
ALCHEMY_RPC_URL=https://base-sepolia.g.alchemy.com/v2/{ALCHEMY_API_KEY}
```

### Event Signature Reference

```python
# Calculate at runtime (no hardcoding)
from web3 import Web3

BATCH_MINTED_SIGNATURE = Web3.keccak(
    text="BatchMinted(address,address,uint256,uint256,uint256)"
).hex()

# Expected result: 0x...  (store in constant for reference)
```

### Security Checklist

- [ ] Validate HMAC signature on ALL webhook requests
- [ ] Use `hmac.compare_digest()` for constant-time comparison
- [ ] Never log or expose webhook signing key
- [ ] Filter events by contract address (ignore other contracts)
- [ ] Verify transaction status == 1 (only successful transactions)
- [ ] Filter out removed events (`removed: true` from reorgs)
- [ ] Return 401 Unauthorized for invalid signatures (no processing)
- [ ] Use database transactions for atomic event + token creation
- [ ] Implement rate limiting on webhook endpoint (prevent DoS)

### Testing Strategy

**Unit Tests**:
- Signature validation (valid, invalid, missing)
- Event decoding (all parameter types)
- Hex conversions (addresses, uint256)

**Integration Tests**:
- Complete webhook flow (signature → parse → store)
- Duplicate event handling (409 Conflict)
- Database transaction rollback on errors
- Recovery mechanism (eth_getLogs → store → state update)

**Testnet Testing**:
- Deploy contract to Base Sepolia
- Configure Alchemy webhook to ngrok URL
- Mint test NFTs and verify detection
- Test recovery CLI on historical blocks

---

## 7. References

### Official Alchemy Documentation
- Notify API Quickstart: https://www.alchemy.com/docs/reference/notify-api-quickstart
- Custom Webhooks: https://www.alchemy.com/docs/reference/custom-webhook
- NFT Activity Webhook: https://www.alchemy.com/docs/reference/nft-activity-webhook
- eth_getLogs Deep Dive: https://www.alchemy.com/docs/deep-dive-into-eth_getlogs
- eth_getLogs Reference: https://docs.alchemy.com/reference/eth-getlogs
- Compute Units: https://www.alchemy.com/docs/reference/compute-units

### web3.py Documentation
- Events and Logs: https://web3py.readthedocs.io/en/stable/filters.html
- Contracts: https://web3py.readthedocs.io/en/stable/web3.contract.html

### Python Standard Library
- hmac module: https://docs.python.org/3/library/hmac.html
- hashlib module: https://docs.python.org/3/library/hashlib.html

### Security Resources
- HMAC-SHA256 in Python: https://ssojet.com/hashing/hmac-sha256-in-python/
- Constant-Time Comparison: https://securitypitfalls.wordpress.com/2018/08/03/constant-time-compare-in-python/
- Webhook Security (GitHub): https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries

### Best Practices
- Webhook Idempotency: https://hookdeck.com/webhooks/guides/implement-webhook-idempotency
- Webhooks at Scale: https://hookdeck.com/blog/webhooks-at-scale
- Ethereum Event Logs (Linum Labs): https://www.linumlabs.com/articles/everything-you-ever-wanted-to-know-about-events-and-logs-on-ethereum

---

## 8. Open Questions / Future Research

1. **GraphQL Webhook Configuration**: Need to confirm exact GraphQL query syntax for filtering BatchMinted events in Alchemy dashboard
2. **Webhook Replay**: Does Alchemy provide webhook replay functionality for debugging? (Alternative: use recovery CLI)
3. **Multi-contract Scaling**: If supporting multiple NFT contracts in future, consider event parser abstraction at that point
4. **WebSocket Subscriptions**: For ultra-low latency, could replace webhooks with WebSocket subscriptions (defer until latency requirements tighten)
5. **Rate Limit Monitoring**: Implement Alchemy API usage tracking to avoid surprise rate limit hits

---

**Document Version**: 1.0
**Last Updated**: 2025-10-17
**Status**: Ready for Implementation
