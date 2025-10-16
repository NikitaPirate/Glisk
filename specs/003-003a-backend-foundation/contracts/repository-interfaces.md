# Repository Interfaces: Backend Foundation

**Feature**: 003a Backend Foundation
**Date**: 2025-10-16
**Purpose**: Define method signatures and contracts for all repository classes

## Overview

This document specifies the public interface for each repository. Repositories provide data access abstraction over SQLModel entities. Per GLISK constitution, repositories are **direct implementations without base classes**.

## Common Patterns

All repositories follow these patterns:

1. **Constructor**: Takes `AsyncSession` dependency
2. **Async Methods**: All data access methods are `async def`
3. **Return Types**: Domain objects (SQLModel instances), not dictionaries
4. **Error Handling**: Let database errors bubble up (no swallowing exceptions)

```python
class ExampleRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def method_name(self, param: Type) -> ReturnType:
        """Docstring explaining query purpose and special behavior."""
        # Implementation
```

---

## AuthorRepository

**Purpose**: Data access for Author entities

### Methods

#### `get_by_id(author_id: UUID) -> Author | None`
Get author by UUID.

**Returns**: Author instance or None if not found

**Example**:
```python
author = await repo.get_by_id(uuid.UUID("..."))
if author:
    print(author.wallet_address)
```

---

#### `get_by_wallet(wallet_address: str) -> Author | None`
Get author by wallet address (case-insensitive lookup).

**Parameters**:
- `wallet_address`: Ethereum address (0x...)

**Returns**: Author instance or None if not found

**Query**: SELECT with WHERE LOWER(wallet_address) = LOWER(:address)

**Example**:
```python
author = await repo.get_by_wallet("0xABC...")  # Case-insensitive
```

---

#### `add(author: Author) -> Author`
Insert new author into database.

**Parameters**:
- `author`: Author instance with fields populated

**Returns**: Same author instance (with auto-generated id if applicable)

**Raises**: IntegrityError if wallet_address already exists

**Example**:
```python
author = Author(wallet_address="0x...", prompt_text="...")
await repo.add(author)
# author.id is now populated
```

---

#### `list_all(limit: int = 100, offset: int = 0) -> list[Author]`
List authors with pagination.

**Parameters**:
- `limit`: Maximum results (default 100, max 1000)
- `offset`: Number of records to skip

**Returns**: List of Author instances

**Ordering**: By created_at DESC (newest first)

---

## TokenRepository

**Purpose**: Data access for Token entities with worker coordination

### Methods

#### `get_by_id(token_id: UUID) -> Token | None`
Get token by UUID.

**Returns**: Token instance or None if not found

---

#### `get_by_token_id(token_id: int) -> Token | None`
Get token by on-chain token ID.

**Parameters**:
- `token_id`: On-chain ERC-721 token ID

**Returns**: Token instance or None if not found

---

#### `add(token: Token) -> Token`
Insert new token into database.

**Parameters**:
- `token`: Token instance with fields populated

**Returns**: Same token instance

**Raises**: IntegrityError if token_id (on-chain ID) already exists

---

#### `get_pending_for_generation(limit: int) -> list[Token]`
**CRITICAL METHOD**: Get tokens ready for image generation with row-level locking.

**Purpose**: Fetch tokens with status=detected for image generation worker. Uses `FOR UPDATE SKIP LOCKED` to prevent concurrent workers from processing same tokens.

**Parameters**:
- `limit`: Maximum tokens to fetch (typically 10-50)

**Returns**: List of Token instances (locked for update)

**Query**:
```sql
SELECT * FROM tokens_s0
WHERE status = 'detected'
ORDER BY mint_timestamp ASC
LIMIT :limit
FOR UPDATE SKIP LOCKED
```

**Behavior**:
- Oldest tokens processed first (FIFO order by mint_timestamp)
- Locks returned rows for duration of transaction
- Other workers skip locked rows (SKIP LOCKED clause)
- Returns empty list if no tokens available

**Concurrency**:
- Worker A gets tokens 1-10 (locks them)
- Worker B (concurrent) gets tokens 11-20 (skips locked rows)
- Zero overlap guaranteed

**Example**:
```python
async with uow:  # Transaction starts
    tokens = await uow.tokens.get_pending_for_generation(limit=10)
    for token in tokens:
        token.mark_generating()  # Status transition
    # Locks released when transaction commits
```

---

#### `get_pending_for_upload(limit: int) -> list[Token]`
Get tokens with status=generating ready for IPFS upload. Uses `FOR UPDATE SKIP LOCKED`.

**Similar to**: `get_pending_for_generation` but filters on status='generating'

**Query**:
```sql
SELECT * FROM tokens_s0
WHERE status = 'generating'
ORDER BY mint_timestamp ASC
LIMIT :limit
FOR UPDATE SKIP LOCKED
```

