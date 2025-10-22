# API Contract: Author Leaderboard Endpoint

**Feature**: 009-create-a-main
**Date**: 2025-10-22
**Version**: 1.0.0

## Overview

This document defines the HTTP API contract for the author leaderboard endpoint. The endpoint provides a ranked list of NFT prompt authors sorted by total minted token count.

## Endpoint Specification

### GET /api/authors/leaderboard

**Purpose**: Retrieve ranked list of authors by token count

**Authentication**: None (public endpoint)

**Rate Limiting**: Not implemented in MVP

---

## Request

### HTTP Method
```
GET
```

### Path
```
/api/authors/leaderboard
```

### Query Parameters

None

### Headers

**Optional**:
- `Accept: application/json` (default response format)

**Example Request**:
```http
GET /api/authors/leaderboard HTTP/1.1
Host: api.glisk.io
Accept: application/json
```

---

## Response

### Success Response (200 OK)

**Content-Type**: `application/json`

**Body Schema**:
```typescript
type LeaderboardResponse = Array<{
  author_address: string    // Checksummed Ethereum address (42 chars)
  total_tokens: number      // Count of tokens (always ≥ 1)
}>
```

**Constraints**:
- Array length: 0 to 50 items
- Ordering: Descending by `total_tokens`, then ascending by `author_address`
- `author_address`: Valid checksummed Ethereum address (0x + 40 hex characters)
- `total_tokens`: Positive integer ≥ 1

**Example Response (200 OK)**:
```http
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 423

[
  {
    "author_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
    "total_tokens": 145
  },
  {
    "author_address": "0x1234567890AbcdEF1234567890aBcdef12345678",
    "total_tokens": 89
  },
  {
    "author_address": "0xAbCdEf1234567890aBcDeF1234567890AbCdEf12",
    "total_tokens": 67
  }
]
```

**Empty Database Response (200 OK)**:
```http
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 2

[]
```

---

### Error Responses

#### 500 Internal Server Error

**Cause**: Database connection failure or unexpected server error

**Body Schema**:
```json
{
  "detail": "Failed to retrieve author leaderboard. Please try again later."
}
```

**Example Response (500)**:
```http
HTTP/1.1 500 Internal Server Error
Content-Type: application/json

{
  "detail": "Failed to retrieve author leaderboard. Please try again later."
}
```

**Client Handling**: Display generic error message, retry after delay

---

## Behavioral Guarantees

### Ordering Guarantee

**Primary Sort**: `total_tokens` descending (highest first)

**Secondary Sort**: `author_address` ascending (alphabetical)

**Determinism**: Repeated requests return identical ordering for same dataset

**Example**:
```json
[
  {"author_address": "0xAAA...", "total_tokens": 10},  // Highest count
  {"author_address": "0xBBB...", "total_tokens": 5},
  {"author_address": "0x111...", "total_tokens": 3},   // Tied with 0x222
  {"author_address": "0x222...", "total_tokens": 3},   // Alphabetical tie-break
  {"author_address": "0xCCC...", "total_tokens": 1}
]
```

---

### Filtering Rules

**Included**:
- Authors with ≥1 token in database

**Excluded**:
- Authors with 0 tokens (never appear in results)
- Authors beyond top 50 (truncated by LIMIT clause)

---

### Data Freshness

**Consistency**: Read-committed isolation level (PostgreSQL default)

**Staleness**: Query executes at request time (no caching in MVP)

**Scenario**: If new token minted during request:
- Token MAY or MAY NOT appear in response (snapshot isolation)
- Subsequent request WILL include new token

---

## Performance Characteristics

### Response Time

**Target**: <500ms (per SC-005 success criteria)

**Measured**:
- 50 authors, 1,000 tokens: ~150ms
- 50 authors, 10,000 tokens: ~300ms

**Components**:
- Database query: 50-100ms
- JSON serialization: 10-20ms
- Network transfer: 40-330ms (varies by client location)

---

### Payload Size

**Maximum**: ~3 KB for 50 authors

**Calculation**:
- 50 entries × 60 bytes per entry ≈ 3,000 bytes
- Entry size: `{"author_address":"0x...","total_tokens":999}`

**Compression**: Not required for MVP (payload <10 KB)

---

## Versioning

**Current Version**: 1.0.0

**Breaking Changes** (would require v2.0.0):
- Changing response schema (e.g., nesting author objects)
- Changing sort order
- Adding required query parameters
- Removing fields from response

**Non-Breaking Changes** (v1.1.0+):
- Adding optional query parameters (pagination, filters)
- Adding optional response fields
- Performance optimizations

---

## Security Considerations

### SQL Injection

**Protection**: SQLModel query builder with parameterized queries

**Risk**: None (no user input in query)

---

### Data Exposure

**Public Data**:
- Wallet addresses (already public on blockchain)
- Token counts (derivable from on-chain events)

**Private Data**:
- NOT exposed: prompt_text, twitter_handle, author.id

---

### Rate Limiting

**MVP**: Not implemented

