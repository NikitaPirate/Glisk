# Research Notes: Author Profile Management

**Date**: 2025-10-20
**Feature**: Author Profile Management (006)
**Purpose**: Resolve technical unknowns identified in Technical Context

## Research Tasks

### 1. Wallet Signature Verification Library

**Question**: Which Python library should we use for EIP-191 signature verification?

**Decision**: Use `eth-account` (already a dependency via web3.py)

**Rationale**:
- Already installed as transitive dependency of web3.py (no new dependency)
- Provides `Account.recover_message()` for EIP-191 signature verification
- Well-maintained by Ethereum Foundation
- Used by web3.py internally for transaction signing
- Supports both legacy (prefix: "\x19Ethereum Signed Message:\n") and EIP-191 standard messages

**Implementation Pattern**:
```python
from eth_account.messages import encode_defunct
from eth_account import Account

def verify_wallet_signature(wallet_address: str, message: str, signature: str) -> bool:
    """Verify EIP-191 signature matches wallet address."""
    message_hash = encode_defunct(text=message)
    recovered_address = Account.recover_message(message_hash, signature=signature)
    return recovered_address.lower() == wallet_address.lower()
```

**Alternatives Considered**:
- **eth_utils**: Lower-level, requires manual message encoding
- **eciespy**: Focused on encryption, not signature verification
- **pycryptodome**: General crypto library, requires more boilerplate

**Reference**: https://eth-account.readthedocs.io/en/stable/eth_account.html#module-eth_account.messages

---

### 2. Database Schema Validation

**Question**: Does the existing `authors` table schema support all requirements?

**Decision**: Yes, existing schema is sufficient. No migration needed.

**Current Schema** (from `backend/src/glisk/models/author.py`):
```python
class Author(SQLModel, table=True):
    __tablename__ = "authors"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    wallet_address: str = Field(max_length=42, unique=True, index=True)  # ✅ Unique constraint
    twitter_handle: Optional[str] = Field(default=None, max_length=255)  # ℹ️ Out of scope
    farcaster_handle: Optional[str] = Field(default=None, max_length=255)  # ℹ️ Out of scope
    prompt_text: str  # ✅ TEXT field (no max_length = PostgreSQL TEXT type)
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

**Validation Results**:
- ✅ **FR-003**: `wallet_address` has UNIQUE constraint (prevents duplicate authors)
- ✅ **FR-004**: `prompt_text` validation exists in model (1-1000 characters via `@field_validator`)
- ✅ **FR-012**: UPDATE operation supported (no need to delete/recreate)
- ✅ **Case-insensitive lookup**: Repository already uses `func.lower()` for wallet queries
- ✅ **Indexing**: `wallet_address` is indexed for fast lookups

**Repository Methods**:
- `get_by_wallet(wallet_address)`: Case-insensitive lookup ✅
- `add(author)`: Create new author ✅
- Need to add: `update_prompt(wallet_address, new_prompt)` (simple UPDATE query)

**No Migration Required**: All required fields exist and are correctly configured.

---

### 3. Frontend Signature Flow

**Question**: What is the standard pattern for wallet signature requests in wagmi?

**Decision**: Use `useSignMessage` hook with EIP-191 message format

**Implementation Pattern**:
```typescript
import { useSignMessage } from 'wagmi'

const { signMessage, data: signature, error } = useSignMessage()

// Trigger signature on prompt save
const handleSave = async () => {
  const message = `Sign this message to update your GLISK prompt.\n\nWallet: ${address}\nTimestamp: ${Date.now()}`
  await signMessage({ message })

  // Send signature to backend for verification
  await fetch('/api/authors/prompt', {
    method: 'POST',
    body: JSON.stringify({ wallet_address: address, prompt_text, signature })
  })
}
```

**Message Format**:
- Include wallet address in message (prevents signature replay across wallets)
- Include timestamp (optional: can implement expiration window)
- Human-readable message explains what user is authorizing

**Alternatives Considered**:
- **EIP-712 (typed data)**: Overkill for simple authorization, adds complexity
- **Personal sign**: Same as useSignMessage (uses EIP-191 under the hood)

**Reference**: https://wagmi.sh/react/api/hooks/useSignMessage

---

### 4. Error Handling Patterns

**Question**: How should we handle different failure modes for signature verification and blockchain calls?

**Decision**: Use structured error responses with actionable messages per FR-011

**Backend Error Categories**:
```python
# 400 Bad Request - Client error
- Invalid signature format (not hex string)
- Prompt validation failure (empty, >1000 chars)
- Signature verification failed (wrong wallet)

