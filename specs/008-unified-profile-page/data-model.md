# Data Model: Unified Profile Page

**Date**: 2025-10-22
**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

## Overview

This document defines the data structures for the unified profile page. **No database migrations are required** - this feature uses existing `tokens_s0` and `authors` tables. Includes frontend-only pagination state structures and backend API response models.

---

## Database Schema (No Changes)

### Existing Tables

**tokens_s0** (already exists - no modifications):
```sql
CREATE TABLE tokens_s0 (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    token_id INTEGER UNIQUE NOT NULL,  -- On-chain token ID
    author_id UUID NOT NULL REFERENCES authors(id),
    status VARCHAR(20) NOT NULL DEFAULT 'detected',
    image_url TEXT,
    image_cid VARCHAR(255),
    metadata_cid VARCHAR(255),
    generation_attempts INTEGER NOT NULL DEFAULT 0,
    generation_error VARCHAR(1000),
    reveal_tx_hash VARCHAR(66),
    error_data JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC')
);

CREATE INDEX idx_tokens_author_id ON tokens_s0(author_id);  -- Existing index (FK)
CREATE INDEX idx_tokens_status ON tokens_s0(status);        -- Existing index
CREATE UNIQUE INDEX idx_tokens_token_id ON tokens_s0(token_id);  -- Existing unique index
```

**authors** (already exists - no modifications):
```sql
CREATE TABLE authors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    wallet_address TEXT UNIQUE NOT NULL,
    prompt_text TEXT,
    twitter_handle VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC'),
    updated_at TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC')
);

CREATE UNIQUE INDEX idx_authors_wallet ON authors(wallet_address);  -- Existing index
```

**Key Relationships**:
- `tokens_s0.author_id` → `authors.id` (foreign key, indexed)
- Query pattern: `SELECT * FROM tokens_s0 WHERE author_id = ? ORDER BY created_at DESC LIMIT 20 OFFSET 0`

---

## Backend API Models

### Request Models

**AuthorTokensRequest** (query parameters):
```python
from pydantic import BaseModel, Field

# Query parameters (FastAPI auto-parsing)
class AuthorTokensQueryParams:
    wallet_address: str  # Path parameter
    page: int = Query(1, ge=1, description="Page number (1-indexed)")
    limit: int = Query(20, ge=1, le=100, description="Items per page")
```

### Response Models

**TokenResponse**:
```python
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from glisk.models.token import TokenStatus

class TokenResponse(BaseModel):
    """Single token data for API response."""
    token_id: int  # On-chain token ID
    status: TokenStatus  # detected | generating | uploading | ready | revealed | failed
    image_url: Optional[str] = None  # Replicate CDN URL (if generated)
    metadata_cid: Optional[str] = None  # IPFS CID of metadata JSON (if uploaded)
    created_at: datetime  # UTC timestamp

    @classmethod
    def from_token(cls, token: Token) -> "TokenResponse":
        """Convert Token entity to API response."""
        return cls(
            token_id=token.token_id,
            status=token.status,
            image_url=token.image_url,
            metadata_cid=token.metadata_cid,
            created_at=token.created_at,
        )

    class Config:
        json_schema_extra = {
            "example": {
                "token_id": 42,
                "status": "revealed",
                "image_url": "https://replicate.delivery/pbxt/xyz123.png",
                "metadata_cid": "QmXoypizjW3WknFiJnKLwHCnL72vedxjQkDDP1mXWo6uco",
                "created_at": "2025-10-22T14:30:00Z"
            }
        }
```

**AuthorTokensResponse**:
```python
class AuthorTokensResponse(BaseModel):
    """Paginated list of tokens for a given author."""
    tokens: list[TokenResponse]  # Current page of tokens
    total: int  # Total count of tokens (all pages)
    page: int  # Current page number (1-indexed)
    limit: int  # Items per page

    class Config:
        json_schema_extra = {
            "example": {
                "tokens": [
                    {
                        "token_id": 42,
                        "status": "revealed",
                        "image_url": "https://replicate.delivery/pbxt/xyz123.png",
                        "metadata_cid": "QmXoypizjW3WknFiJnKLwHCnL72vedxjQkDDP1mXWo6uco",
                        "created_at": "2025-10-22T14:30:00Z"
                    }
                ],
                "total": 73,
                "page": 1,
                "limit": 20
            }
        }
```

