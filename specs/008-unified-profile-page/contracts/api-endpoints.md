# API Endpoints: Unified Profile Page

**Date**: 2025-10-22
**Feature**: [spec.md](../spec.md) | **Plan**: [plan.md](../plan.md)

## Overview

This document defines the REST API endpoint for retrieving authored NFTs. Uses standard OpenAPI-style documentation.

---

## GET /api/authors/{wallet_address}/tokens

Retrieve paginated list of NFTs where the specified wallet address is the prompt author.

### Path Parameters

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `wallet_address` | string | Yes | Ethereum wallet address (0x + 40 hex, case-insensitive) | `0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0` |

### Query Parameters

| Parameter | Type | Required | Default | Constraints | Description |
|-----------|------|----------|---------|-------------|-------------|
| `page` | integer | No | 1 | ≥ 1 | Page number (1-indexed) |
| `limit` | integer | No | 20 | 1-100 | Items per page |

### Request Example

```http
GET /api/authors/0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0/tokens?page=1&limit=20 HTTP/1.1
Host: localhost:8000
Accept: application/json
```

### Response (200 OK)

**Success - Author with tokens**:

```json
{
  "tokens": [
    {
      "token_id": 101,
      "status": "revealed",
      "image_url": "https://replicate.delivery/pbxt/abc123.png",
      "metadata_cid": "QmXoypizjW3WknFiJnKLwHCnL72vedxjQkDDP1mXWo6uco",
      "created_at": "2025-10-22T14:30:00Z"
    },
    {
      "token_id": 98,
      "status": "uploading",
      "image_url": "https://replicate.delivery/pbxt/def456.png",
      "metadata_cid": null,
      "created_at": "2025-10-22T13:15:00Z"
    }
  ],
  "total": 73,
  "page": 1,
  "limit": 20
}
```

**Success - Author with no tokens** (not 404):

```json
{
  "tokens": [],
  "total": 0,
  "page": 1,
  "limit": 20
}
```

**Response Schema**:

```typescript
interface AuthorTokensResponse {
  tokens: TokenResponse[];
  total: number;
  page: number;
  limit: number;
}

interface TokenResponse {
  token_id: number;
  status: TokenStatus;
  image_url?: string;
  metadata_cid?: string;
  created_at: string;  // ISO 8601 UTC timestamp
}

type TokenStatus = 'detected' | 'generating' | 'uploading' | 'ready' | 'revealed' | 'failed';
```

### Error Responses

**400 Bad Request** - Invalid wallet address format:

```json
{
  "detail": "Invalid Ethereum address format. Address must be 0x followed by 40 hexadecimal characters."
}
```

**422 Validation Error** - Invalid query parameters:

```json
{
  "detail": [
    {
      "loc": ["query", "page"],
      "msg": "ensure this value is greater than or equal to 1",
      "type": "value_error.number.not_ge"
    }
  ]
}
```

**500 Internal Server Error** - Database or unexpected error:

```json
{
  "detail": "Failed to retrieve tokens. Please try again later."
}
```

### Behavior Notes

1. **Case-Insensitive Address**: Input wallet address is normalized to checksummed format via `Web3.to_checksum_address()`. Both lowercase and checksummed addresses accepted.

2. **Author Not Found**: Returns empty `tokens` array with `total: 0` (not 404). This allows frontend to distinguish "no authored NFTs yet" from "invalid address".

3. **Pagination Bounds**: If `page` exceeds available pages, returns empty `tokens` array (total remains accurate).

4. **Ordering**: Tokens sorted by `created_at DESC` (newest first).

5. **Performance**: Query uses `idx_tokens_author_id` index. Expected performance:
   - Count query: O(log n)
   - Data query: O(log n + limit)
   - Acceptable for <100k tokens per author

### Implementation Details

**Repository Method** (`repositories/token.py`):

```python
async def get_by_author_paginated(
    self,
    author_id: UUID,
    page: int = 1,
    limit: int = 20
) -> tuple[list[Token], int]:
    """Get tokens by author with pagination."""
    # Count total
    count_result = await self.session.execute(
        select(func.count(Token.id))
        .where(Token.author_id == author_id)
    )
    total = count_result.scalar_one()

    # Fetch page
    offset = (page - 1) * limit
    result = await self.session.execute(
        select(Token)
        .where(Token.author_id == author_id)
        .order_by(Token.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    tokens = list(result.scalars().all())

    return tokens, total
```

**Endpoint Handler** (`api/routes/tokens.py`):

```python
@router.get("/authors/{wallet_address}/tokens", response_model=AuthorTokensResponse)
async def get_author_tokens(
    wallet_address: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    uow_factory=Depends(get_uow_factory),
) -> AuthorTokensResponse:
    """Get tokens authored by wallet address with pagination."""
    # Normalize address
    checksummed = Web3.to_checksum_address(wallet_address)

    async with await uow_factory() as uow:
        # Get author
        author = await uow.authors.get_by_wallet(checksummed)
        if not author:
            return AuthorTokensResponse(tokens=[], total=0, page=page, limit=limit)

        # Get paginated tokens
        tokens, total = await uow.tokens.get_by_author_paginated(
            author_id=author.id,
            page=page,
            limit=limit,
        )

        return AuthorTokensResponse(
            tokens=[TokenResponse.from_token(t) for t in tokens],
            total=total,
            page=page,
            limit=limit,
        )
```

### Testing

**Unit Tests**:
- Valid wallet address with tokens → 200 with data
- Valid wallet address without author record → 200 with empty array
- Invalid wallet address format → 400 error
- Page beyond bounds → 200 with empty tokens array
- Limit validation (negative, zero, >100) → 422 error

**Integration Tests** (testcontainers):
- Seed database with author + 50 tokens
- Query page 1 (20 tokens) → verify tokens[0-19], total=50
- Query page 2 (20 tokens) → verify tokens[20-39], total=50
- Query page 3 (10 tokens) → verify tokens[40-49], total=50
- Query page 4 → verify empty array, total=50

**Manual Testing** (curl):

```bash
# Test with existing author
curl "http://localhost:8000/api/authors/0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0/tokens?page=1&limit=20"

# Test with non-existent author (should return empty array)
curl "http://localhost:8000/api/authors/0x0000000000000000000000000000000000000001/tokens?page=1&limit=20"

# Test pagination
curl "http://localhost:8000/api/authors/0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0/tokens?page=2&limit=10"

# Test invalid address (should return 400)
curl "http://localhost:8000/api/authors/invalid-address/tokens"
```

---

## Summary

**Endpoints**: 1 new GET endpoint

**Authentication**: None required (public read)

**Rate Limiting**: Not implemented in MVP (acceptable for initial launch)

**Caching**: Not implemented in MVP (database queries fast enough for expected load)

**CORS**: Already configured in main.py (allows localhost:5173 for dev)

**Next Steps**: Create internal service contracts documentation