---

#### `get_ready_for_reveal(limit: int) -> list[Token]`
Get tokens with status=ready for batch reveal. Uses `FOR UPDATE SKIP LOCKED`.

**Similar to**: `get_pending_for_generation` but filters on status='ready'

**Query**:
```sql
SELECT * FROM tokens_s0
WHERE status = 'ready'
ORDER BY mint_timestamp ASC
LIMIT :limit
FOR UPDATE SKIP LOCKED
```

---

#### `get_by_author(author_id: UUID, limit: int = 100) -> list[Token]`
Get all tokens for a specific author.

**Parameters**:
- `author_id`: Author UUID
- `limit`: Maximum results

**Returns**: List of Token instances

**Ordering**: By mint_timestamp DESC (newest first)

---

#### `get_by_status(status: TokenStatus, limit: int = 100) -> list[Token]`
Get tokens by status (without locking).

**Purpose**: Admin queries and monitoring (no worker coordination needed)

**Parameters**:
- `status`: TokenStatus enum value
- `limit`: Maximum results

**Returns**: List of Token instances

**Note**: Does NOT use FOR UPDATE (read-only query)

---

## MintEventRepository

**Purpose**: Data access for MintEvent entities

### Methods

#### `add(event: MintEvent) -> MintEvent`
Insert new mint event.

**Raises**: IntegrityError if (tx_hash, log_index) already exists

---

#### `exists(tx_hash: str, log_index: int) -> bool`
Check if mint event already processed (deduplication).

**Parameters**:
- `tx_hash`: Transaction hash
- `log_index`: Log index within transaction

**Returns**: True if event exists, False otherwise

**Query**:
```sql
SELECT EXISTS(
    SELECT 1 FROM mint_events
    WHERE tx_hash = :tx_hash AND log_index = :log_index
)
```

**Example**:
```python
if await repo.exists(tx_hash, log_index):
    logger.info("event.duplicate", tx_hash=tx_hash)
    return  # Skip processing
```

---

#### `get_by_block_range(start_block: int, end_block: int) -> list[MintEvent]`
Get events within block range (for recovery).

**Parameters**:
- `start_block`: Inclusive start block
- `end_block`: Inclusive end block

**Returns**: List of MintEvent instances

**Ordering**: By block_number ASC, log_index ASC

---

## ImageGenerationJobRepository

**Purpose**: Data access for ImageGenerationJob entities

### Methods

#### `add(job: ImageGenerationJob) -> ImageGenerationJob`
Insert new image generation job.

---

#### `get_by_id(job_id: UUID) -> ImageGenerationJob | None`
Get job by UUID.

---

#### `get_by_token(token_id: UUID) -> list[ImageGenerationJob]`
Get all jobs for a specific token (for retry history).

**Returns**: List of ImageGenerationJob instances

**Ordering**: By created_at DESC (newest first)

---

#### `get_latest_by_token(token_id: UUID) -> ImageGenerationJob | None`
Get most recent job for a token.

**Returns**: Single ImageGenerationJob or None

---

## IPFSUploadRecordRepository

**Purpose**: Data access for IPFSUploadRecord entities

### Methods

#### `add(record: IPFSUploadRecord) -> IPFSUploadRecord`
Insert new IPFS upload record.

---

#### `get_by_id(record_id: UUID) -> IPFSUploadRecord | None`
Get record by UUID.

---

#### `get_by_token(token_id: UUID, record_type: str | None = None) -> list[IPFSUploadRecord]`
Get upload records for a token, optionally filtered by type.

**Parameters**:
- `token_id`: Token UUID
- `record_type`: Optional filter ("image" or "metadata")

**Returns**: List of IPFSUploadRecord instances

**Example**:
```python
# All records for token
records = await repo.get_by_token(token_id)

# Only image upload records
image_records = await repo.get_by_token(token_id, record_type="image")
```

---

## RevealTransactionRepository

**Purpose**: Data access for RevealTransaction entities

### Methods

#### `add(tx: RevealTransaction) -> RevealTransaction`
Insert new reveal transaction.

---

#### `get_by_id(tx_id: UUID) -> RevealTransaction | None`
Get transaction by UUID.

---

#### `get_by_tx_hash(tx_hash: str) -> RevealTransaction | None`
Get transaction by blockchain transaction hash.

---

#### `get_by_status(status: str, limit: int = 100) -> list[RevealTransaction]`
Get reveal transactions by status.

**Parameters**:
- `status`: One of "pending", "sent", "confirmed", "failed"
- `limit`: Maximum results

**Returns**: List of RevealTransaction instances

---

#### `get_pending() -> list[RevealTransaction]`
Get transactions awaiting confirmation.

**Returns**: Transactions with status='sent' (submitted but not confirmed)

**Purpose**: Monitoring worker checks these periodically for confirmation

