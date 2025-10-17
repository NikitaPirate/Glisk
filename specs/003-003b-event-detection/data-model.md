# Data Model: Mint Event Detection System

**Feature**: 003-003b-event-detection
**Created**: 2025-10-17
**Source**: Extracted from [spec.md](./spec.md) requirements

## Overview

This data model supports **detection only** - storing mint events and creating token records with `status='detected'`. No processing logic (image generation, IPFS upload) is included in this feature.

All tables already exist from **003a Backend Foundation**. This feature uses existing tables without schema changes.

## Entities

### 1. MintEvent

**Purpose**: Immutable audit trail of detected NFT mint events from blockchain.

**Table**: `mint_events` (created in 003a)

**Attributes**:
- `id` (UUID, PK) - Auto-generated
- `tx_hash` (VARCHAR(66), NOT NULL) - Transaction hash (0x + 64 hex chars)
- `log_index` (INTEGER, NOT NULL) - Position of log within transaction
- `block_number` (BIGINT, NOT NULL) - Block number where event occurred
- `token_id` (BIGINT, NOT NULL) - NFT token ID (from BatchMinted.startTokenId + offset)
- `author_wallet` (VARCHAR(42), NOT NULL) - Prompt author's wallet address (checksummed)
- `recipient` (VARCHAR(42), NOT NULL) - Minter's wallet address (checksummed)
- `detected_at` (TIMESTAMP, NOT NULL) - UTC timestamp when event was detected by system

**Constraints**:
- `UNIQUE(tx_hash, log_index)` - Prevents duplicate event processing (idempotency)
- `CHECK(tx_hash ~ '^0x[0-9a-fA-F]{64}$')` - Validates hex format
- `CHECK(author_wallet ~ '^0x[0-9a-fA-F]{40}$')` - Checksummed address
- `CHECK(recipient ~ '^0x[0-9a-fA-F]{40}$')` - Checksummed address

**Relationships**:
- No foreign keys - intentionally denormalized for audit trail
- `author_wallet` does NOT reference `authors.wallet_address` (allows historical tracking even if author deleted)

**Usage**:
- Created by: Webhook endpoint (`POST /webhooks/alchemy`) and recovery CLI (`python -m glisk.cli.recover_events`)
- Updated: Never - immutable audit trail
- Queried by: Future admin APIs, analytics

