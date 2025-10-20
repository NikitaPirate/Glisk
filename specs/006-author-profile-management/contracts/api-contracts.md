# API Contracts: Author Profile Management

**Feature**: Author Profile Management (006)
**Date**: 2025-10-20
**Version**: 1.0.0

## Overview

This document defines the HTTP API contracts for author profile management. All endpoints follow REST conventions and return JSON responses.

**Base URL**: `/api/authors`

**Authentication**: Wallet signature verification (EIP-191) required for state-changing operations

---

## Endpoints

### 1. Update Author Prompt

**Purpose**: Create or update an author's AI generation prompt with wallet signature verification

**Method**: `POST`
**Path**: `/api/authors/prompt`
**Authentication**: Required (EIP-191 signature)

#### Request

**Headers**:
```http
Content-Type: application/json
```

**Body**:
```json
{
  "wallet_address": "string",
  "prompt_text": "string",
  "signature": "string",
  "message": "string"
}
```

**Field Specifications**:

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `wallet_address` | string | Yes | - Format: `0x` + 40 hex chars<br>- Case-insensitive<br>- Length: 42 | Ethereum wallet address of the author |
| `prompt_text` | string | Yes | - Min length: 1<br>- Max length: 1000<br>- UTF-8 encoding | AI generation prompt text |
| `signature` | string | Yes | - Format: `0x` + hex string<br>- Valid EIP-191 signature | Wallet signature of the message |
| `message` | string | Yes | - Must match server-expected format | Signed message for verification |

**Message Format** (must be signed by wallet):
```
Update GLISK prompt for wallet: {wallet_address}
Timestamp: {unix_timestamp_ms}
```

**Example Request**:
```json
{
  "wallet_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
  "prompt_text": "Surreal neon landscapes with futuristic architecture and glowing flora",
  "signature": "0x1a2b3c4d5e6f7890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890ab",
  "message": "Update GLISK prompt for wallet: 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0\nTimestamp: 1729425000000"
}
```

#### Response

**Success** (200 OK):
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
| `has_prompt` | boolean | Always `true` (confirms author now has a configured prompt) |

**Note**: Prompt text is never echoed back in the response. It is stored in the database for backend image generation use only.

**Errors**:

| Status | Code | Message | When |
|--------|------|---------|------|
| 400 | `invalid_wallet_format` | "Wallet address must be in format 0x followed by 40 hex characters" | Invalid wallet address format |
| 400 | `invalid_prompt_length` | "Prompt text must be between 1 and 1000 characters" | Prompt too short/long |
| 400 | `signature_verification_failed` | "Signature verification failed. Please ensure you're using the correct wallet." | Signature doesn't match wallet |
| 400 | `invalid_signature_format` | "Invalid signature format. Expected hex string starting with 0x" | Malformed signature |
| 401 | `missing_signature` | "Signature required for authentication" | Missing signature field |
| 500 | `internal_error` | "Failed to save prompt. Please try again." | Database error or unexpected exception |

**Error Response Format**:
```json
{
  "detail": "string",
  "code": "string"
}
```

**Example Error**:
```json
{
  "detail": "Prompt text must be between 1 and 1000 characters",
  "code": "invalid_prompt_length"
}
```

---

### 2. Check Author Prompt Status

**Purpose**: Check if an author has configured a prompt (prompt text is never exposed via API)

**Method**: `GET`
**Path**: `/api/authors/{wallet_address}`
**Authentication**: Not required (public read)

#### Request

**Path Parameters**:

| Parameter | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `wallet_address` | string | - Format: `0x` + 40 hex chars<br>- Case-insensitive | Ethereum wallet address |

**Example Request**:
```http
GET /api/authors/0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0
```

#### Response

**Success** (200 OK):
```json
{
  "has_prompt": true
}
```

**Response Schema**:

| Field | Type | Description |
|-------|------|-------------|
| `has_prompt` | boolean | `true` if author has configured a prompt, `false` otherwise |

**Note**: This endpoint always returns 200 OK. If the wallet address has no associated author record, it returns `{"has_prompt": false}`.

**Errors**:

| Status | Code | Message | When |
|--------|------|---------|------|
| 400 | `invalid_wallet_format` | "Invalid wallet address format" | Malformed wallet address in path |

**Example Error** (400):
```json
{
  "detail": "Invalid wallet address format",
  "code": "invalid_wallet_format"
}
```

---

## Frontend Integration Patterns

### React Hook for Checking Prompt Status

