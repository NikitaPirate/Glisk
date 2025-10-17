# Data Model: IPFS Upload and Batch Reveal Mechanism

**Feature**: 003-003d-ipfs-reveal
**Date**: 2025-10-17
**Phase**: 1 - Design & Contracts

## Overview

This document defines the data entities, field specifications, relationships, and state transitions for the IPFS upload and batch reveal feature. The feature extends the existing `tokens_s0` table with three new fields and adds two audit tables for tracking IPFS operations and reveal transactions.

## Entities

### Token (Extended)

**Table**: `tokens_s0` (existing table from 003a, extended in this feature)

**Description**: Represents a minted NFT token progressing through the complete pipeline: detection → generation → upload → reveal. Tracks IPFS storage references and reveal transaction.

**New Fields** (added by this feature):

| Field | Type | Nullable | Default | Constraints | Description |
|-------|------|----------|---------|-------------|-------------|
| `image_cid` | `TEXT` | Yes | `NULL` | None | IPFS content identifier for uploaded image (Pinata CID v1 format) |
| `metadata_cid` | `TEXT` | Yes | `NULL` | None | IPFS content identifier for uploaded metadata JSON (Pinata CID v1 format) |
| `reveal_tx_hash` | `TEXT` | Yes | `NULL` | None | Ethereum transaction hash of batch reveal operation (0x-prefixed hex) |

**Existing Fields** (from 003a/003b/003c, relevant to this feature):

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `token_id` | `INTEGER` | No | Primary key, unique token identifier |
| `contract_address` | `TEXT` | No | NFT contract address (indexed) |
| `status` | `TEXT` | No | Token lifecycle status (enum: 'detected', 'generating', 'uploading', 'ready', 'revealed', 'failed') |
| `detected_at` | `TIMESTAMP` | No | UTC timestamp when mint event detected (used for FIFO ordering) |
| `author_id` | `INTEGER` | No | Foreign key to `authors` table |
| `image_url` | `TEXT` | Yes | Generated image URL from Replicate (003c) |
| `generation_attempts` | `INTEGER` | No | Image generation retry counter (003c) |
| `generation_error` | `TEXT` | Yes | Last generation error message (003c) |

