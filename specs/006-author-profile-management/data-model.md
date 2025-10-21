# Data Model: Author Profile Management

**Feature**: Author Profile Management (006)
**Date**: 2025-10-20
**Status**: Design

## Overview

This feature reuses the existing `authors` table with no schema changes. All required fields (wallet_address, prompt_text) already exist with appropriate constraints and validation.

## Entities

### Author (Existing - No Changes)

**Table**: `authors`
**Source**: `backend/src/glisk/models/author.py`

**Purpose**: Stores creator profiles with wallet address and AI generation prompt

**Fields**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY, AUTO-GENERATED | Internal unique identifier |
| `wallet_address` | VARCHAR(42) | UNIQUE, NOT NULL, INDEXED | Ethereum wallet address (0x + 40 hex chars) |
| `twitter_handle` | VARCHAR(255) | NULL | Twitter handle (out of scope for this feature) |
| `farcaster_handle` | VARCHAR(255) | NULL | Farcaster handle (out of scope for this feature) |
| `prompt_text` | TEXT | NOT NULL | AI generation prompt (1-1000 characters validated at app level) |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Record creation timestamp (UTC) |

**Indexes**:
- `wallet_address` (UNIQUE index for fast case-insensitive lookups)

**Validation Rules** (enforced in Python model):
```python
@field_validator("wallet_address")
def validate_wallet_address(cls, v: str) -> str:
    """Validate Ethereum wallet address format (0x + 40 hex characters)."""
    if not v.startswith("0x") or len(v) != 42:
        raise ValueError("Wallet address must be in format 0x followed by 40 hex characters")
    try:
        int(v[2:], 16)  # Verify hex
    except ValueError:
        raise ValueError("Wallet address must contain valid hexadecimal characters")
    return v

@field_validator("prompt_text")
def validate_prompt_text(cls, v: str) -> str:
    """Validate AI prompt text length (1-1000 characters)."""
    if len(v) < 1 or len(v) > 1000:
        raise ValueError("Prompt text must be between 1 and 1000 characters")
    return v
```

**Relationships**: None (standalone entity)

**State Transitions**: None (simple CRUD operations)

---

### Claimable Rewards (Smart Contract State - Read-Only)

**Storage**: On-chain mapping in `GliskNFT.sol`
**Access**: Read-only from backend/frontend

**Mapping**:
```solidity
mapping(address => uint256) public authorClaimable;
```

**Purpose**: Tracks accumulated ETH rewards for each prompt author

**Update Triggers** (handled by smart contract, not this feature):
- **Increment**: When user mints NFT with this author's address (50% of mint price added)
- **Reset to 0**: When author calls `claimAuthorRewards()` (transfers ETH to author wallet)

**Query Pattern**:
```typescript
// Frontend: Read claimable balance
const { data: claimableWei } = useReadContract({
  address: CONTRACT_ADDRESS,
  abi: GLISK_NFT_ABI,
  functionName: 'authorClaimable',
  args: [authorAddress],
})
```

**No Backend Storage**: Balance is never stored in PostgreSQL (always queried from contract)

---

## Data Flow Diagrams

### Prompt Update Flow

```
┌─────────────┐
│   Creator   │
│   Wallet    │
└──────┬──────┘
       │
       │ 1. Connect wallet (wagmi)
       ▼
┌─────────────────────────────┐
│   Frontend (Dashboard)      │
│                             │
│  - Show prompt status       │
│  - Enter prompt text        │
│  - Click "Save"             │
└──────┬──────────────────────┘
       │
       │ 2. Sign message (EIP-191)
       │    Message: "Update GLISK prompt for {wallet}"
       ▼
┌─────────────────────────────┐
│   Wallet Provider           │
│   (MetaMask/WalletConnect)  │
└──────┬──────────────────────┘
       │
       │ 3. Return signature
       ▼
┌─────────────────────────────┐
│   Frontend                  │
│                             │
│  POST /api/authors/prompt   │
│  Body: {                    │
│    wallet_address,          │
│    prompt_text,             │
│    signature                │
│  }                          │
└──────┬──────────────────────┘
       │
       │ 4. HTTP request
       ▼
┌─────────────────────────────┐
│   Backend (FastAPI)         │
│                             │
│  - Verify signature         │
│  - Validate prompt          │
│  - Update/Insert author     │
└──────┬──────────────────────┘
       │
       │ 5. SQL: INSERT or UPDATE
       ▼
┌─────────────────────────────┐
│   PostgreSQL                │
│                             │
│   authors table:            │
│   wallet_address (UNIQUE)   │
│   prompt_text               │
└─────────────────────────────┘
```

