# Data Model: 003a Backend Foundation

**Feature**: Backend Foundation - Shared Infrastructure
**Date**: 2025-10-16
**Phase**: 1 (Design)

## Overview

This document defines the database schema and domain models for the GLISK backend. All entities are implemented as SQLModel classes (combining Pydantic validation with SQLAlchemy ORM).

## Schema Diagram

```
┌─────────────┐
│   Author    │
│─────────────│
│ id          │◄───┐
│ wallet_addr │    │
│ twitter     │    │
│ farcaster   │    │
│ prompt_text │    │
│ created_at  │    │
└─────────────┘    │
                   │ author_id (FK)
                   │
┌─────────────┐    │     ┌──────────────────┐
│ MintEvent   │    │     │    Token (s0)    │
│─────────────│    │     │──────────────────│
│ id          │    └─────┤ id               │
│ tx_hash     │          │ author_id (FK)   │
│ log_index   │          │ minter_addr      │
│ block_num   │          │ status (enum)    │
│ block_time  │          │ mint_timestamp   │
│ token_id    │          │ image_cid        │
│ detected_at │          │ metadata_cid     │
└─────────────┘          │ error_data       │
     (UNIQUE: tx+log)    │ created_at       │
                         └──────────────────┘
                                │
                  ┌─────────────┼─────────────┐
                  │             │             │
                  ▼             ▼             ▼
         ┌────────────┐  ┌────────────┐  ┌────────────┐
         │ ImageJob   │  │ IPFSRecord │  │ RevealTx   │
         │────────────│  │────────────│  │────────────│
         │ id         │  │ id         │  │ id         │
         │ token_id   │  │ token_id   │  │ token_ids[]│
         │ service    │  │ record_type│  │ tx_hash    │
         │ status     │  │ cid        │  │ block_num  │
         │ job_id     │  │ status     │  │ gas_price  │
         │ retry_count│  │ retry_count│  │ created_at │
         │ error_data │  │ error_data │  └────────────┘
         │ created_at │  │ created_at │
         └────────────┘  └────────────┘

┌────────────────┐
│  SystemState   │
│────────────────│
│ key (PK)       │
│ state_value    │
│ updated_at     │
└────────────────┘
```

## Entities

### Author

**Purpose**: Represents an NFT creator with wallet address and AI prompt for image generation.

**Table Name**: `authors`

**Fields**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Auto-generated UUID |
| wallet_address | VARCHAR(42) | UNIQUE, NOT NULL | Ethereum address (0x...) |
| twitter_handle | VARCHAR(255) | NULLABLE | Twitter username (without @) |
| farcaster_handle | VARCHAR(255) | NULLABLE | Farcaster username |
| prompt_text | TEXT | NOT NULL | AI image generation prompt |
| created_at | TIMESTAMP | NOT NULL | UTC timestamp of creation |

**Indexes**:
- PRIMARY KEY on `id`
- UNIQUE INDEX on `wallet_address`

**Validation Rules**:
- `wallet_address` must match pattern `^0x[a-fA-F0-9]{40}$`
- `prompt_text` must be 10-500 characters
- At least one of `twitter_handle` or `farcaster_handle` should be present (soft requirement, not enforced)

**Relationships**:
- One author → Many tokens (one-to-many via `author_id` FK)

---

### Token

**Purpose**: Represents a minted NFT with lifecycle status tracking.

**Table Name**: `tokens_s0`

**Fields**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Auto-generated UUID |
| token_id | INTEGER | UNIQUE, NOT NULL | On-chain token ID |
| author_id | UUID | FOREIGN KEY, NOT NULL | References authors(id) |
| minter_address | VARCHAR(42) | NOT NULL | Address that minted this token |
| status | ENUM | NOT NULL | Lifecycle status (see below) |
| mint_timestamp | TIMESTAMP | NOT NULL | UTC timestamp from blockchain |
| image_cid | VARCHAR(255) | NULLABLE | IPFS CID of generated image |
| metadata_cid | VARCHAR(255) | NULLABLE | IPFS CID of metadata JSON |
| error_data | JSONB | NULLABLE | Error details if status = failed |
| created_at | TIMESTAMP | NOT NULL | UTC timestamp of record creation |

