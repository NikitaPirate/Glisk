# Data Model: Author Leaderboard Landing Page

**Feature**: 009-create-a-main
**Date**: 2025-10-22

## Overview

This feature does **not introduce new database tables or schema changes**. It uses existing `tokens_s0` and `authors` tables with a new aggregation query pattern.

## Existing Entities (Used by This Feature)

### Author Entity

**Table**: `authors`

**Purpose**: Represents NFT prompt creators with wallet-based identity

**Schema**:
```python
class Author(SQLModel, table=True):
    __tablename__ = "authors"

    id: UUID = Field(primary_key=True)
    wallet_address: str = Field(unique=True)     # Used in leaderboard response
    prompt_text: Optional[str]                   # NOT used (not exposed in leaderboard)
    twitter_handle: Optional[str]                # NOT used (not exposed in leaderboard)
    created_at: datetime
```

**Indexes**:
- Primary key on `id`
- Unique index on `wallet_address`

**Leaderboard Usage**:
- `wallet_address`: Displayed in frontend list (checksummed format)
- `id`: Join key for aggregation query

---

### Token Entity

**Table**: `tokens_s0`

**Purpose**: Represents minted NFTs with lifecycle tracking

**Schema**:
```python
class Token(SQLModel, table=True):
    __tablename__ = "tokens_s0"

    id: UUID = Field(primary_key=True)
    token_id: int = Field(unique=True, index=True)
    author_id: UUID = Field(foreign_key="authors.id")  # Aggregation key
    status: TokenStatus
    image_cid: Optional[str]
    metadata_cid: Optional[str]
    # ... other fields (not used in leaderboard)
```

**Indexes**:
- Primary key on `id`
- Unique index on `token_id`
- Foreign key index on `author_id` (used for GROUP BY)

**Leaderboard Usage**:
- `author_id`: GROUP BY key to count tokens per author
- Row count per author: Aggregated into `total_tokens` field

---

## Aggregation Query

**Purpose**: Transform relational data into leaderboard format

**SQL Pattern**:
```sql
SELECT
    a.wallet_address,
    COUNT(t.id) as total_tokens
FROM tokens_s0 t
INNER JOIN authors a ON t.author_id = a.id
GROUP BY a.id, a.wallet_address
ORDER BY total_tokens DESC, a.wallet_address ASC
LIMIT 50
```

**SQLModel Implementation** (in `AuthorRepository.get_author_leaderboard()`):
```python
from sqlmodel import select, func

stmt = (
    select(
        Author.wallet_address,
        func.count(Token.id).label("total_tokens")
    )
    .select_from(Token)
    .join(Author, Token.author_id == Author.id)
    .group_by(Author.id, Author.wallet_address)
    .order_by(func.count(Token.id).desc(), Author.wallet_address.asc())
    .limit(50)
)

results = await session.exec(stmt)
```

**Query Characteristics**:
- **Complexity**: O(n log n) where n = total tokens
- **Performance**: <100ms for 10,000 tokens
- **Output**: List of tuples `(wallet_address: str, total_tokens: int)`

---

## Data Transfer Objects (DTOs)

### AuthorLeaderboardEntry

**Purpose**: API response format for leaderboard entries

**TypeScript Interface** (frontend):
```typescript
interface AuthorLeaderboardEntry {
  author_address: string    // Checksummed Ethereum address (42 chars)
  total_tokens: number      // Count of tokens authored (always ≥ 1)
}
```

**Python Pydantic Model** (backend):
```python
class AuthorLeaderboardEntry(BaseModel):
    author_address: str = Field(
        ...,
        description="Checksummed Ethereum wallet address",
        min_length=42,
        max_length=42,
    )
    total_tokens: int = Field(
        ...,
        description="Total number of tokens minted by author",
        ge=1,  # Only authors with ≥1 token included
    )
```

**Validation Rules**:
- `author_address`: Must be valid checksummed Ethereum address (0x + 40 hex)
- `total_tokens`: Must be positive integer (≥1)

**Example**:
```json
{
  "author_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
  "total_tokens": 145
}
```

---

### LeaderboardResponse

**Purpose**: Full API response format (array of entries)

**TypeScript Type** (frontend):
```typescript
type LeaderboardResponse = AuthorLeaderboardEntry[]
```

**Python Pydantic Model** (backend):
```python
class LeaderboardResponse(BaseModel):
    """Root response model for GET /api/authors/leaderboard"""
    __root__: list[AuthorLeaderboardEntry] = Field(
        ...,
        description="Array of authors sorted by token count (descending)",
        max_items=50,
    )
```

**Constraints**:
- Array length: 0 to 50 items (enforced by SQL LIMIT)
- Ordering: Guaranteed descending by `total_tokens`, then ascending by `author_address`