**Example**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "tx_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
  "log_index": 0,
  "block_number": 12345678,
  "token_id": 1,
  "author_wallet": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
  "recipient": "0x1234567890123456789012345678901234567890",
  "detected_at": "2025-10-17T00:30:00.000000Z"
}
```

---

### 2. Token

**Purpose**: Represents an NFT token in the system, tracking ownership and processing status.

**Table**: `tokens_s0` (created in 003a)

**Attributes**:
- `token_id` (BIGINT, PK) - NFT token ID from contract
- `current_owner` (VARCHAR(42), NOT NULL) - Current owner's wallet address (updated on transfers)
- `author_id` (UUID, FK → authors.id, NULL allowed) - Link to author who created the prompt
- `status` (ENUM, NOT NULL) - Processing status: `'detected' | 'generating' | 'uploading' | 'revealed'`
- `minted_at` (TIMESTAMP, NOT NULL) - UTC timestamp of on-chain mint
- `tx_hash` (VARCHAR(66), NOT NULL) - Transaction hash of mint transaction
- `created_at` (TIMESTAMP, NOT NULL) - UTC timestamp when record was created
- `updated_at` (TIMESTAMP, NOT NULL) - UTC timestamp when record was last updated

**Constraints**:
- `PRIMARY KEY(token_id)` - One token per ID
- `FOREIGN KEY(author_id) REFERENCES authors(id) ON DELETE SET NULL` - Preserve token if author deleted
- `CHECK(status IN ('detected', 'generating', 'uploading', 'revealed'))` - Valid statuses only
- `CHECK(current_owner ~ '^0x[0-9a-fA-F]{40}$')` - Checksummed address

**Status Transitions** (for this feature):
```
[Mint Event] → detected (INITIAL STATE - created by webhook/recovery)
```

Future features will implement:
```
detected → generating (003c: Image Generation)
generating → uploading (003d: IPFS Upload)
uploading → revealed (003d: Metadata Update)
```

**Author Lookup Logic**:
1. Query `authors` table using `MintEvent.author_wallet`
2. If found: Set `author_id = authors.id`
3. If NOT found: Use default author from config (`GLISK_DEFAULT_AUTHOR_WALLET`)

**Relationships**:
- `author_id → authors.id` (NULLABLE FK) - Link to prompt creator
- Referenced by: Future `token_metadata`, `generation_jobs` tables

**Usage**:
- Created by: Webhook endpoint and recovery CLI (same transaction as MintEvent)
- Updated by: Transfer event listener (future), processing workers (003c-003d)
- Queried by: Frontend collection pages, creator dashboards

**Example**:
```json
{
  "token_id": 1,
  "current_owner": "0x1234567890123456789012345678901234567890",
  "author_id": "660e8400-e29b-41d4-a716-446655440001",
  "status": "detected",
  "minted_at": "2025-10-17T00:30:00.000000Z",
  "tx_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
  "created_at": "2025-10-17T00:30:05.123456Z",
  "updated_at": "2025-10-17T00:30:05.123456Z"
}
```

---

### 3. SystemState

**Purpose**: Stores operational state for recovery mechanism.

**Table**: `system_state` (created in 003a)

**Attributes**:
- `key` (VARCHAR(255), PK) - State variable name
- `value` (TEXT, NOT NULL) - State variable value (stored as string)
- `updated_at` (TIMESTAMP, NOT NULL) - UTC timestamp when value was last updated

**Keys Used by This Feature**:
- `"last_processed_block"` - Block number of last successfully processed block in recovery (stored as string, e.g., `"12345678"`)

**Usage**:
- Created by: Recovery CLI on first run (if key doesn't exist)
- Updated by: Recovery CLI after each successful batch
- Queried by: Recovery CLI to resume from last checkpoint

**Example**:
```json
{
  "key": "last_processed_block",
  "value": "12345678",
  "updated_at": "2025-10-17T00:35:00.000000Z"
}
```

---

### 4. Author (Pre-existing)

**Purpose**: Represents NFT creators who register prompts.

**Table**: `authors` (created in 003a)

**Attributes** (relevant to this feature):
- `id` (UUID, PK) - Author's unique identifier
- `wallet_address` (VARCHAR(42), UNIQUE, NOT NULL) - Ethereum wallet (checksummed)
- `created_at` (TIMESTAMP, NOT NULL)

**Usage by This Feature**:
- Queried by: Webhook endpoint and recovery CLI to look up `author_id` for Token creation
- Fallback: If `wallet_address` not found, use default author from config

**Example**:
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "wallet_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
  "created_at": "2025-10-15T12:00:00.000000Z"
}
```

---

## Data Flow

### Webhook Event Detection

```
Alchemy Webhook (POST /webhooks/alchemy)
  ↓
Validate HMAC Signature
  ↓
Parse BatchMinted Event Log
  ↓
Database Transaction (UoW):
  1. Lookup Author (author_wallet → author_id)
  2. INSERT INTO mint_events (tx_hash, log_index, block_number, ...)
  3. INSERT INTO tokens_s0 (token_id, author_id, status='detected', ...)
  ↓
Commit or Rollback
  ↓
Response: 200 OK | 409 Conflict | 500 Error
```

### Event Recovery (CLI)

```
python -m glisk.cli.recover_events --from-block X
  ↓
Load last_processed_block from system_state (or use --from-block)
  ↓
Loop (paginated by block ranges):
  1. eth_getLogs(fromBlock=current, toBlock=current+1000)
  2. For each log:
     - Parse BatchMinted event
     - Database Transaction:
       * INSERT mint_events (with UNIQUE constraint)
       * INSERT tokens_s0 (with PK constraint)
       * ON CONFLICT: Skip gracefully (already processed)
  3. UPDATE system_state SET value=toBlock WHERE key='last_processed_block'
  ↓
Continue until toBlock='latest'
```