**Status Enum Values**:
- `detected` - Mint event received, not yet processed
- `generating` - Image generation in progress
- `uploading` - IPFS upload in progress
- `ready` - Metadata uploaded, ready for reveal
- `revealed` - Reveal transaction confirmed on-chain
- `failed` - Processing failed (see error_data)

**Indexes**:
- PRIMARY KEY on `id`
- UNIQUE INDEX on `token_id`
- INDEX on `(status, mint_timestamp)` for worker polling queries
- INDEX on `author_id` for author lookups

**Validation Rules**:
- `minter_address` must match pattern `^0x[a-fA-F0-9]{40}$`
- `status` must be one of enum values
- `image_cid` and `metadata_cid` required when status = `ready` or `revealed`

**State Transitions** (enforced by domain methods):
```
detected → generating → uploading → ready → revealed
    ↓          ↓            ↓         ↓
             failed ←────────────────┘
```

**Relationships**:
- Many tokens → One author (many-to-one via `author_id` FK)
- One token → Many image jobs (one-to-many)
- One token → Many IPFS records (one-to-many)
- Many tokens → Many reveal transactions (many-to-many via `token_ids` array)

---

### MintEvent

**Purpose**: Tracks blockchain mint events for deduplication and recovery.

**Table Name**: `mint_events`

**Fields**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Auto-generated UUID |
| tx_hash | VARCHAR(66) | NOT NULL | Transaction hash (0x...) |
| log_index | INTEGER | NOT NULL | Log index within transaction |
| block_number | INTEGER | NOT NULL | Block number |
| block_timestamp | TIMESTAMP | NOT NULL | UTC timestamp from block |
| token_id | INTEGER | NOT NULL | On-chain token ID |
| detected_at | TIMESTAMP | NOT NULL | UTC timestamp when event detected |

**Indexes**:
- PRIMARY KEY on `id`
- UNIQUE INDEX on `(tx_hash, log_index)` for deduplication
- INDEX on `block_number` for recovery queries

**Validation Rules**:
- `tx_hash` must match pattern `^0x[a-fA-F0-9]{64}$`
- `log_index` must be >= 0
- `block_number` must be > 0

**Relationships**:
- No foreign keys (denormalized for recovery)

---

### ImageGenerationJob

**Purpose**: Tracks image generation attempts for retry and debugging.

**Table Name**: `image_generation_jobs`

**Fields**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Auto-generated UUID |
| token_id | UUID | FOREIGN KEY, NOT NULL | References tokens_s0(id) |
| service | VARCHAR(50) | NOT NULL | Service used (replicate, selfhosted) |
| status | VARCHAR(50) | NOT NULL | Job status (pending, running, completed, failed) |
| external_job_id | VARCHAR(255) | NULLABLE | External service job ID |
| retry_count | INTEGER | NOT NULL, DEFAULT 0 | Number of retry attempts |
| error_data | JSONB | NULLABLE | Error details if status = failed |
| created_at | TIMESTAMP | NOT NULL | UTC timestamp of job creation |
| completed_at | TIMESTAMP | NULLABLE | UTC timestamp of completion |

**Indexes**:
- PRIMARY KEY on `id`
- INDEX on `token_id` for token lookup
- INDEX on `(service, status)` for monitoring queries

**Validation Rules**:
- `service` must be one of: `replicate`, `selfhosted`
- `status` must be one of: `pending`, `running`, `completed`, `failed`
- `retry_count` must be >= 0

**Relationships**:
- Many jobs → One token (many-to-one via `token_id` FK)

---

### IPFSUploadRecord

**Purpose**: Tracks IPFS upload attempts for images and metadata.

**Table Name**: `ipfs_upload_records`

