# API Endpoints: Unified Profile Page

**Feature Branch**: `008-unified-profile-page`
**Date**: 2025-10-22

This document specifies the backend API contract for the new authored NFTs endpoint.

---

## Overview

This feature adds **one new GET endpoint** to the existing authors API routes. The endpoint returns paginated tokens authored by a wallet address.

**File**: `backend/src/glisk/api/routes/authors.py`

---

## New Endpoint

### GET /api/authors/{wallet_address}/tokens

Retrieve paginated list of tokens where the specified wallet address is the prompt author.

**Method**: `GET`
**Path**: `/api/authors/{wallet_address}/tokens`
**Authentication**: None (public read)
**Rate Limit**: None (MVP)

---

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `wallet_address` | String | Yes | Ethereum wallet address (0x + 40 hex chars, case-insensitive) |

**Validation**:
- Must be valid Ethereum address format (42 characters, 0x prefix)
- Automatically normalized to checksummed format (EIP-55)
- Invalid format returns 200 with empty results (not 400) for better UX

---

### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `offset` | Integer | No | `0` | Number of tokens to skip (for pagination) |
| `limit` | Integer | No | `20` | Maximum tokens to return per page |

**Validation**:
- `offset`: Must be >= 0 (returns 400 if negative)
- `limit`: Must be 1-100 (returns 400 if out of range)

**Pagination Formula**:
```
Page 1: offset=0,  limit=20  → tokens[0:20]
Page 2: offset=20, limit=20  → tokens[20:40]
Page N: offset=(N-1)*20, limit=20
```

---

### Response (Success)

**Status Code**: `200 OK`
**Content-Type**: `application/json`

```json
{
  "tokens": [
    {
      "token_id": 1,
      "status": "revealed",
      "image_cid": "QmXyz123...",
      "metadata_cid": "QmAbc456...",
      "image_url": "https://replicate.delivery/...",
      "generation_attempts": 1,
      "generation_error": null,
      "reveal_tx_hash": "0x1234567890abcdef...",
      "created_at": "2025-10-22T12:34:56Z"
    }
  ],
  "total": 45,
  "offset": 0,
  "limit": 20
}
```

---

### Response Fields

#### Root Object

| Field | Type | Description |
|-------|------|-------------|
| `tokens` | Array | List of token objects (ordered by created_at DESC) |
| `total` | Integer | Total number of tokens authored by this wallet (all pages) |
| `offset` | Integer | Echo of request offset (for client-side validation) |
| `limit` | Integer | Echo of request limit (for client-side validation) |

#### Token Object

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `token_id` | Integer | No | On-chain token ID (unique) |
| `status` | String (Enum) | No | Lifecycle status: "detected", "generating", "uploading", "ready", "revealed", "failed" |
| `image_cid` | String | Yes | IPFS CID for generated image (null until uploaded) |
| `metadata_cid` | String | Yes | IPFS CID for metadata JSON (null until uploaded) |
| `image_url` | String | Yes | Replicate URL for generated image (null if not generated or expired) |
| `generation_attempts` | Integer | No | Number of image generation attempts (0-3) |
| `generation_error` | String | Yes | Error message if generation failed (null if successful or not attempted) |
| `reveal_tx_hash` | String | Yes | Transaction hash for reveal (null until revealed on-chain) |
| `created_at` | String (ISO 8601) | No | Timestamp when token was detected (UTC) |

**Status Enum Values**:
- `detected`: Token minted, awaiting image generation
- `generating`: Image generation in progress
- `uploading`: Generated image being uploaded to IPFS
- `ready`: Uploaded to IPFS, awaiting on-chain reveal
- `revealed`: Metadata revealed on-chain (terminal state)
- `failed`: Permanent failure (terminal state)

---

### Response (Empty Results)

**Case 1: Author has no tokens**

```json
{
  "tokens": [],
  "total": 0,
  "offset": 0,
  "limit": 20
}
```

**Case 2: Author doesn't exist**

Same as Case 1 (not a 404 error - better UX)

**Case 3: Offset exceeds total**

```json
{
  "tokens": [],
  "total": 45,
  "offset": 60,
  "limit": 20
}
```

---

### Response (Error)

#### 400 Bad Request

**Cause**: Invalid query parameters

```json
{
  "detail": "Offset must be >= 0"
}
```

**Examples**:
- `offset=-1` → `"Offset must be >= 0"`
- `limit=0` → `"Limit must be between 1 and 100"`
- `limit=200` → `"Limit must be between 1 and 100"`

**Note**: Invalid wallet address format does NOT return 400 (returns empty results for better UX)

---

#### 500 Internal Server Error

**Cause**: Database connection failure or unexpected error

```json
{
  "detail": "Failed to retrieve tokens. Please try again later."
}
```