**Key Points**:
- Signature verification happens before database write
- `wallet_address` UNIQUE constraint prevents duplicates (UPSERT logic in repository)
- Case-insensitive wallet lookup (`func.lower()`) prevents duplicate authors
- Prompt text is never returned to frontend (stored for backend image generation only)

---

### Rewards Claim Flow

```
┌─────────────┐
│   Creator   │
│   Wallet    │
└──────┬──────┘
       │
       │ 1. Connect wallet
       ▼
┌─────────────────────────────┐
│   Frontend (Dashboard)      │
│                             │
│  - Query authorClaimable    │
│  - Display balance in ETH   │
└──────┬──────────────────────┘
       │
       │ 2. Read contract state
       ▼
┌─────────────────────────────┐
│   Smart Contract (RPC)      │
│                             │
│   authorClaimable[address]  │
│   → returns uint256 (wei)   │
└──────┬──────────────────────┘
       │
       │ 3. Balance = X ETH (displayed)
       │
       │ User clicks "Claim Rewards"
       ▼
┌─────────────────────────────┐
│   Frontend                  │
│                             │
│  writeContract({            │
│    functionName:            │
│      'claimAuthorRewards'   │
│  })                         │
└──────┬──────────────────────┘
       │
       │ 4. Send transaction
       ▼
┌─────────────────────────────┐
│   Wallet Provider           │
│   (MetaMask/WalletConnect)  │
│                             │
│  - Estimate gas             │
│  - Request user approval    │
└──────┬──────────────────────┘
       │
       │ 5. User approves tx
       ▼
┌─────────────────────────────┐
│   Smart Contract (On-Chain) │
│                             │
│  claimAuthorRewards():      │
│   - Read authorClaimable    │
│   - Transfer ETH to caller  │
│   - Set balance to 0        │
└──────┬──────────────────────┘
       │
       │ 6. Emit AuthorClaimed event
       │    Transaction confirmed
       ▼
┌─────────────────────────────┐
│   Frontend                  │
│                             │
│  - Wait for receipt         │
│  - Show success message     │
│  - Re-query balance (now 0) │
└─────────────────────────────┘
```

**Key Points**:
- No backend involvement in claim flow (direct wallet → contract interaction)
- Balance is never cached (always fresh from contract)
- Transaction failures are handled at frontend (gas errors, rejections, reverts)

---

## Repository Methods

### AuthorRepository (Existing + New Method)

**Existing Methods** (no changes):
```python
async def get_by_id(author_id: UUID) -> Author | None
async def get_by_wallet(wallet_address: str) -> Author | None  # Case-insensitive
async def add(author: Author) -> Author
async def list_all(limit: int, offset: int) -> list[Author]
```

**New Method** (to be added):
```python
async def update_prompt(wallet_address: str, new_prompt: str) -> Author:
    """Update prompt for existing author.

    Args:
        wallet_address: Author's wallet (case-insensitive)
        new_prompt: New prompt text (must pass validation)

    Returns:
        Updated author record

    Raises:
        ValueError: If author not found
    """
    author = await self.get_by_wallet(wallet_address)
    if not author:
        raise ValueError(f"Author not found: {wallet_address}")

    author.prompt_text = new_prompt  # Triggers validation
    await self.session.flush()
    return author
```

**Alternative**: Use UPSERT logic (INSERT ... ON CONFLICT UPDATE) for create-or-update in single query

---

## API Request/Response Schemas

### Update Prompt Request

**Endpoint**: `POST /api/authors/prompt`

**Request Body**:
```json
{
  "wallet_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
  "prompt_text": "Surreal neon landscapes with futuristic architecture",
  "signature": "0x1234567890abcdef..."
}
```

**Validation Rules**:
- `wallet_address`: Must be valid Ethereum address (0x + 40 hex)
- `prompt_text`: 1-1000 characters
- `signature`: Hex string, recoverable EIP-191 signature

**Success Response** (200 OK):
```json
{
  "success": true,
  "has_prompt": true
}
```

**Response Schema**:

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Always `true` for successful saves |
| `has_prompt` | boolean | Always `true` after save |

**Note**: Prompt text is never echoed back. It is stored in database for backend image generation only.

**Error Responses**:
```json
// 400 Bad Request - Invalid signature
{
  "detail": "Signature verification failed. Please ensure you're using the correct wallet."
}

// 400 Bad Request - Validation error
{
  "detail": "Prompt text must be between 1 and 1000 characters"
}

// 401 Unauthorized - Missing signature
{
  "detail": "Signature required for authentication"
}
```

---

### Check Author Prompt Status

**Endpoint**: `GET /api/authors/{wallet_address}`