**Indexes** (existing from 003a):
- Primary key on `token_id`
- Index on `contract_address` (for contract-specific queries)
- Index on `status` (used by workers' `WHERE status = X` queries)

**No new indexes needed**: Workers filter on `status` (already indexed) and order by `token_id` (primary key, implicit index).

---

### IPFS Upload Record (New Audit Table)

**Table**: `ipfs_upload_records`

**Description**: Audit trail for IPFS operations. Tracks each upload attempt (image and metadata) for debugging, compliance, and failure analysis.

**Fields**:

| Field | Type | Nullable | Default | Constraints | Description |
|-------|------|----------|---------|-------------|-------------|
| `upload_id` | `SERIAL` | No | Auto-increment | Primary key | Unique identifier for upload record |
| `token_id` | `INTEGER` | No | - | Foreign key to `tokens_s0.token_id` | Associated token |
| `upload_type` | `TEXT` | No | - | Enum: 'image', 'metadata' | Type of content uploaded |
| `ipfs_cid` | `TEXT` | Yes | `NULL` | None | IPFS CID if upload succeeded |
| `status` | `TEXT` | No | - | Enum: 'success', 'failed', 'retrying' | Upload outcome |
| `attempt_number` | `INTEGER` | No | `1` | `>= 1` | Which attempt this was (1, 2, 3) |
| `error_message` | `TEXT` | Yes | `NULL` | None | Error details if status='failed' |
| `created_at` | `TIMESTAMP` | No | `now()` | UTC timestamp | When upload was attempted |

**Indexes**:
- Primary key on `upload_id`
- Index on `token_id` (for querying upload history per token)
- Index on `(token_id, upload_type)` (for querying specific upload type)

**Relationship**: `IPFSUploadRecord.token_id` → `Token.token_id` (many-to-one)

**Rationale**: Audit records enable debugging failed uploads, tracking retry patterns, and compliance reporting. Separate table prevents token table bloat with historical attempts.

---

### Reveal Transaction (New Audit Table)

**Table**: `reveal_transactions`

**Description**: Tracks batch reveal operations submitted to blockchain. Enables monitoring batch efficiency, troubleshooting transaction failures, and correlating on-chain state with database state.

**Fields**:

| Field | Type | Nullable | Default | Constraints | Description |
|-------|------|----------|---------|-------------|-------------|
| `reveal_id` | `SERIAL` | No | Auto-increment | Primary key | Unique identifier for reveal record |
| `tx_hash` | `TEXT` | No | - | Unique constraint | Ethereum transaction hash (0x-prefixed hex) |
| `token_ids` | `INTEGER[]` | No | - | Non-empty array | Array of token IDs in this batch |
| `metadata_uris` | `TEXT[]` | No | - | Non-empty array | Array of metadata URIs (ipfs://CID format) |
| `status` | `TEXT` | No | - | Enum: 'pending', 'confirmed', 'failed' | Transaction status |
| `gas_price` | `BIGINT` | Yes | `NULL` | None | Gas price used (wei) |
| `gas_limit` | `INTEGER` | Yes | `NULL` | None | Gas limit set for transaction |
| `gas_used` | `INTEGER` | Yes | `NULL` | None | Actual gas used (after confirmation) |
| `block_number` | `INTEGER` | Yes | `NULL` | None | Block number where transaction confirmed |
| `error_message` | `TEXT` | Yes | `NULL` | None | Error details if status='failed' |
| `submitted_at` | `TIMESTAMP` | No | `now()` | UTC timestamp | When transaction was submitted |
| `confirmed_at` | `TIMESTAMP` | Yes | `NULL` | UTC timestamp | When transaction was confirmed (if successful) |

**Indexes**:
- Primary key on `reveal_id`
- Unique index on `tx_hash` (one record per transaction)
- Index on `status` (for querying pending/failed transactions)
- Index on `submitted_at` (for time-based queries)

**Relationship**: `RevealTransaction.token_ids` references multiple `Token.token_id` (many-to-many via array)

**Rationale**: Audit records enable gas cost analysis (compare gas_limit vs gas_used), batch efficiency tracking (array_length(token_ids)), transaction monitoring (pending vs confirmed), and revert investigation (error_message). Critical for production observability.

---

## State Transitions

### Token Status Lifecycle (IPFS Upload & Reveal Phase)

**State Machine**:

```
┌───────────┐
│ uploading │ ← Initial state (from 003c image generation)
└────┬──────┘
     │ IPFS upload worker polls and locks token
     │ Status: uploading → uploading (in-flight)
     ▼
┌─────────────────────────┐
│ uploading (processing)  │
└────┬──────────┬─────────┘
     │          │
     │          │ ┌────────────────────────────────┐
     │          │ │ On upload failure:             │
     │          └─┤ - Transient error: Retry with  │
     │            │   exponential backoff (up to   │
     │            │   3 attempts, status unchanged)│
     │            │ - Permanent error: Status →    │
     │            │   failed, store error          │
     │            └────────────────────────────────┘
     │
     │ On upload success (both image + metadata)
     │ Status: uploading → ready
     ▼
┌──────┐
│ ready│ ← Ready for batch reveal
└──┬───┘
   │ Reveal worker polls and locks token
   │ Batch accumulation (5s OR 50 tokens)
   │ Status: ready → ready (in-flight)
   ▼
┌────────────────────────┐
│ ready (in batch)       │
└────┬───────────┬───────┘
     │           │
     │           │ ┌─────────────────────────────┐
     │           │ │ On reveal failure:          │
     │           └─┤ - Timeout/gas error:        │
     │             │   Status unchanged, retry   │
     │             │   next poll                 │
     │             │ - Transaction revert:       │
     │             │   Status unchanged, manual  │
     │             │   investigation required    │
     │             └─────────────────────────────┘
     │
     │ On reveal success (transaction confirmed)
     │ Status: ready → revealed
     ▼
┌──────────┐
│ revealed │ ← Terminal success state
└──────────┘

┌────────┐
│ failed │ ← Terminal failure state (from any phase)
└────────┘
```

**Transition Rules**:

| From State | To State | Trigger | Field Updates |
|------------|----------|---------|---------------|
| `uploading` | `ready` | IPFS upload succeeds (both image + metadata) | `image_cid` = CID, `metadata_cid` = CID |
| `uploading` | `failed` | Permanent IPFS error (401, 403, max retries) | `generation_error` = error message |
| `ready` | `revealed` | Batch reveal transaction confirmed | `reveal_tx_hash` = tx hash |
| `ready` | `ready` | Reveal transaction timeout/gas error | None (retry on next poll) |
| `ready` | `ready` | Transaction revert | None (investigation required) |

**Note**: Unlike 'generating' (003c), 'uploading' and 'ready' states do NOT reset to previous state on transient failure. Workers retry within the same status (using generation_attempts field for retries). This simplifies state machine and reduces status churn.

**Startup Recovery** (orphaned tokens):

| From State | To State | Trigger | Condition |
|------------|----------|---------|-----------|
| `uploading` | `uploading` | Worker startup | Reset to stable state (no in-flight operation) |
| `ready` | `ready` | Worker startup | Already stable (no recovery needed) |

---

## Validation Rules

### Field-Level Validation

**Image URL** (from 003c, used for IPFS upload):
- Must be non-null when status='uploading'
- Must be valid HTTP/HTTPS URL format
- Replicate CDN URLs expire after 10 days (time pressure for upload)

**IPFS CID**:
- Must be valid CIDv0 (Qm...) or CIDv1 (baf...) format
- Pinata returns CIDv1 by default (configurable via `cidVersion` parameter)
- Both image_cid and metadata_cid must be non-null when status='ready'

**Metadata URI**:
- Format: `ipfs://<metadata_cid>` (ERC721 standard)
- No gateway URL in metadata (wallets resolve IPFS URIs to their preferred gateway)

**Reveal Transaction Hash**:
- Must be valid Ethereum transaction hash (0x-prefixed, 66 characters)
- Must be non-null when status='revealed'

**Token IDs in Batch**:
- Array length: 1-50 tokens (enforced at reveal worker)
- All token IDs must exist in tokens_s0 table
- All tokens must have status='ready' before batch submission

---

## Invariants

**Business Logic Invariants**:

1. **IPFS Upload Completeness**: A token with status='ready' MUST have non-null `image_cid` AND `metadata_cid`
2. **Reveal Completeness**: A token with status='revealed' MUST have non-null `reveal_tx_hash`
3. **Metadata Consistency**: `metadata_cid` MUST reference metadata JSON containing `image_cid` in its 'image' field
4. **Batch Atomicity**: All tokens in a reveal batch MUST transition to 'revealed' together (or remain 'ready' together on failure)
5. **Idempotency**: A token MUST NOT be included in multiple concurrent batches (enforced via `FOR UPDATE SKIP LOCKED`)

**Database-Level Invariants**:

1. **Foreign Key**: `Token.author_id` MUST reference valid `Author.author_id`
2. **Foreign Key**: `IPFSUploadRecord.token_id` MUST reference valid `Token.token_id`
3. **Unique Transaction**: `RevealTransaction.tx_hash` MUST be unique across all records
4. **Non-Empty Batch**: `RevealTransaction.token_ids` array MUST have length >= 1
5. **Array Consistency**: `RevealTransaction.metadata_uris` array MUST have same length as `token_ids` array

---

## Example Data Flow

### Successful IPFS Upload (First Attempt)

```
Initial State:
  token_id: 123
  status: 'uploading'
  image_url: "https://replicate.delivery/pbxt/abc123/output.png"
  image_cid: NULL
  metadata_cid: NULL
  generation_attempts: 1 (from 003c)

IPFS Upload Worker Processing:
  1. Lock token (FOR UPDATE SKIP LOCKED)
  2. Download image from image_url
  3. Upload image to Pinata → CID: "bafkreih5aznjvttude6c3wbvqeebb6rlx5wkbzyppv7garjiubll2ceym4"
  4. Create audit record:
     - upload_id: 1
     - token_id: 123
     - upload_type: 'image'
     - ipfs_cid: "bafkreih5aznjvttude6c3wbvqeebb6rlx5wkbzyppv7garjiubll2ceym4"
     - status: 'success'
     - attempt_number: 1
  5. Build metadata JSON:
     {
       "name": "Token #123",
       "description": "Generated NFT from Season 0",
       "image": "ipfs://bafkreih5aznjvttude6c3wbvqeebb6rlx5wkbzyppv7garjiubll2ceym4",
       "attributes": []
     }
  6. Upload metadata to Pinata → CID: "bafkreihjk9abc..."
  7. Create audit record:
     - upload_id: 2
     - token_id: 123
     - upload_type: 'metadata'
     - ipfs_cid: "bafkreihjk9abc..."
     - status: 'success'
     - attempt_number: 1
  8. Update token:
     - status: 'uploading' → 'ready'
     - image_cid: "bafkreih5aznjvttude6c3wbvqeebb6rlx5wkbzyppv7garjiubll2ceym4"
     - metadata_cid: "bafkreihjk9abc..."
  9. Commit transaction

Final State:
  token_id: 123
  status: 'ready'
  image_cid: "bafkreih5aznjvttude6c3wbvqeebb6rlx5wkbzyppv7garjiubll2ceym4"
  metadata_cid: "bafkreihjk9abc..."
  reveal_tx_hash: NULL
```

---

### Successful Batch Reveal (3 Tokens)

```
Initial State:
  Tokens 123, 124, 125 with status='ready', non-null metadata_cid

Reveal Worker Processing:
  1. Poll for ready tokens (FOR UPDATE SKIP LOCKED, LIMIT 50)
     → Result: [123, 124, 125]
  2. Wait 5 seconds for more tokens (batch accumulation)
     → No additional tokens available
  3. Build batch transaction inputs:
     - token_ids: [123, 124, 125]
     - metadata_uris: [
         "ipfs://bafkreihjk9abc...",
         "ipfs://bafkreixyz123...",
         "ipfs://bafkreiqwe789..."
       ]
  4. Estimate gas:
     - estimated_gas: 150,000 (example)
     - gas_limit: 180,000 (150,000 * 1.2)
  5. Get gas price (EIP-1559):
     - maxPriorityFeePerGas: 0.5 gwei * 1.2 = 0.6 gwei
     - maxFeePerGas: (2 gwei * 2) + 0.6 gwei = 4.6 gwei
  6. Submit transaction:
     - tx_hash: "0xabcdef123456..."
  7. Create reveal_transactions record:
     - reveal_id: 1
     - tx_hash: "0xabcdef123456..."
     - token_ids: [123, 124, 125]
     - metadata_uris: [array above]
     - status: 'pending'
     - gas_limit: 180,000
     - gas_price: 4,600,000,000 (wei)
     - submitted_at: 2025-10-17T12:34:56Z
  8. Wait for confirmation (timeout 180s):
     - receipt.status: 1 (success)
     - receipt.blockNumber: 98765432
     - receipt.gasUsed: 145,000
  9. Update reveal_transactions record:
     - status: 'pending' → 'confirmed'
     - block_number: 98765432
     - gas_used: 145,000
     - confirmed_at: 2025-10-17T12:35:12Z
  10. Update tokens:
     - Token 123: status='ready' → 'revealed', reveal_tx_hash="0xabcdef123456..."
     - Token 124: status='ready' → 'revealed', reveal_tx_hash="0xabcdef123456..."
     - Token 125: status='ready' → 'revealed', reveal_tx_hash="0xabcdef123456..."
  11. Commit transaction

Final State:
  Tokens 123, 124, 125:
    status: 'revealed'
    reveal_tx_hash: "0xabcdef123456..."

  reveal_transactions record 1:
    status: 'confirmed'
    gas_used: 145,000 (saved 35,000 gas vs limit)
```

---

### IPFS Upload Failure with Retry

```
Initial State:
  token_id: 456
  status: 'uploading'
  generation_attempts: 1

IPFS Upload Worker Processing (Attempt 1):
  1. Lock token
  2. Upload image to Pinata → 429 Rate Limit (Retry-After: 60s)
  3. Create audit record:
     - upload_id: 3
     - token_id: 456
     - upload_type: 'image'
     - ipfs_cid: NULL
     - status: 'retrying'
     - attempt_number: 1
     - error_message: "Rate limit exceeded, retry after 60s"
  4. Increment generation_attempts: 1 → 2
  5. Commit transaction
  6. Worker applies exponential backoff: 60s + jitter

IPFS Upload Worker Processing (Attempt 2, after 60s):
  1. Lock token
  2. Upload image to Pinata → Success, CID: "bafkreiabc..."
  3. Create audit record:
     - upload_id: 4
     - token_id: 456
     - upload_type: 'image'
     - ipfs_cid: "bafkreiabc..."
     - status: 'success'
     - attempt_number: 2
  4. Upload metadata → Success, CID: "bafkreidef..."
  5. Create audit record:
     - upload_id: 5
     - token_id: 456
     - upload_type: 'metadata'
     - ipfs_cid: "bafkreidef..."
     - status: 'success'
     - attempt_number: 2
  6. Update token:
     - status: 'uploading' → 'ready'
     - image_cid: "bafkreiabc..."
     - metadata_cid: "bafkreidef..."
  7. Commit transaction

Final State:
  token_id: 456
  status: 'ready'
  generation_attempts: 2 (reflects retry)
  image_cid: "bafkreiabc..."
  metadata_cid: "bafkreidef..."
```

---

### Batch Reveal Failure (Transaction Revert)

```
Initial State:
  Tokens 789, 790 with status='ready'

Reveal Worker Processing:
  1. Lock tokens [789, 790]
  2. Build batch, estimate gas, submit transaction
  3. Create reveal_transactions record:
     - reveal_id: 2
     - tx_hash: "0xfailed123..."
     - token_ids: [789, 790]
     - status: 'pending'
  4. Wait for confirmation:
     - receipt.status: 0 (REVERTED)
  5. Update reveal_transactions record:
     - status: 'pending' → 'failed'
     - error_message: "Transaction reverted: Invalid token ID 789"
  6. Tokens remain in 'ready' state (no update)
  7. Log error for manual investigation
  8. Commit transaction

Final State:
  Tokens 789, 790:
    status: 'ready' (unchanged, available for retry after investigation)

  reveal_transactions record 2:
    status: 'failed'
    error_message: "Transaction reverted: Invalid token ID 789"

Manual Investigation:
  - Check why token 789 is invalid (not yet revealed on-chain?)
  - Fix root cause
  - Tokens will be retried on next poll
```

---

## Migration Scripts (Alembic)

### Migration 1: Add IPFS and Reveal Fields to tokens_s0

**File**: `backend/alembic/versions/XXXX_add_ipfs_reveal_fields.py`

```python
"""add_ipfs_reveal_fields

Revision ID: XXXX
Revises: YYYY (003c migration)
Create Date: 2025-10-17

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'XXXX'
down_revision = 'YYYY'  # Previous migration from 003c
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add three new columns to tokens_s0 table
    op.add_column('tokens_s0', sa.Column('image_cid', sa.Text(), nullable=True))
    op.add_column('tokens_s0', sa.Column('metadata_cid', sa.Text(), nullable=True))
    op.add_column('tokens_s0', sa.Column('reveal_tx_hash', sa.Text(), nullable=True))

def downgrade() -> None:
    # Remove columns in reverse order
    op.drop_column('tokens_s0', 'reveal_tx_hash')
    op.drop_column('tokens_s0', 'metadata_cid')
    op.drop_column('tokens_s0', 'image_cid')
```

### Migration 2: Create IPFS Upload Records Table

**File**: `backend/alembic/versions/YYYY_create_ipfs_upload_records.py`

```python
"""create_ipfs_upload_records

Revision ID: YYYY
Revises: XXXX (previous migration)
Create Date: 2025-10-17

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'YYYY'
down_revision = 'XXXX'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'ipfs_upload_records',
        sa.Column('upload_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('token_id', sa.Integer(), nullable=False),
        sa.Column('upload_type', sa.Text(), nullable=False),
        sa.Column('ipfs_cid', sa.Text(), nullable=True),
        sa.Column('status', sa.Text(), nullable=False),
        sa.Column('attempt_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('(CURRENT_TIMESTAMP)')),
        sa.PrimaryKeyConstraint('upload_id'),
        sa.ForeignKeyConstraint(['token_id'], ['tokens_s0.token_id'], ondelete='CASCADE'),
    )

    # Create indexes
    op.create_index('ix_ipfs_upload_records_token_id', 'ipfs_upload_records', ['token_id'])
    op.create_index('ix_ipfs_upload_records_token_id_upload_type', 'ipfs_upload_records', ['token_id', 'upload_type'])

def downgrade() -> None:
    op.drop_index('ix_ipfs_upload_records_token_id_upload_type', table_name='ipfs_upload_records')
    op.drop_index('ix_ipfs_upload_records_token_id', table_name='ipfs_upload_records')
    op.drop_table('ipfs_upload_records')
```

### Migration 3: Create Reveal Transactions Table

**File**: `backend/alembic/versions/ZZZZ_create_reveal_transactions.py`

```python
"""create_reveal_transactions

Revision ID: ZZZZ
Revises: YYYY (previous migration)
Create Date: 2025-10-17

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'ZZZZ'
down_revision = 'YYYY'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'reveal_transactions',
        sa.Column('reveal_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tx_hash', sa.Text(), nullable=False),
        sa.Column('token_ids', postgresql.ARRAY(sa.Integer()), nullable=False),
        sa.Column('metadata_uris', postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column('status', sa.Text(), nullable=False),
        sa.Column('gas_price', sa.BigInteger(), nullable=True),
        sa.Column('gas_limit', sa.Integer(), nullable=True),
        sa.Column('gas_used', sa.Integer(), nullable=True),
        sa.Column('block_number', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=False, server_default=sa.text('(CURRENT_TIMESTAMP)')),
        sa.Column('confirmed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('reveal_id'),
        sa.UniqueConstraint('tx_hash'),
    )

    # Create indexes
    op.create_index('ix_reveal_transactions_status', 'reveal_transactions', ['status'])
    op.create_index('ix_reveal_transactions_submitted_at', 'reveal_transactions', ['submitted_at'])

def downgrade() -> None:
    op.drop_index('ix_reveal_transactions_submitted_at', table_name='reveal_transactions')
    op.drop_index('ix_reveal_transactions_status', table_name='reveal_transactions')
    op.drop_table('reveal_transactions')
```

**Testing Idempotency**:
```bash
cd backend
alembic upgrade head       # Apply all migrations
alembic downgrade -3       # Rollback 3 migrations
alembic upgrade head       # Reapply (should succeed)
```

---

## SQLModel Definitions

### Token Model (Updated)

**File**: `backend/src/glisk/db/models.py` (updated)

```python
from sqlmodel import Field, SQLModel
from datetime import datetime
from typing import Optional

class Token(SQLModel, table=True):
    __tablename__ = "tokens_s0"

    token_id: int = Field(primary_key=True)
    contract_address: str = Field(index=True)
    status: str = Field(index=True)  # 'detected', 'generating', 'uploading', 'ready', 'revealed', 'failed'
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    author_id: int = Field(foreign_key="authors.author_id")

    # From 003c (image generation)
    image_url: Optional[str] = Field(default=None, sa_column_kwargs={"nullable": True})
    generation_attempts: int = Field(default=0, ge=0)
    generation_error: Optional[str] = Field(default=None, sa_column_kwargs={"nullable": True})

    # New fields for 003d (IPFS upload and reveal)
    image_cid: Optional[str] = Field(default=None, sa_column_kwargs={"nullable": True})
    metadata_cid: Optional[str] = Field(default=None, sa_column_kwargs={"nullable": True})
    reveal_tx_hash: Optional[str] = Field(default=None, sa_column_kwargs={"nullable": True})
```

### IPFS Upload Record Model (New)

```python
from sqlmodel import Field, SQLModel
from datetime import datetime
from typing import Optional

class IPFSUploadRecord(SQLModel, table=True):
    __tablename__ = "ipfs_upload_records"

    upload_id: int = Field(primary_key=True, sa_column_kwargs={"autoincrement": True})
    token_id: int = Field(foreign_key="tokens_s0.token_id", index=True)
    upload_type: str  # 'image' or 'metadata'
    ipfs_cid: Optional[str] = Field(default=None)
    status: str  # 'success', 'failed', 'retrying'
    attempt_number: int = Field(default=1, ge=1)
    error_message: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

### Reveal Transaction Model (New)

```python
from sqlmodel import Field, SQLModel, Column
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy import BigInteger, Integer, Text
from datetime import datetime
from typing import Optional

class RevealTransaction(SQLModel, table=True):
    __tablename__ = "reveal_transactions"

    reveal_id: int = Field(primary_key=True, sa_column_kwargs={"autoincrement": True})
    tx_hash: str = Field(unique=True)
    token_ids: list[int] = Field(sa_column=Column(ARRAY(Integer)))
    metadata_uris: list[str] = Field(sa_column=Column(ARRAY(Text)))
    status: str = Field(index=True)  # 'pending', 'confirmed', 'failed'
    gas_price: Optional[int] = Field(default=None, sa_column=Column(BigInteger))
    gas_limit: Optional[int] = Field(default=None)
    gas_used: Optional[int] = Field(default=None)
    block_number: Optional[int] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
    submitted_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    confirmed_at: Optional[datetime] = Field(default=None)
```

---

## Repository Methods

### TokenRepository (Extended)

**File**: `backend/src/glisk/repositories/token.py` (extended)

```python
async def get_ready_for_upload(self, limit: int = 10) -> list[Token]:
    """Find tokens ready for IPFS upload with row-level locking."""
    stmt = (
        select(Token)
        .where(Token.status == "uploading")
        .where(Token.generation_attempts < 3)  # Retry budget
        .order_by(Token.token_id)  # Consistent lock ordering
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    result = await self.session.execute(stmt)
    return list(result.scalars().all())

async def update_ipfs_cids(
    self,
    token: Token,
    image_cid: str,
    metadata_cid: str
) -> None:
    """Update token with IPFS CIDs and mark as ready for reveal."""
    token.image_cid = image_cid
    token.metadata_cid = metadata_cid
    token.status = "ready"
    self.session.add(token)
    await self.session.commit()
    await self.session.refresh(token)

async def get_ready_for_reveal(self, limit: int = 50) -> list[Token]:
    """Find tokens ready for batch reveal with row-level locking."""
    stmt = (
        select(Token)
        .where(Token.status == "ready")
        .order_by(Token.token_id)  # Consistent lock ordering
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    result = await self.session.execute(stmt)
    return list(result.scalars().all())

async def mark_revealed(
    self,
    tokens: list[Token],
    tx_hash: str
) -> None:
    """Update tokens as revealed with transaction hash."""
    for token in tokens:
        token.status = "revealed"
        token.reveal_tx_hash = tx_hash
        self.session.add(token)
    await self.session.commit()
```

### IPFSUploadRecordRepository (New)

**File**: `backend/src/glisk/repositories/ipfs_upload_record.py` (new)

```python
from sqlmodel.ext.asyncio.session import AsyncSession
from glisk.db.models import IPFSUploadRecord

class IPFSUploadRecordRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        token_id: int,
        upload_type: str,
        status: str,
        attempt_number: int,
        ipfs_cid: str | None = None,
        error_message: str | None = None,
    ) -> IPFSUploadRecord:
        """Create audit record for IPFS upload attempt."""
        record = IPFSUploadRecord(
            token_id=token_id,
            upload_type=upload_type,
            ipfs_cid=ipfs_cid,
            status=status,
            attempt_number=attempt_number,
            error_message=error_message,
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record
```

### RevealTransactionRepository (New)

**File**: `backend/src/glisk/repositories/reveal_transaction.py` (new)

```python
from sqlmodel.ext.asyncio.session import AsyncSession
from glisk.db.models import RevealTransaction

class RevealTransactionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        tx_hash: str,
        token_ids: list[int],
        metadata_uris: list[str],
        gas_limit: int,
        gas_price: int,
    ) -> RevealTransaction:
        """Create audit record for reveal transaction."""
        record = RevealTransaction(
            tx_hash=tx_hash,
            token_ids=token_ids,
            metadata_uris=metadata_uris,
            status="pending",
            gas_limit=gas_limit,
            gas_price=gas_price,
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def mark_confirmed(
        self,
        tx_hash: str,
        block_number: int,
        gas_used: int,
    ) -> None:
        """Update transaction as confirmed."""
        stmt = select(RevealTransaction).where(RevealTransaction.tx_hash == tx_hash)
        result = await self.session.execute(stmt)
        record = result.scalar_one()

        record.status = "confirmed"
        record.block_number = block_number
        record.gas_used = gas_used
        record.confirmed_at = datetime.utcnow()

        self.session.add(record)
        await self.session.commit()

    async def mark_failed(
        self,
        tx_hash: str,
        error_message: str,
    ) -> None:
        """Update transaction as failed."""
        stmt = select(RevealTransaction).where(RevealTransaction.tx_hash == tx_hash)
        result = await self.session.execute(stmt)
        record = result.scalar_one()

        record.status = "failed"
        record.error_message = error_message[:1000]  # Truncate

        self.session.add(record)
        await self.session.commit()
```

---

## Summary

**Schema Changes**:
- Add 3 columns to `tokens_s0`: `image_cid`, `metadata_cid`, `reveal_tx_hash`
- Add 2 new tables: `ipfs_upload_records`, `reveal_transactions`
- 3 migration files required

**State Machine**:
- 6 states: `detected` → `generating` → `uploading` → `ready` → `revealed` | `failed`
- New states: `ready` (awaiting reveal), `revealed` (terminal success)
- Transient states: `uploading` (IPFS upload in progress), `ready` (batch accumulation)

**Validation**:
- IPFS CID: v0/v1 format validation
- Metadata URI: `ipfs://` scheme validation
- Transaction hash: 0x-prefixed hex, 66 characters
- Batch size: 1-50 tokens (enforced at worker)

**Relationships**:
- `Token` ↔ `IPFSUploadRecord` (one-to-many, audit trail)
- `Token` ↔ `RevealTransaction` (many-to-many via array, batch tracking)
- No new foreign keys on tokens_s0 (audit tables reference token_id)

**Audit Trail**:
- IPFS operations: Track every upload attempt, success/failure, CID, error message
- Reveal operations: Track every batch, transaction hash, gas usage, block number
- Enables debugging, compliance reporting, gas cost analysis