```typescript
import { useEffect, useState } from 'react'

function useAuthorStatus(walletAddress: string | undefined) {
  const [hasPrompt, setHasPrompt] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!walletAddress) return

    setIsLoading(true)
    fetch(`/api/authors/${walletAddress}`)
      .then(res => {
        if (!res.ok) throw new Error('Failed to fetch author status')
        return res.json()
      })
      .then(data => setHasPrompt(data.has_prompt))
      .catch(err => setError(err.message))
      .finally(() => setIsLoading(false))
  }, [walletAddress])

  return { hasPrompt, isLoading, error }
}
```

### React Hook for Updating Prompt

```typescript
import { useState } from 'react'
import { useSignMessage } from 'wagmi'

function useUpdatePrompt(walletAddress: string | undefined) {
  const { signMessageAsync } = useSignMessage()
  const [isUpdating, setIsUpdating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const updatePrompt = async (promptText: string) => {
    if (!walletAddress) throw new Error('Wallet not connected')

    setIsUpdating(true)
    setError(null)

    try {
      // Sign message
      const timestamp = Date.now()
      const message = `Update GLISK prompt for wallet: ${walletAddress}\nTimestamp: ${timestamp}`
      const signature = await signMessageAsync({ message })

      // Send to backend
      const res = await fetch('/api/authors/prompt', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          wallet_address: walletAddress,
          prompt_text: promptText,
          signature,
          message,
        }),
      })

      if (!res.ok) {
        const errorData = await res.json()
        throw new Error(errorData.detail || 'Failed to update prompt')
      }

      const data = await res.json()
      return data.success
    } catch (err: any) {
      if (err.name === 'UserRejectedRequestError') {
        setError('Signature cancelled. Your prompt was not saved.')
      } else {
        setError(err.message)
      }
      throw err
    } finally {
      setIsUpdating(false)
    }
  }

  return { updatePrompt, isUpdating, error }
}
```

---

## Smart Contract Integration

### Reading Claimable Balance

**Contract Function**:
```solidity
mapping(address => uint256) public authorClaimable;
```

**Frontend Pattern** (wagmi):
```typescript
import { useReadContract } from 'wagmi'
import { formatEther } from 'viem'
import { CONTRACT_ADDRESS, GLISK_NFT_ABI } from '@/lib/contract'

function useClaimableBalance(authorAddress: string | undefined) {
  const { data: claimableWei, isLoading, error } = useReadContract({
    address: CONTRACT_ADDRESS,
    abi: GLISK_NFT_ABI,
    functionName: 'authorClaimable',
    args: authorAddress ? [authorAddress] : undefined,
  }) as { data: bigint | undefined; isLoading: boolean; error: Error | null }

  const claimableEth = claimableWei ? formatEther(claimableWei) : '0.00'

  return { claimableWei, claimableEth, isLoading, error }
}
```

**Required ABI Entry**:
```json
{
  "inputs": [
    {
      "internalType": "address",
      "name": "",
      "type": "address"
    }
  ],
  "name": "authorClaimable",
  "outputs": [
    {
      "internalType": "uint256",
      "name": "",
      "type": "uint256"
    }
  ],
  "stateMutability": "view",
  "type": "function"
}
```

### Claiming Rewards

**Contract Function**:
```solidity
function claimAuthorRewards() external nonReentrant;
```

**Frontend Pattern** (wagmi):
```typescript
import { useWriteContract, useWaitForTransactionReceipt } from 'wagmi'
import { CONTRACT_ADDRESS, GLISK_NFT_ABI } from '@/lib/contract'

function useClaimRewards() {
  const { writeContract, data: hash, isPending, error: writeError } = useWriteContract()
  const { isLoading: isConfirming, isSuccess, error: receiptError } = useWaitForTransactionReceipt({ hash })

  const claimRewards = () => {
    writeContract({
      address: CONTRACT_ADDRESS,
      abi: GLISK_NFT_ABI,
      functionName: 'claimAuthorRewards',
    })
  }

  const error = writeError || receiptError
  const isProcessing = isPending || isConfirming

  return { claimRewards, isProcessing, isSuccess, error, hash }
}
```

**Required ABI Entry**:
```json
{
  "inputs": [],
  "name": "claimAuthorRewards",
  "outputs": [],
  "stateMutability": "nonpayable",
  "type": "function"
}
```

---

## Security Considerations

### EIP-191 Message Signing

**Standard**: Ethereum Signed Message standard
**Prefix**: `\x19Ethereum Signed Message:\n{message_length}`