---

## Validation Rules

### MintEvent Validation

- `tx_hash`: Must match regex `^0x[0-9a-fA-F]{64}$`
- `log_index`: Must be >= 0
- `block_number`: Must be > 0
- `token_id`: Must be >= 0
- `author_wallet`: Must be valid checksummed Ethereum address
- `recipient`: Must be valid checksummed Ethereum address
- `detected_at`: Must be UTC timestamp

### Token Validation

- `token_id`: Must be >= 0
- `current_owner`: Must be valid checksummed Ethereum address
- `author_id`: Must exist in `authors` table OR NULL (if using default author)
- `status`: Must be one of: `'detected'` (only status set by this feature)
- `minted_at`: Must be UTC timestamp
- `tx_hash`: Must match regex `^0x[0-9a-fA-F]{64}$`

---

## Repository Methods (from 003a)

### MintEventRepository

- `create(mint_event: MintEvent) -> MintEvent` - Insert new event (raises on UNIQUE constraint violation)
- `get_by_tx_hash_and_log_index(tx_hash: str, log_index: int) -> MintEvent | None` - Check if event exists

### TokenRepository

- `create(token: Token) -> Token` - Insert new token (raises on PK constraint violation)
- `get_by_id(token_id: int) -> Token | None` - Fetch token by ID
- `update(token: Token) -> Token` - Update token (used by future features)

### AuthorRepository

- `get_by_wallet(wallet_address: str) -> Author | None` - Look up author by wallet

### SystemStateRepository

- `get(key: str) -> str | None` - Fetch state value
- `set(key: str, value: str) -> None` - Upsert state value

---

## Configuration

### Environment Variables (added to `core/config.py`)

```python
class Config(BaseSettings):
    # Existing config from 003a...

    # Alchemy integration (new)
    alchemy_api_key: str
    alchemy_webhook_secret: str
    glisk_nft_contract_address: str  # Checksummed address
    network: str  # "BASE_SEPOLIA" or "BASE_MAINNET"
    glisk_default_author_wallet: str  # Checksummed address
```

### Example `.env` values

```bash
ALCHEMY_API_KEY=your_api_key_here
ALCHEMY_WEBHOOK_SECRET=your_signing_key_from_alchemy_dashboard
GLISK_NFT_CONTRACT_ADDRESS=0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0
NETWORK=BASE_SEPOLIA
GLISK_DEFAULT_AUTHOR_WALLET=0x0000000000000000000000000000000000000001
```

---

## Notes

### No Schema Changes Required

All tables were created in **003a Backend Foundation**. This feature only **uses** existing tables:
- `mint_events` - Stores detected events
- `tokens_s0` - Stores token records with `status='detected'`
- `authors` - Queried for author lookup
- `system_state` - Tracks recovery progress

### Idempotency Strategy

**Database-level idempotency** via constraints:
- `mint_events.UNIQUE(tx_hash, log_index)` - Prevents duplicate event storage
- `tokens_s0.PRIMARY KEY(token_id)` - Prevents duplicate token creation

**Application-level handling**:
- Webhook: Catch `IntegrityError`, return `409 Conflict`
- Recovery CLI: Catch `IntegrityError`, skip and continue

### UTC Enforcement

Per Constitution v1.1.0:
- ALL timestamps stored as UTC (no timezone-aware PostgreSQL types)
- Application imports `glisk.core.timezone` at startup to set `TZ=UTC`
- Use `datetime.utcnow()` for all timestamp generation

### Default Author Fallback

When `author_wallet` not found in `authors` table:
1. Query `authors` table using `GLISK_DEFAULT_AUTHOR_WALLET`
2. Use that author's `id` as `author_id`
3. This ensures all tokens have a valid `author_id` (or NULL if default author also missing)

**Rationale**: Enables permissionless minting while maintaining referential integrity. Default author can be a system account or "Unknown Creator" placeholder.