**Path Parameters**:
- `wallet_address`: Ethereum address (case-insensitive)

**Success Response** (200 OK):
```json
{
  "has_prompt": true
}
```

**Response Schema**:

| Field | Type | Description |
|-------|------|-------------|
| `has_prompt` | boolean | `true` if author has configured a prompt, `false` otherwise |

**Note**: Always returns 200 OK. Returns `{"has_prompt": false}` for non-existent authors (no 404 error).

---

## Security Considerations

### Signature Verification

**Message Format**:
```
Update GLISK prompt for wallet: {wallet_address}
Timestamp: {unix_timestamp_ms}
```

**Verification Steps**:
1. Decode signature (hex → bytes)
2. Recover signer address from message + signature (EIP-191)
3. Compare recovered address with claimed wallet_address (case-insensitive)
4. Optional: Validate timestamp is within acceptable window (e.g., 5 minutes)

**Implementation**:
```python
from eth_account.messages import encode_defunct
from eth_account import Account

def verify_signature(wallet_address: str, message: str, signature: str) -> bool:
    message_hash = encode_defunct(text=message)
    recovered_address = Account.recover_message(message_hash, signature=signature)
    return recovered_address.lower() == wallet_address.lower()
```

### SQL Injection Prevention

- ✅ All queries use SQLAlchemy ORM (parameterized queries)
- ✅ No raw SQL with user input
- ✅ Pydantic validation sanitizes inputs before database access

### Race Conditions

- ✅ `wallet_address` UNIQUE constraint prevents duplicate authors
- ✅ PostgreSQL handles concurrent UPDATE/INSERT via MVCC
- ✅ No manual locking needed for this feature

---

## Migration Plan

**Required Migrations**: None

**Verification Steps**:
1. Confirm `authors` table exists with correct schema
2. Confirm `wallet_address` UNIQUE constraint is active
3. Confirm `wallet_address` index exists
4. Test case-insensitive lookup: `func.lower(Author.wallet_address) == func.lower(input)`

**Rollback Plan**: N/A (no schema changes)

---

## Testing Data Scenarios

### Valid Test Cases

1. **Create new author**:
   - Wallet: `0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0`
   - Prompt: `"Minimalist geometric art with pastel colors"`
   - Expected: Author created, prompt saved

2. **Update existing author**:
   - Wallet: `0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0` (existing)
   - New prompt: `"Abstract expressionism with bold contrasts"`
   - Expected: Prompt updated, no duplicate author created

3. **Case-insensitive wallet lookup**:
   - Create with: `0xAbCdEf1234567890AbCdEf1234567890AbCdEf12`
   - Query with: `0xabcdef1234567890abcdef1234567890abcdef12`
   - Expected: Same author returned

### Invalid Test Cases

1. **Empty prompt**: `""` → 400 error
2. **Prompt too long**: `"a" * 1001` → 400 error
3. **Invalid wallet**: `"not-a-wallet"` → 400 error
4. **Wrong signature**: Signature from different wallet → 400 error
5. **Missing signature**: No signature provided → 401 error

### Edge Cases

1. **Prompt with emojis**: `"🌈 Rainbow landscapes 🦄"` → Should save successfully to database (UTF-8 TEXT field)
2. **Prompt with newlines**: `"Line 1\nLine 2\nLine 3"` → Should save successfully to database
3. **Prompt with special chars**: `"Art & <Design> 'with' \"quotes\""` → Should save successfully (PostgreSQL TEXT handles escaping)
4. **Concurrent updates**: Two requests update same author simultaneously → One succeeds, PostgreSQL handles conflict
5. **Query non-existent author**: GET request for wallet with no prompt → Returns `{"has_prompt": false}` (not 404)

---

## Performance Considerations

**Query Optimization**:
- `wallet_address` is indexed → O(log n) lookup time
- Case-insensitive search uses indexed column with `func.lower()` → PostgreSQL can use functional index if needed
- No joins required (standalone table)

**Expected Load**:
- ~100-1000 authors in Season 0
- ~10-50 concurrent dashboard users
- Prompt updates: <100/day
- Query latency target: <100ms p95 (database only, excluding signature verification)

**Scalability**:
- Current design scales to 100K+ authors without changes
- If >1M authors needed, consider partitioning by wallet address prefix

---

## Summary

- ✅ **No schema changes**: Existing `authors` table supports all requirements
- ✅ **Simple data model**: Single table with straightforward CRUD operations
- ✅ **Secure**: Wallet signature verification prevents unauthorized updates
- ✅ **Performant**: Indexed lookups, no complex queries
- ✅ **Testable**: Clear validation rules and error cases