# 401 Unauthorized - Authentication error
- Missing signature
- Expired signature (if timestamp validation added)

# 500 Internal Server Error - Server error
- Database connection failure
- Unexpected exception
```

**Frontend Error Handling**:
```typescript
// Signature rejection
if (error?.name === 'UserRejectedRequestError') {
  setError('Signature cancelled. Your prompt was not saved.')
  return
}

// Network error
if (error?.message?.includes('fetch')) {
  setError('Network error. Please check your connection and try again.')
  return
}

// Validation error (from backend 400 response)
const errorData = await response.json()
setError(errorData.detail || 'Failed to save prompt')
```

**Actionable Error Messages** (examples):
- ❌ "Error 400" → ✅ "Prompt must be between 1 and 1000 characters"
- ❌ "Unauthorized" → ✅ "Signature verification failed. Please ensure you're using the correct wallet."
- ❌ "Transaction failed" → ✅ "Claim failed. Check that you have enough ETH for gas fees and try again."

---

### 5. Blockchain RPC Integration

**Question**: How should frontend query `authorClaimable` mapping for balance display?

**Decision**: Use `useReadContract` hook (already established pattern in CreatorMintPage.tsx)

**Implementation Pattern**:
```typescript
import { useReadContract } from 'wagmi'
import { CONTRACT_ADDRESS, GLISK_NFT_ABI } from '@/lib/contract'
import { formatEther } from 'viem'

const { data: claimableWei, isLoading, error } = useReadContract({
  address: CONTRACT_ADDRESS,
  abi: GLISK_NFT_ABI,
  functionName: 'authorClaimable',
  args: [authorAddress],
}) as { data: bigint | undefined; isLoading: boolean; error: Error | null }

// Convert wei to ETH for display
const claimableEth = claimableWei ? formatEther(claimableWei) : '0.00'
```

**ABI Addition Required**:
```json
{
  "inputs": [{"name": "", "type": "address"}],
  "name": "authorClaimable",
  "outputs": [{"name": "", "type": "uint256"}],
  "stateMutability": "view",
  "type": "function"
}
```

**Claim Transaction Pattern**:
```typescript
import { useWriteContract, useWaitForTransactionReceipt } from 'wagmi'

const { writeContract, data: hash } = useWriteContract()
const { isLoading: isConfirming, isSuccess } = useWaitForTransactionReceipt({ hash })

const handleClaim = () => {
  writeContract({
    address: CONTRACT_ADDRESS,
    abi: GLISK_NFT_ABI,
    functionName: 'claimAuthorRewards',
  })
}
```

**Existing Pattern**: Matches `CreatorMintPage.tsx` implementation (read `mintPrice`, write `mint`)

---

## Summary of Decisions

| Unknown | Decision | Impact |
|---------|----------|--------|
| Signature library | `eth-account` (existing dependency) | No new dependencies, standard EIP-191 support |
| Database schema | No changes needed | Faster implementation, no migration risk |
| Frontend signature | `useSignMessage` hook | Standard wagmi pattern, simple integration |
| Error handling | Structured errors with actionable messages | Better UX, easier debugging |
| Blockchain RPC | `useReadContract` + `useWriteContract` | Consistent with existing code patterns |

## Security Considerations

1. **Signature Replay Prevention**:
   - Include wallet address in signed message (prevents cross-wallet replay)
   - Optional: Add timestamp + expiration window (prevents time-based replay)

2. **Constant-Time Comparison**:
   - Use `recovered_address.lower() == wallet_address.lower()` (Python string comparison is constant-time for equal-length strings)
   - Ethereum addresses are fixed length (42 chars including 0x prefix)

3. **Input Validation**:
   - Backend validates all inputs (wallet format, prompt length, signature format)
   - Frontend provides client-side validation for UX (not security)

4. **CORS Configuration**:
   - Backend must allow frontend origin for `/api/authors/*` endpoints
   - Already configured in existing FastAPI app (check `backend/src/glisk/app.py`)

## Open Questions (None)

All NEEDS CLARIFICATION items resolved. Ready for Phase 1 (data model + contracts).