**Structured Logs** (backend only):
```json
{
  "event": "unexpected_error_getting_tokens",
  "wallet_address": "0x742d35Cc...",
  "error": "Connection timeout",
  "error_type": "DatabaseConnectionError"
}
```

---

## Implementation Details

### Repository Method

**File**: `backend/src/glisk/repositories/token.py`

```python
async def get_tokens_by_author_paginated(
    self,
    author_id: UUID,
    offset: int = 0,
    limit: int = 20
) -> tuple[list[Token], int]:
    """Get paginated tokens for author with total count.

    Args:
        author_id: UUID of author from authors table
        offset: Number of tokens to skip (default 0)
        limit: Maximum tokens to return (default 20)

    Returns:
        Tuple of (token list, total count)

    Raises:
        ValueError: If offset < 0 or limit not in 1-100 range
    """
    # Validation
    if offset < 0:
        raise ValueError("Offset must be >= 0")
    if limit < 1 or limit > 100:
        raise ValueError("Limit must be between 1 and 100")

    # Count query (total for pagination metadata)
    count_stmt = select(func.count(Token.id)).where(Token.author_id == author_id)
    total = await self.session.scalar(count_stmt)

    # Data query (paginated results)
    stmt = (
        select(Token)
        .where(Token.author_id == author_id)
        .order_by(Token.created_at.desc())  # Newest first
        .offset(offset)
        .limit(limit)
    )
    result = await self.session.execute(stmt)
    tokens = result.scalars().all()

    return (list(tokens), total or 0)
```

---

### API Route Handler

**File**: `backend/src/glisk/api/routes/authors.py`

```python
from fastapi import Query

class TokensResponse(BaseModel):
    """Response model for paginated tokens endpoint."""
    tokens: list[TokenDTO]
    total: int
    offset: int
    limit: int

class TokenDTO(BaseModel):
    """Data transfer object for token information."""
    token_id: int
    status: str  # TokenStatus enum value
    image_cid: str | None
    metadata_cid: str | None
    image_url: str | None
    generation_attempts: int
    generation_error: str | None
    reveal_tx_hash: str | None
    created_at: datetime

@router.get(
    "/{wallet_address}/tokens",
    response_model=TokensResponse,
    status_code=status.HTTP_200_OK
)
async def get_author_tokens(
    wallet_address: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    uow_factory=Depends(get_uow_factory),
) -> TokensResponse:
    """Get paginated tokens authored by wallet address.

    Returns empty list if author doesn't exist (not 404).
    """
    try:
        # Normalize wallet address
        try:
            checksummed_address = Web3.to_checksum_address(wallet_address)
        except ValueError:
            # Invalid address format - return empty results (not 400)
            logger.warning("invalid_wallet_format", wallet=wallet_address)
            return TokensResponse(tokens=[], total=0, offset=offset, limit=limit)

        async with await uow_factory() as uow:
            # Get author by wallet
            author = await uow.authors.get_by_wallet(checksummed_address)

            if author is None:
                # Author doesn't exist - return empty results (not 404)
                logger.debug("author_not_found", wallet=checksummed_address)
                return TokensResponse(tokens=[], total=0, offset=offset, limit=limit)

            # Get paginated tokens
            tokens, total = await uow.tokens.get_tokens_by_author_paginated(
                author_id=author.id,
                offset=offset,
                limit=limit
            )

            # Convert to DTOs
            token_dtos = [
                TokenDTO(
                    token_id=token.token_id,
                    status=token.status.value,  # Enum to string
                    image_cid=token.image_cid,
                    metadata_cid=token.metadata_cid,
                    image_url=token.image_url,
                    generation_attempts=token.generation_attempts,
                    generation_error=token.generation_error,
                    reveal_tx_hash=token.reveal_tx_hash,
                    created_at=token.created_at,
                )
                for token in tokens
            ]

            logger.info(
                "tokens_retrieved",
                wallet=checksummed_address,
                total=total,
                offset=offset,
                limit=limit,
            )

            return TokensResponse(
                tokens=token_dtos,
                total=total,
                offset=offset,
                limit=limit,
            )

    except ValueError as e:
        # Validation error from repository (offset/limit)
        logger.warning("validation_error", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(
            "unexpected_error_getting_tokens",
            wallet=wallet_address,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve tokens. Please try again later."
        )
```

---

## Usage Examples

### Frontend Fetch (TypeScript)

```typescript
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

interface TokensResponse {
  tokens: {
    token_id: number;
    status: string;
    image_cid: string | null;
    metadata_cid: string | null;
    image_url: string | null;
    generation_attempts: number;
    generation_error: string | null;
    reveal_tx_hash: string | null;
    created_at: string;
  }[];
  total: number;
  offset: number;
  limit: number;
}

async function fetchAuthoredTokens(
  walletAddress: string,
  page: number = 1
): Promise<TokensResponse> {
  const offset = (page - 1) * 20;
  const response = await fetch(
    `${API_BASE_URL}/api/authors/${walletAddress}/tokens?offset=${offset}&limit=20`
  );

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${await response.text()}`);
  }

  return response.json();
}

