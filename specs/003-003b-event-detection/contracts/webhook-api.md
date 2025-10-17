# Webhook API Contract

**Feature**: 003-003b-event-detection
**Created**: 2025-10-17
**Type**: HTTP REST API

## Overview

This document defines the HTTP contract for the Alchemy webhook endpoint that receives NFT mint event notifications.

---

## Endpoint: Receive Alchemy Webhook

### Request

```
POST /webhooks/alchemy
Content-Type: application/json
X-Alchemy-Signature: <hmac-sha256-hex-signature>
```

**Headers**:
- `Content-Type`: `application/json` (required)
- `X-Alchemy-Signature`: HMAC-SHA256 hex signature of request body (required)

**Body** (Alchemy Custom Webhook format):

```json
{
  "webhookId": "wh_abc123xyz",
  "id": "whevt_unique_event_id_for_dedup",
  "createdAt": "2025-10-17T00:30:00.123Z",
  "type": "CUSTOM",
  "event": {
    "network": "BASE_SEPOLIA",
    "data": {
      "block": {
        "number": 12345678,
        "hash": "0xblockhash...",
        "timestamp": 1697500000,
        "logs": [
          {
            "address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
            "topics": [
              "0xeventSignature...",
              "0x000000000000000000000000minterAddress",
              "0x000000000000000000000000promptAuthorAddress",
              "0x0000000000000000000000000000000000000000000000000000000000000001"
            ],
            "data": "0x00000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000000",
            "blockNumber": "0xbc614e",
            "transactionHash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            "transactionIndex": "0x5",
            "blockHash": "0xblockhash...",
            "logIndex": "0x0",
            "removed": false
          }
        ]
      },
      "transaction": {
        "hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        "from": "0x1234567890123456789012345678901234567890",
        "to": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
        "status": 1
      }
    }
  }
}
```

**Event Log Structure** (within `event.data.block.logs[]`):
- `address` (string) - Contract address (checksummed)
- `topics` (string[]) - Indexed event parameters:
  - `topics[0]`: Event signature hash
  - `topics[1]`: Minter address (indexed)
  - `topics[2]`: Prompt author address (indexed)
  - `topics[3]`: Start token ID (indexed)
- `data` (string) - ABI-encoded non-indexed parameters (quantity, totalPaid)
- `blockNumber` (string) - Block number (hex)
- `transactionHash` (string) - Transaction hash
- `logIndex` (string) - Log index (hex)
- `removed` (boolean) - Chain reorg indicator

**Validation Requirements**:
1. `X-Alchemy-Signature` must match HMAC-SHA256(signing_key, raw_body)
2. `event.data.block.logs[].removed` must be `false`
3. `event.data.transaction.status` must be `1` (success)
4. `event.data.block.logs[].address` must match configured `GLISK_NFT_CONTRACT_ADDRESS`
5. `event.data.block.logs[].topics[0]` must match BatchMinted event signature

---

### Response: Success (New Event)

```
HTTP/1.1 200 OK
Content-Type: application/json
```

```json
{
  "status": "success",
  "message": "Event processed successfully",
  "mint_event_id": "550e8400-e29b-41d4-a716-446655440000",
  "token_id": 1
}
```

**When**: Event was successfully parsed, validated, and stored in database.

---

### Response: Duplicate Event (Idempotent)

```
HTTP/1.1 409 Conflict
Content-Type: application/json
```

```json
{
  "status": "duplicate",
  "message": "Event already processed",
  "tx_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
  "log_index": 0
}
```

**When**: Event with same `(tx_hash, log_index)` already exists in `mint_events` table.

**Behavior**: No database modification, no error logged. Alchemy should treat as success.

---

### Response: Invalid Signature

```
HTTP/1.1 401 Unauthorized
Content-Type: application/json
```

```json
{
  "status": "error",
  "message": "Invalid webhook signature",
  "code": "INVALID_SIGNATURE"
}
```

**When**: `X-Alchemy-Signature` header is missing or does not match computed HMAC-SHA256.

**Behavior**: Request rejected before any processing. Alchemy should NOT retry (authentication failure).

---

### Response: Malformed Payload

```
HTTP/1.1 400 Bad Request
Content-Type: application/json
```

```json
{
  "status": "error",
  "message": "Invalid webhook payload: missing field 'event.data.block.logs'",
  "code": "INVALID_PAYLOAD"
}
```

**When**: JSON parsing fails, required fields missing, or data types incorrect.

**Behavior**: Request rejected. Alchemy should NOT retry (client error).

---

### Response: Server Error (Temporary)

```
HTTP/1.1 500 Internal Server Error
Content-Type: application/json
```

```json
{
  "status": "error",
  "message": "Database connection failed",
  "code": "INTERNAL_ERROR"
}
```

**When**: Database unavailable, unexpected exceptions, or transaction rollback.

**Behavior**: Alchemy SHOULD retry with exponential backoff (temporary failure).

---

### Response: Async Processing (Long-Running)

```
HTTP/1.1 202 Accepted
Content-Type: application/json
```

```json
{
  "status": "accepted",
  "message": "Event queued for processing",
  "event_id": "whevt_unique_event_id_for_dedup"
}
```

**When**: Processing will take >3 seconds (webhook timeout threshold).

**Behavior**: Return immediately, process asynchronously. **NOT IMPLEMENTED IN MVP** - deferred until throughput issues arise.

---

## Security

### HMAC Signature Validation

**Algorithm**: HMAC-SHA256