**Fields**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Auto-generated UUID |
| token_id | UUID | FOREIGN KEY, NOT NULL | References tokens_s0(id) |
| record_type | VARCHAR(50) | NOT NULL | Type (image, metadata) |
| cid | VARCHAR(255) | NULLABLE | IPFS CID if successful |
| status | VARCHAR(50) | NOT NULL | Upload status (pending, uploading, completed, failed) |
| retry_count | INTEGER | NOT NULL, DEFAULT 0 | Number of retry attempts |
| error_data | JSONB | NULLABLE | Error details if status = failed |
| created_at | TIMESTAMP | NOT NULL | UTC timestamp of upload attempt |
| completed_at | TIMESTAMP | NULLABLE | UTC timestamp of completion |

**Indexes**:
- PRIMARY KEY on `id`
- INDEX on `token_id` for token lookup
- INDEX on `(record_type, status)` for monitoring

**Validation Rules**:
- `record_type` must be one of: `image`, `metadata`
- `status` must be one of: `pending`, `uploading`, `completed`, `failed`
- `retry_count` must be >= 0
- `cid` required when status = `completed`

**Relationships**:
- Many records → One token (many-to-one via `token_id` FK)

---

### RevealTransaction

**Purpose**: Tracks batch reveal transactions for gas optimization.

**Table Name**: `reveal_transactions`

**Fields**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Auto-generated UUID |
| token_ids | UUID[] | NOT NULL | Array of token UUIDs revealed together |
| tx_hash | VARCHAR(66) | NULLABLE | Transaction hash (0x...) once confirmed |
| block_number | INTEGER | NULLABLE | Block number once confirmed |
| gas_price_gwei | DECIMAL(20, 9) | NULLABLE | Gas price paid in Gwei |
| status | VARCHAR(50) | NOT NULL | Transaction status (pending, sent, confirmed, failed) |
| created_at | TIMESTAMP | NOT NULL | UTC timestamp of transaction creation |
| confirmed_at | TIMESTAMP | NULLABLE | UTC timestamp of confirmation |

**Indexes**:
- PRIMARY KEY on `id`
- INDEX on `tx_hash` for transaction lookup
- INDEX on `status` for monitoring

**Validation Rules**:
- `token_ids` array must have 1-50 elements (batch size limits)
- `tx_hash` must match pattern `^0x[a-fA-F0-9]{64}$` when present
- `status` must be one of: `pending`, `sent`, `confirmed`, `failed`

**Relationships**:
- Many-to-many with tokens (stored as UUID array for simplicity)

**Note**: This is a simplified many-to-many using PostgreSQL array type. For MVP, this avoids junction table complexity.

---

### SystemState

**Purpose**: Singleton key-value store for operational state.

**Table Name**: `system_state`

**Fields**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| key | VARCHAR(255) | PRIMARY KEY | State key (e.g., "last_processed_block") |
| state_value | JSONB | NOT NULL | Arbitrary JSON value |
| updated_at | TIMESTAMP | NOT NULL | UTC timestamp of last update |

**Indexes**:
- PRIMARY KEY on `key`

**Common Keys**:
- `last_processed_block` - INTEGER - Last blockchain block number processed by event listener
- `reveal_worker_enabled` - BOOLEAN - Flag to enable/disable reveal worker
- `image_generation_service` - STRING - Active service ("replicate" or "selfhosted")

**Validation Rules**:
- `key` must be alphanumeric + underscores only
- `state_value` must be valid JSON

**Relationships**:
- None (singleton store)

---

## Domain Model Behavior

### Token State Transitions

State transitions are implemented as methods on the `Token` domain model:

```python
class Token(SQLModel, table=True):
    # ... fields ...

    def mark_generating(self) -> None:
        """Transition from detected to generating. Raises InvalidStateTransition if current status != detected."""
        if self.status != TokenStatus.DETECTED:
            raise InvalidStateTransition(
                f"Cannot mark generating from {self.status}. Token must be in detected state."
            )
        self.status = TokenStatus.GENERATING

    def mark_uploading(self, image_path: str) -> None:
        """Transition from generating to uploading. Requires image_path."""
        if self.status != TokenStatus.GENERATING:
            raise InvalidStateTransition(
                f"Cannot mark uploading from {self.status}. Token must be in generating state."
            )
        # image_path stored in separate table, not on token
        self.status = TokenStatus.UPLOADING

    def mark_ready(self, metadata_cid: str) -> None:
        """Transition from uploading to ready. Requires metadata CID."""
        if self.status != TokenStatus.UPLOADING:
            raise InvalidStateTransition(
                f"Cannot mark ready from {self.status}. Token must be in uploading state."
            )
        if not metadata_cid:
            raise ValueError("metadata_cid required")
        self.metadata_cid = metadata_cid
        self.status = TokenStatus.READY

    def mark_revealed(self, tx_hash: str) -> None:
        """Transition from ready to revealed. Requires transaction hash."""
        if self.status != TokenStatus.READY:
            raise InvalidStateTransition(
                f"Cannot mark revealed from {self.status}. Token must be in ready state."
            )
        if not tx_hash:
            raise ValueError("tx_hash required")
        # tx_hash stored in reveal_transactions table
        self.status = TokenStatus.REVEALED

    def mark_failed(self, error_dict: dict) -> None:
        """Transition from any non-terminal state to failed. Stores error details."""
        if self.status in (TokenStatus.REVEALED, TokenStatus.FAILED):
            raise InvalidStateTransition(
                f"Cannot mark failed from terminal state {self.status}."
            )
        self.error_data = error_dict
        self.status = TokenStatus.FAILED
```

### Custom Exceptions

```python
class InvalidStateTransition(Exception):
    """Raised when attempting an invalid token state transition."""
    pass
```

---

## Database Constraints Summary

### Foreign Keys
- `tokens_s0.author_id` → `authors.id` (ON DELETE RESTRICT)
- `image_generation_jobs.token_id` → `tokens_s0.id` (ON DELETE CASCADE)
- `ipfs_upload_records.token_id` → `tokens_s0.id` (ON DELETE CASCADE)

### Unique Constraints
- `authors.wallet_address` (UNIQUE)
- `tokens_s0.token_id` (UNIQUE)
- `mint_events(tx_hash, log_index)` (UNIQUE)

### Check Constraints
- `tokens_s0.status` IN (detected, generating, uploading, ready, revealed, failed)
- `image_generation_jobs.retry_count` >= 0
- `ipfs_upload_records.retry_count` >= 0
- `reveal_transactions.token_ids` array length BETWEEN 1 AND 50

---

## Migration Strategy

### Initial Migration (001_initial_schema.py)

1. Create ENUM types:
   - `token_status_enum` with 6 values

2. Create tables in dependency order:
   - `system_state` (no dependencies)
   - `authors` (no dependencies)
   - `tokens_s0` (depends on authors)
   - `mint_events` (no dependencies, denormalized)
   - `image_generation_jobs` (depends on tokens_s0)
   - `ipfs_upload_records` (depends on tokens_s0)
   - `reveal_transactions` (no direct FK, uses UUID array)

3. Create indexes:
   - All PRIMARY KEY indexes (automatic)
   - `tokens_s0(status, mint_timestamp)` for worker queries
   - `tokens_s0(author_id)` for author lookups
   - `mint_events(tx_hash, log_index)` for deduplication

4. Add foreign key constraints with appropriate ON DELETE actions

### Idempotency

- Use `IF NOT EXISTS` clauses
- Check enum type existence before creation
- Migration script should be runnable multiple times safely

---

## Testing Requirements

Per GLISK constitution, test only complex logic:

**Must Test**:
- Token state transition validation (all valid and invalid transitions)
- FOR UPDATE SKIP LOCKED behavior (concurrent worker coordination)
- Unique constraint violations (duplicate mint events, wallet addresses)
- JSONB field operations (storing/retrieving error_data, state_value)

**Skip Testing**:
- Simple CRUD (add, get_by_id, update non-validated fields)
- Foreign key cascade behavior (trust PostgreSQL)
- Index performance (premature optimization)

---

## Future Schema Evolution

These changes are deferred to features 003b-003e:

- **003b (Event Detection)**: No schema changes, uses existing tables
- **003c (Image Generation)**: May add fields to `image_generation_jobs` for generation parameters
- **003d (Reveal Worker)**: May add `reveal_batch_size` to `system_state`
- **003e (Admin API)**: May add `admin_users` table for authentication (TBD)

Schema is designed to be stable for MVP season.