---

## SystemStateRepository

**Purpose**: Key-value store for operational state

### Methods

#### `get_state(key: str) -> Any | None`
Get state value by key.

**Parameters**:
- `key`: State key (e.g., "last_processed_block")

**Returns**: Deserialized JSON value or None if key doesn't exist

**Example**:
```python
last_block = await repo.get_state("last_processed_block")
if last_block is None:
    last_block = 0  # Default value
```

---

#### `set_state(key: str, value: Any) -> None`
Set state value (insert or update).

**Parameters**:
- `key`: State key
- `value`: Any JSON-serializable value

**Behavior**:
- Creates key if doesn't exist
- Updates value if key exists (UPSERT operation)
- Updates `updated_at` timestamp

**Example**:
```python
await repo.set_state("last_processed_block", 12345)
await repo.set_state("worker_config", {"batch_size": 50})
```

---

#### `delete_state(key: str) -> None`
Delete state key.

**Parameters**:
- `key`: State key to delete

**Behavior**: No-op if key doesn't exist (idempotent)

---

## Error Handling Contract

### Database Errors

Repositories let database errors bubble up (no catching/wrapping):

- **IntegrityError**: Unique constraint violations, foreign key violations
- **OperationalError**: Connection issues, timeouts
- **DataError**: Invalid data types, constraint violations

**Example**:
```python
try:
    await repo.add(author)
except IntegrityError:
    # Handle duplicate wallet address
    raise ValueError(f"Wallet {author.wallet_address} already exists")
```

### Not Found

Methods return `None` for not-found scenarios (no exceptions):

```python
author = await repo.get_by_id(uuid)
if author is None:
    raise HTTPException(status_code=404, detail="Author not found")
```

---

## Testing Contract

### Complex Logic Tests (Required)

Per GLISK constitution, test only complex logic:

**Must Test**:
1. **FOR UPDATE SKIP LOCKED**: Concurrent workers get non-overlapping tokens
2. **Case-insensitive wallet lookup**: get_by_wallet("0xABC") finds "0xabc"
3. **Duplicate detection**: exists() returns True for existing events
4. **UPSERT behavior**: set_state() creates or updates correctly

**Skip Testing**:
- Simple add/get_by_id operations (trust SQLAlchemy)
- Foreign key cascades (trust PostgreSQL)
- List methods with pagination (standard pattern)

### Example: FOR UPDATE SKIP LOCKED Test

```python
async def test_concurrent_workers_receive_non_overlapping_tokens(uow_factory):
    # Setup: Create 20 tokens with status=detected
    async with uow_factory() as uow:
        for i in range(20):
            token = Token(token_id=i, status=TokenStatus.DETECTED, ...)
            await uow.tokens.add(token)
        await uow.commit()

    # Act: Two workers fetch tokens concurrently
    async def worker_fetch(worker_id: int) -> list[UUID]:
        async with uow_factory() as uow:
            tokens = await uow.tokens.get_pending_for_generation(limit=10)
            return [t.id for t in tokens]

    worker_a_ids, worker_b_ids = await asyncio.gather(
        worker_fetch(1),
        worker_fetch(2)
    )

    # Assert: No overlap between workers
    assert len(worker_a_ids) == 10
    assert len(worker_b_ids) == 10
    assert set(worker_a_ids).isdisjoint(set(worker_b_ids))
```

---

## Performance Expectations

| Method | Expected Latency | Notes |
|--------|------------------|-------|
| `get_by_id` | <5ms | Indexed lookup |
| `get_pending_for_generation` | <20ms | Index on (status, mint_timestamp) |
| `exists` | <5ms | Unique index lookup |
| `get_state` | <10ms | Primary key lookup |
| `set_state` | <15ms | UPSERT operation |

Latencies measured at database level (excludes network time).

---

## Future Extensions

These repository methods will be added in features 003b-003e:

**003b (Event Detection)**:
- `MintEventRepository.get_last_processed_block()` - Convenience wrapper around SystemState

**003c (Image Generation)**:
- `TokenRepository.get_failed_retryable(max_retry: int)` - Get failed tokens eligible for retry

**003d (Reveal Worker)**:
- `RevealTransactionRepository.get_stale_pending(timeout_seconds: int)` - Detect stuck transactions

**003e (Admin API)**:
- `TokenRepository.search(filters: dict)` - Complex search with multiple filters

---

## Implementation Checklist

For each repository:

- [ ] Constructor takes `AsyncSession` parameter
- [ ] All methods are `async def`
- [ ] Docstrings explain query purpose and special behavior
- [ ] FOR UPDATE SKIP LOCKED queries have explicit comments
- [ ] Methods return domain objects (SQLModel instances), not dicts
- [ ] No exception swallowing (let errors bubble up)
- [ ] Complex logic has dedicated tests in test_repositories.py