**Implementation**:
```python
import hmac
import hashlib

def validate_signature(raw_body: bytes, signature: str, signing_key: str) -> bool:
    expected = hmac.new(
        key=signing_key.encode('utf-8'),
        msg=raw_body,
        digestmod=hashlib.sha256
    ).hexdigest()

    # MUST use constant-time comparison to prevent timing attacks
    return hmac.compare_digest(expected, signature)
```

**Critical Requirements**:
- Use raw request body bytes (NOT JSON-parsed object)
- Use `hmac.compare_digest()` for constant-time comparison
- Validate BEFORE any processing logic
- Return 401 immediately on failure

---

## Event Filtering

**Contract Address Filter**:
- Only process logs where `log.address == GLISK_NFT_CONTRACT_ADDRESS` (case-insensitive)

**Event Signature Filter**:
- Only process logs where `log.topics[0] == keccak256("BatchMinted(address,address,uint256,uint256,uint256)")`

**Transaction Status Filter**:
- Only process logs where `transaction.status == 1` (successful)

**Chain Reorg Filter**:
- Skip logs where `log.removed == true`

---

## Error Handling

### Client Errors (4xx) - Do NOT Retry

- `400 Bad Request` - Malformed JSON, missing fields, invalid data types
- `401 Unauthorized` - Invalid signature
- `409 Conflict` - Duplicate event (idempotent, treat as success)

### Server Errors (5xx) - Retry with Backoff

- `500 Internal Server Error` - Database connection failures, unexpected exceptions
- `502 Bad Gateway` - Upstream service unavailable (rare)
- `503 Service Unavailable` - Server overloaded or maintenance mode

### Alchemy Retry Policy

Alchemy automatically retries 5xx errors with exponential backoff:
- Retry 1: +1 second
- Retry 2: +2 seconds
- Retry 3: +4 seconds
- Retry 4: +8 seconds
- Retry 5: +16 seconds

After 5 retries, Alchemy marks webhook as failed.

---

## Performance

**Target Latency**: <500ms (p95)

**Breakdown**:
- Signature validation: <5ms
- JSON parsing: <10ms
- Event parsing: <10ms
- Database transaction (INSERT mint_event + token): <100ms
- Response serialization: <5ms

**Timeout**: 3 seconds (Alchemy webhook timeout)

**Throughput**: 100 events/minute (MVP target, no queue system yet)

---

## Example: Complete Request/Response Flow

### Successful Processing

**Request**:
```http
POST /webhooks/alchemy HTTP/1.1
Host: api.glisk.com
Content-Type: application/json
X-Alchemy-Signature: a1b2c3d4e5f6...

{
  "webhookId": "wh_abc123",
  "id": "whevt_001",
  "createdAt": "2025-10-17T00:30:00.123Z",
  "type": "CUSTOM",
  "event": {
    "network": "BASE_SEPOLIA",
    "data": {
      "block": {
        "number": 12345678,
        "logs": [
          {
            "address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
            "topics": [
              "0x...",
              "0x000000000000000000000000A1b2c3d4...",
              "0x000000000000000000000000B2c3d4e5...",
              "0x0000000000000000000000000000000000000000000000000000000000000001"
            ],
            "data": "0x0000000000000000000000000000000000000000000000000000000000000001...",
            "blockNumber": "0xbc614e",
            "transactionHash": "0x1234...",
            "logIndex": "0x0",
            "removed": false
          }
        ]
      },
      "transaction": {
        "hash": "0x1234...",
        "status": 1
      }
    }
  }
}
```

**Response**:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "success",
  "message": "Event processed successfully",
  "mint_event_id": "550e8400-e29b-41d4-a716-446655440000",
  "token_id": 1
}
```

---

## Testing Endpoints

### Local Development (ngrok)

```bash
# Start ngrok tunnel
ngrok http 8000

# Configure Alchemy webhook to point to:
https://your-ngrok-url.ngrok.io/webhooks/alchemy
```

### Manual Testing (curl)

```bash
# Generate valid signature
BODY='{"webhookId":"test","id":"test001","createdAt":"2025-10-17T00:30:00.123Z",...}'
SIGNATURE=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "$ALCHEMY_WEBHOOK_SECRET" | awk '{print $2}')

# Send test request
curl -X POST http://localhost:8000/webhooks/alchemy \
  -H "Content-Type: application/json" \
  -H "X-Alchemy-Signature: $SIGNATURE" \
  -d "$BODY"
```

---

## Configuration

**Environment Variables**:
```bash
ALCHEMY_WEBHOOK_SECRET=your_signing_key_from_alchemy_dashboard
GLISK_NFT_CONTRACT_ADDRESS=0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0
```

**Alchemy Dashboard Setup**:
1. Navigate to Webhooks → Custom Webhooks
2. Create new webhook with filters:
   - Network: Base Sepolia (or Base Mainnet)
   - Contract Address: `0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0`
   - Event Signature: `BatchMinted(address,address,uint256,uint256,uint256)`
3. Set webhook URL: `https://api.glisk.com/webhooks/alchemy`
4. Copy signing key to `ALCHEMY_WEBHOOK_SECRET`

---

## Future Enhancements (Out of Scope)

- **Webhook tracking table**: Store webhook metadata for debugging (deferred unless reliability issues)
- **Async processing queue**: Background job queue for long-running operations (deferred until throughput issues)
- **Webhook retry tracking**: Custom retry logic beyond Alchemy's built-in retries (deferred)
- **Multi-contract support**: Handle events from multiple contracts (deferred)
- **Webhook authentication tokens**: Additional auth layer beyond HMAC (deferred)