**Error Responses** (standard FastAPI):
```python
# 400 Bad Request - Invalid wallet address
{
    "detail": "Invalid Ethereum address format"
}

# 404 Not Found - Author doesn't exist (returns empty list instead)
{
    "tokens": [],
    "total": 0,
    "page": 1,
    "limit": 20
}

# 500 Internal Server Error
{
    "detail": "Failed to retrieve tokens. Please try again later."
}
```

---

## Frontend State Models

### TypeScript Interfaces

**Token** (frontend representation):
```typescript
// frontend/src/types/token.ts
export type TokenStatus =
  | 'detected'
  | 'generating'
  | 'uploading'
  | 'ready'
  | 'revealed'
  | 'failed';

export interface Token {
  token_id: number;
  status: TokenStatus;
  image_url?: string;
  metadata_cid?: string;
  created_at: string;  // ISO 8601 string
}

export interface AuthorTokensResponse {
  tokens: Token[];
  total: number;
  page: number;
  limit: number;
}
```

**NFTMetadata** (thirdweb format):
```typescript
// thirdweb's NFT structure (from getOwnedNFTs)
export interface NFTMetadata {
  id: bigint;  // Token ID as bigint
  tokenURI: string;
  metadata: {
    name?: string;
    description?: string;
    image?: string;  // IPFS URL or HTTP URL
    attributes?: Array<{
      trait_type: string;
      value: string | number;
    }>;
  };
}
```

**PaginationState** (client-side state):
```typescript
// frontend/src/pages/Profile.tsx
interface PaginationState {
  currentPage: number;  // 1-indexed
  totalPages: number;
  pageSize: number;  // Always 20 for this feature
  isLoading: boolean;
}

// Example usage
const [authoredPagination, setAuthoredPagination] = useState<PaginationState>({
  currentPage: 1,
  totalPages: 1,
  pageSize: 20,
  isLoading: false,
});

const [collectorPagination, setCollectorPagination] = useState<PaginationState>({
  currentPage: 1,
  totalPages: 1,
  pageSize: 20,
  isLoading: false,
});
```

**TabState** (URL-driven):
```typescript
type TabType = 'author' | 'collector';

// Derived from URL query param
const activeTab: TabType = searchParams.get('tab') === 'collector' ? 'collector' : 'author';
```

---

## Data Flow

### Author Tab - Authored NFTs (Backend API)

```
┌─────────────────────────────────────────────────────────────┐
│ Frontend: Profile.tsx (Author Tab)                         │
├─────────────────────────────────────────────────────────────┤
│ 1. User connects wallet (wagmi useAccount hook)            │
│ 2. useEffect watches: [address, currentPage]               │
│ 3. Fetch: GET /api/authors/{address}/tokens?page=1&limit=20│
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Backend: tokens.py (GET /api/authors/{wallet}/tokens)      │
├─────────────────────────────────────────────────────────────┤
│ 1. Normalize wallet address (Web3.to_checksum_address)     │
│ 2. Query authors table: get_by_wallet(wallet_address)      │
│ 3. If not found: return empty AuthorTokensResponse         │
│ 4. Query tokens table: get_by_author_paginated(author.id)  │
│    - WHERE author_id = ?                                    │
│    - ORDER BY created_at DESC                               │
│    - LIMIT 20 OFFSET (page-1)*20                            │
│ 5. Count total: SELECT COUNT(*) WHERE author_id = ?        │
│ 6. Return AuthorTokensResponse                             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Frontend: Render NFT Grid                                  │
├─────────────────────────────────────────────────────────────┤
│ 1. Map response.tokens to NFT cards                        │
│ 2. Use thirdweb NFTMedia (via metadata_cid if available)   │
│ 3. Calculate totalPages = Math.ceil(total / 20)            │
│ 4. Render pagination controls                              │
└─────────────────────────────────────────────────────────────┘
```