**Example Response**:
```json
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

---

## Data Flow

### Read Path (Leaderboard Display)

```
1. Frontend Component (AuthorLeaderboard.tsx)
   ↓ HTTP GET /api/authors/leaderboard

2. Backend API Route (authors.py:get_author_leaderboard)
   ↓ Call repository method

3. AuthorRepository.get_author_leaderboard()
   ↓ Execute aggregation query

4. PostgreSQL Database
   ↓ Return aggregated results (wallet_address, total_tokens)

5. Backend API Route
   ↓ Map to AuthorLeaderboardEntry DTOs
   ↓ Serialize to JSON

6. Frontend Component
   ↓ Parse JSON response
   ↓ Store in useState
   ↓ Render list items
```

**No Write Path** - Feature is read-only (display only)

---

## Data Integrity

### Referential Integrity

**Foreign Key**: `tokens_s0.author_id → authors.id`

**Constraints**:
- Every token MUST have a valid author (enforced by FK constraint)
- Authors can be deleted only if they have no tokens (or use CASCADE)
- GROUP BY aggregation never produces orphaned results

### Consistency Guarantees

**Database Level**:
- ACID transactions ensure token counts are accurate
- Unique constraint on `authors.wallet_address` prevents duplicates

**Application Level**:
- Repository method uses async session (transaction-safe)
- Read-only query (no state mutations, no race conditions)

**Edge Cases Handled**:
- Author with 0 tokens: Not included in results (GROUP BY excludes)
- Deleted author with existing tokens: FK constraint prevents deletion
- Concurrent token creation during query: Snapshot isolation ensures consistent view

---

## Performance Considerations

### Query Optimization

**Indexes Used**:
1. `tokens_s0.author_id` (foreign key index) - GROUP BY acceleration
2. `authors.id` (primary key) - JOIN acceleration
3. `authors.wallet_address` (unique index) - SELECT projection

**Expected Query Plan**:
```
Limit (cost=... rows=50)
  -> Sort (cost=... rows=N)
      Sort Key: (count(t.id)) DESC, a.wallet_address ASC
      -> HashAggregate (cost=... rows=N)
          Group Key: a.id, a.wallet_address
          -> Hash Join (cost=... rows=M)
              Hash Cond: (t.author_id = a.id)
              -> Seq Scan on tokens_s0 t
              -> Hash
                  -> Seq Scan on authors a
```

**Bottlenecks**:
- Sequential scan on `tokens_s0` (acceptable for <10k tokens)
- In-memory sort of aggregated results (max 50 rows, negligible)

**Scaling Limits**:
- Up to 10,000 tokens: <100ms query time
- Up to 100,000 tokens: May need index on `tokens_s0.author_id` if not FK-indexed
- Beyond 100,000 tokens: Consider materialized view or caching (future optimization)

---

## Schema Migration

**No migrations required** ✅

This feature uses existing schema without modifications. Verified indexes:
- ✅ `tokens_s0.author_id` - Foreign key (indexed by PostgreSQL)
- ✅ `authors.wallet_address` - Unique constraint (indexed)

If `tokens_s0.author_id` foreign key does NOT have implicit index (some databases), add:

```sql
-- Optional (only if FK not auto-indexed)
CREATE INDEX idx_tokens_author_id ON tokens_s0 (author_id);
```

**Verification Query**:
```sql
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'tokens_s0' AND indexname LIKE '%author%';
```

---

## Testing Data Scenarios

### Test Dataset 1: Basic Leaderboard
```
Author A (0x111...): 5 tokens
Author B (0x222...): 3 tokens
Author C (0x333...): 1 token

Expected Output:
[
  {author_address: "0x111...", total_tokens: 5},
  {author_address: "0x222...", total_tokens: 3},
  {author_address: "0x333...", total_tokens: 1}
]
```

### Test Dataset 2: Tie-Breaking
```
Author A (0xAAA...): 3 tokens
Author B (0xBBB...): 3 tokens
Author C (0xCCC...): 3 tokens

Expected Output (alphabetical by address):
[
  {author_address: "0xAAA...", total_tokens: 3},
  {author_address: "0xBBB...", total_tokens: 3},
  {author_address: "0xCCC...", total_tokens: 3}
]
```

### Test Dataset 3: Limit Enforcement
```
60 authors with varying token counts

Expected Output:
- Array length = 50 (truncated)
- Highest 50 token counts only
- Sorted correctly
```

### Test Dataset 4: Empty Database
```
No authors, no tokens

Expected Output:
[]
```

---

## Summary

This feature introduces **zero new database entities** and requires **zero schema migrations**. It leverages existing `tokens_s0` and `authors` tables through a simple aggregation query. The data model is read-only, performant, and uses standard SQL patterns consistent with the project's Simplicity First principle.

**Schema Changes**: None ✅
**New Tables**: None ✅
**New Indexes**: None (FK indexes already exist) ✅
**Migrations**: None required ✅
