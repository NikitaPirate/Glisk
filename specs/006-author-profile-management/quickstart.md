# Quickstart Guide: Author Profile Management

**Feature**: Author Profile Management (006)
**Audience**: Developers implementing this feature
**Time**: 10 minutes to setup and test

## Prerequisites

Before starting, ensure you have:

- [x] GLISK development environment running (backend + frontend)
- [x] PostgreSQL database with `authors` table (from previous features)
- [x] MetaMask or compatible wallet extension installed
- [x] Base Sepolia testnet ETH for gas fees (optional for testing claim flow)

## Quick Overview

This feature adds two main capabilities:

1. **Prompt Management**: Authors can set/update their AI generation prompt via `/creator-dashboard` page
2. **Reward Claiming**: Authors can claim accumulated ETH rewards from the smart contract

**Implementation Timeline**: ~2-3 days for full implementation

---

## Setup Steps

### 1. Verify Database Schema

The `authors` table should already exist from previous features. Verify it has the required fields:

```bash
# Connect to PostgreSQL
docker exec backend-postgres-1 psql -U glisk -d glisk

# Verify schema
\d authors
```

**Expected Output**:
```
                                    Table "public.authors"
      Column       |            Type             | Collation | Nullable |      Default
-------------------+-----------------------------+-----------+----------+-------------------
 id                | uuid                        |           | not null |
 wallet_address    | character varying(42)       |           | not null |
 twitter_handle    | character varying(255)      |           |          |
 farcaster_handle  | character varying(255)      |           |          |
 prompt_text       | text                        |           | not null |
 created_at        | timestamp without time zone |           | not null | CURRENT_TIMESTAMP

Indexes:
    "authors_pkey" PRIMARY KEY, btree (id)
    "authors_wallet_address_key" UNIQUE CONSTRAINT, btree (wallet_address)
    "ix_authors_wallet_address" btree (wallet_address)
```

✅ If output matches, proceed. No migration needed.

---

### 2. Backend Implementation

#### Step 2.1: Create Signature Verification Service

Create `backend/src/glisk/services/wallet_signature.py`:

```python
"""EIP-191 wallet signature verification service."""

from eth_account.messages import encode_defunct
from eth_account import Account


class SignatureVerificationError(Exception):
    """Raised when signature verification fails."""
    pass


def verify_wallet_signature(wallet_address: str, message: str, signature: str) -> bool:
    """Verify EIP-191 signature matches wallet address.

    Args:
        wallet_address: Expected signer address (0x...)
        message: Plain text message that was signed
        signature: Hex-encoded signature (0x...)

    Returns:
        True if signature is valid and matches wallet_address

    Raises:
        SignatureVerificationError: If signature is invalid or doesn't match
    """
    try:
        # Encode message with EIP-191 prefix
        message_hash = encode_defunct(text=message)

        # Recover signer address from signature
        recovered_address = Account.recover_message(message_hash, signature=signature)

        # Compare addresses (case-insensitive)
        if recovered_address.lower() != wallet_address.lower():
            raise SignatureVerificationError(
                f"Signature verification failed. Expected {wallet_address}, got {recovered_address}"
            )

        return True
    except SignatureVerificationError:
        raise
    except Exception as e:
        raise SignatureVerificationError(f"Invalid signature format: {e}")
```

#### Step 2.2: Add Repository Method

Update `backend/src/glisk/repositories/author.py`:

```python
async def upsert_author_prompt(self, wallet_address: str, prompt_text: str) -> Author:
    """Create or update author's prompt (UPSERT logic).

    Args:
        wallet_address: Author's wallet address (case-insensitive)
        prompt_text: New prompt text

    Returns:
        Author record (created or updated)
    """
    # Try to find existing author
    existing = await self.get_by_wallet(wallet_address)

    if existing:
        # Update existing
        existing.prompt_text = prompt_text  # Triggers validation
        await self.session.flush()
        return existing
    else:
        # Create new
        new_author = Author(
            wallet_address=wallet_address,
            prompt_text=prompt_text,
        )
        return await self.add(new_author)
```

#### Step 2.3: Create API Routes

Create `backend/src/glisk/api/routes/authors.py`:

```python
"""Author API routes for GLISK backend."""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from glisk.repositories.author import AuthorRepository
from glisk.services.wallet_signature import verify_wallet_signature, SignatureVerificationError
from glisk.core.dependencies import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/authors", tags=["authors"])


class UpdatePromptRequest(BaseModel):
    """Request model for updating author prompt."""
    wallet_address: str = Field(..., min_length=42, max_length=42)
    prompt_text: str = Field(..., min_length=1, max_length=1000)
    signature: str = Field(..., pattern=r"^0x[a-fA-F0-9]+$")
    message: str


class AuthorResponse(BaseModel):
    """Response model for author data."""
    id: str
    wallet_address: str
    prompt_text: str
    created_at: str


@router.post("/prompt", response_model=AuthorResponse)
async def update_author_prompt(
    request: UpdatePromptRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """Update author's prompt with signature verification."""
    # Verify signature
    try:
        verify_wallet_signature(
            wallet_address=request.wallet_address,
            message=request.message,
            signature=request.signature,
        )
    except SignatureVerificationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Upsert author
    repo = AuthorRepository(session)
    author = await repo.upsert_author_prompt(
        wallet_address=request.wallet_address,
        prompt_text=request.prompt_text,
    )
    await session.commit()

    return AuthorResponse(
        id=str(author.id),
        wallet_address=author.wallet_address,
        prompt_text=author.prompt_text,
        created_at=author.created_at.isoformat() + "Z",
    )


@router.get("/{wallet_address}", response_model=AuthorResponse)
async def get_author_by_wallet(
    wallet_address: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Get author by wallet address (case-insensitive)."""
    repo = AuthorRepository(session)
    author = await repo.get_by_wallet(wallet_address)

    if not author:
        raise HTTPException(
            status_code=404,
            detail=f"Author not found for wallet: {wallet_address}",
        )

    return AuthorResponse(
        id=str(author.id),
        wallet_address=author.wallet_address,
        prompt_text=author.prompt_text,
        created_at=author.created_at.isoformat() + "Z",
    )
```

#### Step 2.4: Register Routes

Update `backend/src/glisk/app.py` to include the new router:

```python
from glisk.api.routes import authors

app.include_router(authors.router)
```

---

### 3. Frontend Implementation

#### Step 3.1: Add Contract ABI Entry

Update `frontend/src/lib/contract.ts` to add `authorClaimable` mapping:

```typescript
export const GLISK_NFT_ABI = [
  // ... existing ABI entries ...

  // Add this entry for reading claimable balance
  {
    "inputs": [{"name": "", "type": "address"}],
    "name": "authorClaimable",
    "outputs": [{"name": "", "type": "uint256"}],
    "stateMutability": "view",
    "type": "function"
  },

  // Add this entry for claiming rewards
  {
    "inputs": [],
    "name": "claimAuthorRewards",
    "outputs": [],
    "stateMutability": "nonpayable",
    "type": "function"
  },
] as const
```

#### Step 3.2: Create Creator Dashboard Page

Create `frontend/src/pages/CreatorDashboard.tsx`:

```tsx
import { useState, useEffect } from 'react'
import { useAccount, useReadContract, useWriteContract, useWaitForTransactionReceipt, useSignMessage } from 'wagmi'
import { formatEther } from 'viem'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card } from '@/components/ui/card'
import { CONTRACT_ADDRESS, GLISK_NFT_ABI } from '@/lib/contract'

export function CreatorDashboard() {
  const { address, isConnected } = useAccount()
  const [promptText, setPromptText] = useState('')
  const [isLoadingPrompt, setIsLoadingPrompt] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Signature hook
  const { signMessageAsync } = useSignMessage()

  // Read claimable balance from contract
  const { data: claimableWei, refetch: refetchBalance } = useReadContract({
    address: CONTRACT_ADDRESS,
    abi: GLISK_NFT_ABI,
    functionName: 'authorClaimable',
    args: address ? [address] : undefined,
  }) as { data: bigint | undefined; refetch: () => void }

  const claimableEth = claimableWei ? formatEther(claimableWei) : '0.00'

  // Claim rewards transaction
  const { writeContract, data: claimHash, isPending: isClaimPending } = useWriteContract()
  const { isLoading: isClaimConfirming, isSuccess: isClaimSuccess } = useWaitForTransactionReceipt({
    hash: claimHash,
  })

  // Load existing prompt on mount
  useEffect(() => {
    if (!address) return

    setIsLoadingPrompt(true)
    fetch(`/api/authors/${address}`)
      .then(res => {
        if (res.status === 404) {
          setPromptText('')
          return
        }
        if (!res.ok) throw new Error('Failed to load prompt')
        return res.json()
      })
      .then(data => data && setPromptText(data.prompt_text))
      .catch(err => console.error('Error loading prompt:', err))
      .finally(() => setIsLoadingPrompt(false))
  }, [address])

  // Refetch balance after successful claim
  useEffect(() => {
    if (isClaimSuccess) {
      refetchBalance()
    }
  }, [isClaimSuccess, refetchBalance])

  const handleSavePrompt = async () => {
    if (!address || !promptText) return

    setIsSaving(true)
    setError(null)

    try {
      // Sign message
      const timestamp = Date.now()
      const message = `Update GLISK prompt for wallet: ${address}\nTimestamp: ${timestamp}`
      const signature = await signMessageAsync({ message })

      // Send to backend
      const res = await fetch('/api/authors/prompt', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          wallet_address: address,
          prompt_text: promptText,
          signature,
          message,
        }),
      })

      if (!res.ok) {
        const errorData = await res.json()
        throw new Error(errorData.detail || 'Failed to save prompt')
      }

      alert('Prompt saved successfully!')
    } catch (err: any) {
      if (err.name === 'UserRejectedRequestError') {
        setError('Signature cancelled. Your prompt was not saved.')
      } else {
        setError(err.message)
      }
    } finally {
      setIsSaving(false)
    }
  }

  const handleClaimRewards = () => {
    writeContract({
      address: CONTRACT_ADDRESS,
      abi: GLISK_NFT_ABI,
      functionName: 'claimAuthorRewards',
    })
  }

  if (!isConnected) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Card className="p-6">
          <p>Please connect your wallet to access the creator dashboard.</p>
        </Card>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-2xl">
      <h1 className="text-3xl font-bold mb-6">Creator Dashboard</h1>

      {/* Prompt Management Section */}
      <Card className="p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4">Your AI Generation Prompt</h2>
        <p className="text-sm text-gray-600 mb-4">
          This prompt will be used to generate AI images when users mint NFTs from your wallet address.
        </p>

        <textarea
          value={promptText}
          onChange={(e) => setPromptText(e.target.value)}
          placeholder="Enter your AI generation prompt (1-1000 characters)"
          className="w-full border rounded p-2 mb-4 min-h-[100px]"
          maxLength={1000}
          disabled={isLoadingPrompt || isSaving}
        />

        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-500">{promptText.length}/1000 characters</span>
          <Button
            onClick={handleSavePrompt}
            disabled={!promptText || promptText.length < 1 || isSaving}
          >
            {isSaving ? 'Saving...' : 'Save Prompt'}
          </Button>
        </div>

        {error && <p className="text-red-600 text-sm mt-2">{error}</p>}
      </Card>

      {/* Rewards Claiming Section */}
      <Card className="p-6">
        <h2 className="text-xl font-semibold mb-4">Your Creator Rewards</h2>
        <p className="text-sm text-gray-600 mb-4">
          Accumulated rewards from NFTs minted with your wallet as the prompt author.
        </p>

        <div className="bg-gray-100 rounded p-4 mb-4">
          <p className="text-2xl font-bold">{claimableEth} ETH</p>
          <p className="text-sm text-gray-600">Claimable Balance</p>
        </div>

        <Button
          onClick={handleClaimRewards}
          disabled={!claimableWei || claimableWei === 0n || isClaimPending || isClaimConfirming}
          className="w-full"
        >
          {isClaimPending || isClaimConfirming ? 'Claiming...' : 'Claim Rewards'}
        </Button>

        {isClaimSuccess && (
          <p className="text-green-600 text-sm mt-2">Rewards claimed successfully!</p>
        )}
      </Card>
    </div>
  )
}
```

#### Step 3.3: Add Route to App

Update `frontend/src/App.tsx`:

```tsx
import { CreatorDashboard } from './pages/CreatorDashboard'

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <Header />
        <Routes>
          <Route path="/:creatorAddress" element={<CreatorMintPage />} />
          <Route path="/creator-dashboard" element={<CreatorDashboard />} />  {/* NEW */}
          <Route path="/" element={<Navigate to="/0x0000000000000000000000000000000000000000" replace />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}
```

---

## Testing

### Manual Testing Checklist

#### Test 1: Set New Prompt

1. Start backend and frontend:
   ```bash
   # Terminal 1: Backend
   cd backend
   uv run uvicorn glisk.main:app --reload

   # Terminal 2: Frontend
   cd frontend
   npm run dev
   ```

2. Navigate to `http://localhost:5173/creator-dashboard`
3. Connect MetaMask wallet
4. Enter a prompt (e.g., "Minimalist geometric art with pastel colors")
5. Click "Save Prompt"
6. Approve signature in MetaMask
7. Verify success message appears
8. Reload page, confirm prompt persists