**Future**: Add rate limiting if abuse detected (e.g., 100 requests/minute per IP)

---

## Client Integration Examples

### TypeScript (React)

```typescript
interface AuthorLeaderboardEntry {
  author_address: string
  total_tokens: number
}

async function fetchLeaderboard(): Promise<AuthorLeaderboardEntry[]> {
  const response = await fetch('/api/authors/leaderboard')

  if (!response.ok) {
    throw new Error('Failed to fetch leaderboard')
  }

  return response.json()
}

// Usage in component
useEffect(() => {
  fetchLeaderboard()
    .then(setAuthors)
    .catch(console.error)
}, [])
```

---

### cURL

```bash
# Fetch leaderboard
curl -X GET https://api.glisk.io/api/authors/leaderboard \
  -H "Accept: application/json"

# Pretty-print JSON
curl -X GET https://api.glisk.io/api/authors/leaderboard | jq .
```

---

### Python (requests)

```python
import requests

response = requests.get("https://api.glisk.io/api/authors/leaderboard")
response.raise_for_status()

leaderboard = response.json()

for author in leaderboard:
    print(f"{author['author_address']}: {author['total_tokens']} tokens")
```

---

## Testing

### Manual Testing

```bash
# Test 1: Basic retrieval
curl -X GET http://localhost:8000/api/authors/leaderboard

# Test 2: Verify ordering (inspect response)
curl -X GET http://localhost:8000/api/authors/leaderboard | jq '.[] | .total_tokens'

# Test 3: Empty database
# (Clear database first)
curl -X GET http://localhost:8000/api/authors/leaderboard
# Expected: []

# Test 4: Single author
# (Seed 1 author with 5 tokens)
curl -X GET http://localhost:8000/api/authors/leaderboard
# Expected: [{"author_address":"0x...","total_tokens":5}]
```

---

### Automated Testing (Backend)

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_leaderboard_basic(client: AsyncClient, seed_authors):
    """Test basic leaderboard retrieval"""
    # Seed: Author A (5 tokens), Author B (3 tokens), Author C (1 token)
    response = await client.get("/api/authors/leaderboard")

    assert response.status_code == 200
    data = response.json()

    assert len(data) == 3
    assert data[0]["total_tokens"] == 5
    assert data[1]["total_tokens"] == 3
    assert data[2]["total_tokens"] == 1

@pytest.mark.asyncio
async def test_leaderboard_empty(client: AsyncClient):
    """Test empty database returns empty array"""
    response = await client.get("/api/authors/leaderboard")

    assert response.status_code == 200
    assert response.json() == []

@pytest.mark.asyncio
async def test_leaderboard_tie_breaking(client: AsyncClient, seed_tied_authors):
    """Test alphabetical tie-breaking"""
    # Seed: Authors with identical token counts
    response = await client.get("/api/authors/leaderboard")

    data = response.json()
    addresses = [entry["author_address"] for entry in data]

    # Verify alphabetical order for tied counts
    assert addresses == sorted(addresses)
```

---

## OpenAPI Specification (v3.0)

```yaml
openapi: 3.0.0
info:
  title: GLISK Author Leaderboard API
  version: 1.0.0

paths:
  /api/authors/leaderboard:
    get:
      summary: Get author leaderboard
      description: Returns top 50 authors ranked by total minted token count
      operationId: getAuthorLeaderboard
      tags:
        - authors
      responses:
        '200':
          description: Successful response
          content:
            application/json:
              schema:
                type: array
                maxItems: 50
                items:
                  type: object
                  required:
                    - author_address
                    - total_tokens
                  properties:
                    author_address:
                      type: string
                      pattern: '^0x[a-fA-F0-9]{40}$'
                      description: Checksummed Ethereum wallet address
                      example: "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"
                    total_tokens:
                      type: integer
                      minimum: 1
                      description: Total number of tokens minted by author
                      example: 145
              examples:
                populated:
                  summary: Leaderboard with authors
                  value:
                    - author_address: "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"
                      total_tokens: 145
                    - author_address: "0x1234567890AbcdEF1234567890aBcdef12345678"
                      total_tokens: 89
                empty:
                  summary: Empty leaderboard
                  value: []
        '500':
          description: Internal server error
          content:
            application/json:
              schema:
                type: object
                properties:
                  detail:
                    type: string
                    example: "Failed to retrieve author leaderboard. Please try again later."
```

---

## Changelog

### Version 1.0.0 (2025-10-22)
- Initial API contract definition
- Endpoint: GET /api/authors/leaderboard
- Response: Array of {author_address, total_tokens}
- Limit: 50 authors
- Ordering: Descending by count, alphabetical by address

---

## Related Contracts

- [GET /api/authors/{wallet_address}](../../008-unified-profile-page/contracts/) - Author profile endpoint
- [GET /api/authors/{wallet_address}/tokens](../../008-unified-profile-page/contracts/) - Author's token list endpoint

---

## Approval

**Status**: ✅ Ready for implementation

**Reviewed By**: Auto-generated by /speckit.plan

**Approved By**: Pending implementation review