**Backend Verification** (Python):
```python
from eth_account.messages import encode_defunct
from eth_account import Account

def verify_signature(wallet_address: str, message: str, signature: str) -> bool:
    """Verify EIP-191 signature matches wallet address.

    Args:
        wallet_address: Expected signer address (0x...)
        message: Plain text message that was signed
        signature: Hex-encoded signature (0x...)

    Returns:
        True if signature is valid and matches wallet_address

    Raises:
        ValueError: If signature format is invalid
    """
    try:
        # Encode message with EIP-191 prefix
        message_hash = encode_defunct(text=message)

        # Recover signer address from signature
        recovered_address = Account.recover_message(message_hash, signature=signature)

        # Compare addresses (case-insensitive)
        return recovered_address.lower() == wallet_address.lower()
    except Exception as e:
        raise ValueError(f"Invalid signature format: {e}")
```

### Signature Replay Prevention

**Timestamp Validation** (optional but recommended):
```python
import time

MAX_MESSAGE_AGE_SECONDS = 300  # 5 minutes

def validate_message_timestamp(message: str) -> bool:
    """Validate message timestamp is recent.

    Args:
        message: Message containing "Timestamp: {unix_ms}" line

    Returns:
        True if timestamp is within MAX_MESSAGE_AGE_SECONDS

    Raises:
        ValueError: If timestamp is missing or too old
    """
    # Extract timestamp from message
    for line in message.split('\n'):
        if line.startswith('Timestamp:'):
            timestamp_ms = int(line.split(':')[1].strip())
            age_seconds = (time.time() * 1000 - timestamp_ms) / 1000

            if age_seconds > MAX_MESSAGE_AGE_SECONDS:
                raise ValueError(f"Message expired (age: {age_seconds:.0f}s)")

            return True

    raise ValueError("Message missing timestamp")
```

### CORS Configuration

**Required CORS Headers**:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
```

---

## Testing

### Integration Test Example

```python
import pytest
from httpx import AsyncClient
from eth_account import Account
from eth_account.messages import encode_defunct

@pytest.mark.asyncio
async def test_update_prompt_with_valid_signature(client: AsyncClient):
    # Setup: Create wallet and sign message
    wallet = Account.create()
    wallet_address = wallet.address
    prompt_text = "Test prompt for integration test"
    message = f"Update GLISK prompt for wallet: {wallet_address}\nTimestamp: {int(time.time() * 1000)}"

    # Sign message
    message_hash = encode_defunct(text=message)
    signature = wallet.sign_message(message_hash).signature.hex()

    # Act: Send request
    response = await client.post(
        "/api/authors/prompt",
        json={
            "wallet_address": wallet_address,
            "prompt_text": prompt_text,
            "signature": f"0x{signature}",
            "message": message,
        },
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["has_prompt"] is True

@pytest.mark.asyncio
async def test_update_prompt_with_invalid_signature(client: AsyncClient):
    # Setup: Create two different wallets
    wallet_a = Account.create()
    wallet_b = Account.create()
    prompt_text = "Test prompt"
    message = f"Update GLISK prompt for wallet: {wallet_a.address}\nTimestamp: {int(time.time() * 1000)}"

    # Sign with wallet B (wrong wallet)
    message_hash = encode_defunct(text=message)
    signature = wallet_b.sign_message(message_hash).signature.hex()

    # Act: Send request
    response = await client.post(
        "/api/authors/prompt",
        json={
            "wallet_address": wallet_a.address,
            "prompt_text": prompt_text,
            "signature": f"0x{signature}",
            "message": message,
        },
    )

    # Assert
    assert response.status_code == 400
    data = response.json()
    assert "signature verification failed" in data["detail"].lower()
```

---

## Rate Limiting

**Recommendation**: Implement rate limiting on POST endpoint to prevent abuse

**Suggested Limits**:
- **Per IP**: 10 requests/minute
- **Per Wallet**: 5 requests/minute (based on wallet_address in request body)

**Implementation** (using slowapi):
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/authors/prompt")
@limiter.limit("10/minute")
async def update_author_prompt(request: Request, ...):
    ...
```

---

## Versioning

**Current Version**: 1.0.0

**Breaking Changes Require Major Version Bump**:
- Removing or renaming fields in request/response
- Changing signature verification algorithm
- Changing message format (would invalidate existing signatures)

**Non-Breaking Changes** (Minor/Patch):
- Adding optional fields to request/response
- Adding new endpoints
- Improving error messages
- Adding validation rules (if they don't break existing valid inputs)

---

## Summary

- ✅ **Two endpoints**: Update prompt (POST), Get author (GET)
- ✅ **RESTful design**: Standard HTTP methods and status codes
- ✅ **Secure**: EIP-191 signature verification prevents unauthorized updates
- ✅ **Clear errors**: Actionable error messages with error codes
- ✅ **Frontend-ready**: Includes React hook examples for integration
- ✅ **Testable**: Comprehensive test examples provided
- ✅ **Production-ready**: Rate limiting and CORS considerations included