**Expected**: Prompt saved successfully, persists after reload

#### Test 2: Update Existing Prompt

1. With wallet connected from Test 1
2. Modify prompt text (e.g., change "pastel" to "vibrant")
3. Click "Save Prompt"
4. Approve signature
5. Verify update success
6. Reload page, confirm new prompt displays

**Expected**: Prompt updated successfully, no duplicate author created

#### Test 3: Query Author via API

```bash
# Replace with your wallet address
curl http://localhost:8000/api/authors/0xYourWalletAddress
```

**Expected Output**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "wallet_address": "0xYourWalletAddress",
  "prompt_text": "Your saved prompt",
  "created_at": "2025-10-20T12:34:56.789Z"
}
```

#### Test 4: Claim Rewards (Optional - Requires On-Chain Balance)

**Setup**: Mint an NFT using your wallet as prompt author to accumulate rewards

1. Navigate to `/creator-dashboard`
2. Verify balance shows non-zero ETH
3. Click "Claim Rewards"
4. Approve transaction in MetaMask
5. Wait for confirmation (~10 seconds on Base Sepolia)
6. Verify balance updates to 0.00 ETH
7. Check MetaMask to confirm ETH received

**Expected**: Rewards claimed successfully, balance resets to zero

---

## Troubleshooting

### Issue: "Author not found" when loading prompt

**Cause**: No author record exists for this wallet yet

**Solution**: This is expected behavior. Enter a prompt and save to create the author record.

---

### Issue: "Signature verification failed"

**Possible Causes**:
1. Wrong wallet connected (signature from different wallet)
2. Message format mismatch (frontend/backend message differs)
3. Signature expired (if timestamp validation enabled)

**Solution**:
- Verify connected wallet matches the address in request
- Check backend logs for detailed error
- Try disconnecting/reconnecting wallet

---

### Issue: "Claim Rewards button disabled"

**Possible Causes**:
1. Balance is zero (no rewards to claim)
2. Contract RPC call failed
3. Not connected to Base Sepolia network

**Solution**:
- Check claimable balance display shows non-zero ETH
- Verify MetaMask is connected to Base Sepolia
- Check browser console for RPC errors

---

### Issue: Backend 500 error on prompt save

**Possible Causes**:
1. Database connection failure
2. Missing `eth-account` dependency
3. CORS configuration issue

**Solution**:
```bash
# Check backend logs
docker logs backend-app-1

# Verify eth-account installed
cd backend
uv pip list | grep eth-account

# Test database connection
docker exec backend-postgres-1 psql -U glisk -d glisk -c "SELECT 1"
```

---

## Next Steps

After completing implementation and testing:

1. **Code Review**: Review signature verification logic for security
2. **Add Tests**: Write pytest tests for signature verification and API endpoints
3. **Update Documentation**: Add creator dashboard to main README
4. **Deploy**: Deploy to staging environment for user testing

---

## Development Tips

### Hot Reload

Both backend and frontend support hot reload:
- **Backend**: uvicorn `--reload` flag automatically restarts on file changes
- **Frontend**: Vite dev server (`npm run dev`) hot reloads on save

### Debugging Signatures

Add logging to signature verification:

```python
import structlog
logger = structlog.get_logger()

def verify_wallet_signature(wallet_address: str, message: str, signature: str) -> bool:
    logger.info("signature_verification.attempt", wallet_address=wallet_address, message=message[:50])
    try:
        # ... verification logic ...
        logger.info("signature_verification.success", wallet_address=wallet_address)
        return True
    except Exception as e:
        logger.error("signature_verification.failed", wallet_address=wallet_address, error=str(e))
        raise
```

### Database Inspection

Query authors directly:

```sql
-- Connect to PostgreSQL
docker exec backend-postgres-1 psql -U glisk -d glisk

-- List all authors
SELECT wallet_address, LEFT(prompt_text, 50) as prompt_preview, created_at
FROM authors
ORDER BY created_at DESC
LIMIT 10;

-- Find author by wallet (case-insensitive)
SELECT * FROM authors WHERE LOWER(wallet_address) = LOWER('0xYourWalletAddress');
```

---

## Summary

✅ **Backend**: Signature verification service + API routes
✅ **Frontend**: Creator dashboard page with prompt management + reward claiming
✅ **No Migrations**: Reuses existing `authors` table
✅ **Testing**: Manual testing checklist provided
✅ **Timeline**: 2-3 days for full implementation

**Ready to start?** Follow the setup steps above and refer to [api-contracts.md](contracts/api-contracts.md) for detailed API specifications.