// Usage in React component
const { address } = useAccount();
const { data, error, isLoading } = useQuery({
  queryKey: ['authored-tokens', address, page],
  queryFn: () => fetchAuthoredTokens(address!, page),
  enabled: !!address,
});
```

---

### cURL Examples

**Get first page (default offset/limit)**:
```bash
curl -X GET "http://localhost:8000/api/authors/0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0/tokens"
```

**Get second page**:
```bash
curl -X GET "http://localhost:8000/api/authors/0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0/tokens?offset=20&limit=20"
```

**Get custom page size**:
```bash
curl -X GET "http://localhost:8000/api/authors/0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0/tokens?offset=0&limit=50"
```

**Invalid offset (400 error)**:
```bash
curl -X GET "http://localhost:8000/api/authors/0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0/tokens?offset=-1"
# Response: {"detail": "Offset must be >= 0"}
```

---

## Performance Characteristics

### Database Query Performance

**Indexes Used**:
- `author_id` foreign key index (existing)
- Consider adding composite index `(author_id, created_at DESC)` if queries slow

**Query Plan** (PostgreSQL EXPLAIN):
```sql
EXPLAIN SELECT * FROM tokens_s0
WHERE author_id = 'uuid-here'
ORDER BY created_at DESC
OFFSET 0 LIMIT 20;

-- Expected:
-- Index Scan using tokens_s0_author_id_idx
-- Sort: created_at DESC
-- Limit: 20
```

**Latency Expectations**:
- <50ms for authors with <100 tokens
- <100ms for authors with 1000 tokens
- <200ms for authors with 10,000 tokens (edge case)

---

### Caching Strategy (Future Enhancement)

Not implemented in MVP, but recommended for production:

```python
from fastapi_cache.decorator import cache

@router.get("/{wallet_address}/tokens")
@cache(expire=30)  # Cache for 30 seconds
async def get_author_tokens(...):
    # Implementation
```

**Rationale**: Tokens don't change frequently (only on new mints). 30s cache drastically reduces database load.

---

## Security Considerations

### No Sensitive Data Exposure

**Excluded fields** (not returned in response):
- `author.prompt_text` (write-only per 006-author-profile-management)
- `token.error_data` (internal debugging data)

**Included fields** (safe to expose):
- `image_cid`, `metadata_cid` (public IPFS data)
- `token_id` (public blockchain data)
- `status` (user-facing lifecycle state)
- `generation_error` (sanitized error messages only)

---

### Rate Limiting (Future Enhancement)

Not implemented in MVP. For production, consider:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.get("/{wallet_address}/tokens")
@limiter.limit("100/minute")  # 100 requests per minute per IP
async def get_author_tokens(...):
    # Implementation
```

---

## Testing Checklist

**Manual Testing** (per constitution - no automated tests for MVP):

- [ ] GET request returns 200 with tokens for existing author
- [ ] GET request returns 200 with empty array for non-existent author
- [ ] GET request returns 200 with empty array for invalid wallet format
- [ ] Pagination works correctly (offset=0, offset=20, offset=40)
- [ ] Total count matches actual token count in database
- [ ] Tokens ordered by created_at DESC (newest first)
- [ ] Offset >= total returns empty tokens array
- [ ] Limit=1 returns single token
- [ ] Limit=100 returns max 100 tokens
- [ ] Offset=-1 returns 400 error
- [ ] Limit=0 returns 400 error
- [ ] Limit=101 returns 400 error
- [ ] All token fields present in response (no nulls where unexpected)
- [ ] Status enum serialized as string ("revealed", not enum object)
- [ ] Timestamps in ISO 8601 format with UTC timezone

---

## Migration from Existing Endpoints

**No migration required**. This is a new endpoint with no deprecations.

**Related endpoints** (unchanged):
- `GET /api/authors/{wallet_address}` - Returns author status (has_prompt, twitter_handle)
- `POST /api/authors/prompt` - Create/update author prompt

---

## OpenAPI Schema

**Auto-generated** by FastAPI at `/docs` endpoint when server running:

```yaml
paths:
  /api/authors/{wallet_address}/tokens:
    get:
      summary: Get Author Tokens
      operationId: get_author_tokens
      parameters:
        - name: wallet_address
          in: path
          required: true
          schema:
            type: string
        - name: offset
          in: query
          required: false
          schema:
            type: integer
            default: 0
            minimum: 0
        - name: limit
          in: query
          required: false
          schema:
            type: integer
            default: 20
            minimum: 1
            maximum: 100
      responses:
        '200':
          description: Successful Response
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/TokensResponse'
        '400':
          description: Bad Request
        '500':
          description: Internal Server Error
```

Access via: `http://localhost:8000/docs` (Swagger UI)