### Collector Tab - Owned NFTs (Blockchain Read)

```
┌─────────────────────────────────────────────────────────────┐
│ Frontend: Profile.tsx (Collector Tab)                      │
├─────────────────────────────────────────────────────────────┤
│ 1. User connects wallet (wagmi useAccount hook)            │
│ 2. useReadContract(getOwnedNFTs) - thirdweb hook           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ thirdweb SDK: getOwnedNFTs extension                       │
├─────────────────────────────────────────────────────────────┤
│ 1. Call contract.balanceOf(owner) → totalNFTs              │
│ 2. Loop i from 0 to totalNFTs-1:                           │
│    - Call contract.tokenOfOwnerByIndex(owner, i) → tokenId │
│    - Call contract.tokenURI(tokenId) → URI                 │
│    - Fetch metadata from URI (IPFS or HTTP)                │
│ 3. Return NFTMetadata[] array (all NFTs)                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Frontend: Client-Side Pagination                           │
├─────────────────────────────────────────────────────────────┤
│ 1. allNFTs = result from thirdweb (complete array)         │
│ 2. totalPages = Math.ceil(allNFTs.length / 20)             │
│ 3. currentPageNFTs = allNFTs.slice(                        │
│      (currentPage - 1) * 20,                                │
│      currentPage * 20                                       │
│    )                                                        │
│ 4. Render NFT grid with currentPageNFTs                    │
│ 5. Render pagination controls                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Pagination Logic

### Backend (SQL LIMIT/OFFSET)

```python
# backend/src/glisk/repositories/token.py

async def get_by_author_paginated(
    self,
    author_id: UUID,
    page: int = 1,
    limit: int = 20
) -> tuple[list[Token], int]:
    """Get tokens by author with pagination.

    Args:
        author_id: UUID of the author
        page: Page number (1-indexed)
        limit: Items per page (default 20, max 100)

    Returns:
        Tuple of (tokens, total_count)
    """
    # Count total tokens
    count_result = await self.session.execute(
        select(func.count(Token.id))
        .where(Token.author_id == author_id)
    )
    total = count_result.scalar_one()

    # Fetch page of tokens
    offset = (page - 1) * limit
    result = await self.session.execute(
        select(Token)
        .where(Token.author_id == author_id)
        .order_by(Token.created_at.desc())  # Newest first
        .limit(limit)
        .offset(offset)
    )
    tokens = list(result.scalars().all())

    return tokens, total

# Example queries:
# Page 1: LIMIT 20 OFFSET 0   (tokens 1-20)
# Page 2: LIMIT 20 OFFSET 20  (tokens 21-40)
# Page 3: LIMIT 20 OFFSET 40  (tokens 41-60)
```

**Performance**:
- Index used: `idx_tokens_author_id` (foreign key index)
- Complexity: O(1) for count, O(log n + limit) for offset query
- Acceptable for <100k tokens per author (well above expected scale)

### Frontend (Array Slicing)

```typescript
// frontend/src/pages/Profile.tsx

// Owned NFTs (client-side pagination)
const { data: allOwnedNFTs, isLoading } = useReadContract(getOwnedNFTs, {
  contract: gliskContract,
  owner: address!,
});

const pageSize = 20;
const totalOwnedPages = Math.ceil((allOwnedNFTs?.length || 0) / pageSize);

const currentPageOwned = allOwnedNFTs?.slice(
  (collectorPage - 1) * pageSize,
  collectorPage * pageSize
);

// Example:
// All NFTs: 47 tokens
// Page 1: allOwnedNFTs.slice(0, 20)   → tokens [0-19]
// Page 2: allOwnedNFTs.slice(20, 40)  → tokens [20-39]
// Page 3: allOwnedNFTs.slice(40, 60)  → tokens [40-46] (only 7 items)
```

**Performance**:
- Array.slice() is O(k) where k = page size (20)
- Negligible cost for <1000 NFTs (expected max per user)
- No re-fetching on pagination (data cached in React state)

---

## State Transitions

### Tab Switching

```
User Action: Click "Collector" tab
  ↓
URL updates: /profile?tab=author → /profile?tab=collector
  ↓
React renders CollectorTabPanel
  ↓
useReadContract(getOwnedNFTs) hook executes
  ↓
Blockchain read via RPC
  ↓
NFT grid displays owned NFTs
```

**State Preservation**:
- Each tab maintains its own pagination state
- Switching tabs preserves pagination (Author tab page 2 → Collector tab → back to Author tab page 2)
- Wallet change resets both tabs to page 1

### Wallet Change

```
User Action: Switch wallet in MetaMask
  ↓
wagmi useAccount hook detects address change
  ↓
useEffect triggers (dependency: [address])
  ↓
Reset pagination state: setCurrentPage(1)
  ↓
Refetch data:
  - Author tab: GET /api/authors/{newAddress}/tokens?page=1
  - Collector tab: getOwnedNFTs(newAddress)
  ↓
NFT grids update with new wallet's data
```

---

## Validation Rules

### Backend

**Wallet Address**:
- Must be 42 characters (0x + 40 hex)
- Checksummed via `Web3.to_checksum_address()` (case-insensitive input)
- Invalid format → 400 Bad Request

**Pagination Parameters**:
- `page`: Must be ≥ 1 (default: 1)
- `limit`: Must be 1-100 (default: 20, capped at 100 to prevent abuse)
- Invalid values → 422 Validation Error (FastAPI auto-validation)

### Frontend

**Tab Parameter**:
- Valid values: "author", "collector"
- Invalid/missing → defaults to "author"
- No error shown to user (silent fallback)

**Pagination Bounds**:
- Current page cannot exceed total pages
- Previous button disabled on page 1
- Next button disabled on last page
- Pagination hidden if total pages ≤ 1

---

## Example Data Snapshots

### Backend Response (Author Tab)

```json
GET /api/authors/0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0/tokens?page=1&limit=20

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

### Frontend State (Collector Tab)

```typescript
// thirdweb getOwnedNFTs result
const allOwnedNFTs: NFTMetadata[] = [
  {
    id: 42n,
    tokenURI: "ipfs://QmXoypizjW3WknFiJnKLwHCnL72vedxjQkDDP1mXWo6uco",
    metadata: {
      name: "Glisk #42",
      description: "Surreal neon landscapes with futuristic architecture",
      image: "ipfs://QmYHNby8fFw4mLTwJzCLzr8wmKmQqp7TK8VjLGECh9dL6H",
      attributes: [
        { trait_type: "Author", value: "0x742d...bEb0" },
        { trait_type: "Prompt", value: "Surreal neon landscapes..." }
      ]
    }
  },
  // ... more NFTs
];

// Pagination state
const collectorPagination = {
  currentPage: 1,
  totalPages: 3,  // Math.ceil(47 / 20)
  pageSize: 20,
  isLoading: false
};

// Current page NFTs (client-side slice)
const currentPageOwned = allOwnedNFTs.slice(0, 20);  // First 20 NFTs
```

---

## Summary

**Database Changes**: None (uses existing schema)

**New API Models**: 2 (TokenResponse, AuthorTokensResponse)

**Frontend State**: 3 interfaces (Token, NFTMetadata, PaginationState)

**Query Performance**: Indexed lookups, acceptable for expected scale (<100k tokens per author)

**Data Flow**: Backend API for authored NFTs, blockchain read for owned NFTs, client-side pagination for both

**Next Steps**: Define API contracts (contracts/api-endpoints.md, contracts/internal-service-contracts.md)
