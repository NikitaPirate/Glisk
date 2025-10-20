# Data Model: Frontend Foundation with Creator Mint Page

**Feature**: 005-frontend-foundation-with
**Date**: 2025-10-20
**Type**: Client-side state (no persistent storage)

## Overview

This frontend is a stateless SPA with no backend integration or local persistence. All data is ephemeral and managed via React state hooks and wagmi's internal caching. The data model focuses on client-side state for wallet connection, transaction lifecycle, and form inputs.

## State Categories

### 1. Wallet Connection State (Managed by wagmi)

wagmi's `useAccount` hook provides wallet connection state automatically. No manual state management needed.

**Provided by `useAccount()`**:
```typescript
{
  address: `0x${string}` | undefined,  // Connected wallet address
  isConnected: boolean,                // True if wallet connected
  isConnecting: boolean,               // True during connection process
  isDisconnected: boolean,             // True if no wallet connected
  connector: Connector | undefined,    // Active wallet connector (MetaMask, Coinbase, etc.)
  chain: Chain | undefined             // Active chain (should be Base Sepolia)
}
```

**State Transitions**:
```
disconnected → connecting → connected
                   ↓
              disconnected (if user cancels)

connected → disconnected (user disconnects or switches wallet)
```

**Usage**:
- Show "Connect Wallet" button when `isDisconnected`
- Show wallet address when `isConnected`
- Disable mint button when `!isConnected`
- Show network warning if `chain.id !== 84532` (not Base Sepolia)

---

### 2. Mint Transaction State (Managed by wagmi)

Transaction lifecycle managed by `useWriteContract` and `useWaitForTransactionReceipt` hooks.

**Provided by `useWriteContract()`**:
```typescript
{
  writeContract: (args: WriteContractParameters) => void, // Trigger mint transaction
  data: `0x${string}` | undefined,                        // Transaction hash after submission
  error: Error | null,                                    // Error object if write fails
  isPending: boolean,                                     // True while waiting for wallet approval
  isSuccess: boolean,                                     // True after hash returned
  reset: () => void                                       // Reset state for retry
}
```

**Provided by `useWaitForTransactionReceipt({ hash })`**:
```typescript
{
  isLoading: boolean,     // True while transaction pending on blockchain
  isSuccess: boolean,     // True when transaction confirmed
  isError: boolean,       // True if transaction reverted
  error: Error | null,    // Error details if transaction failed
  data: Receipt | null    // Transaction receipt on success
}
```

**State Transitions**:
```
idle
  ↓ (user clicks Mint)
writeContract() called
  ↓ (wallet prompt)
user approves → isPending = true
  ↓
transaction hash returned → data = hash, isSuccess = true (write success)
  ↓
useWaitForTransactionReceipt starts polling → isLoading = true
  ↓
transaction mined → isSuccess = true (receipt success)

OR

user rejects → error set, isPending = false
OR
transaction reverts → error set, isError = true
```

**Derived State** (managed in component):
```typescript
// Transaction status message
type TransactionStatus =
  | 'idle'              // No transaction initiated
  | 'waitingApproval'   // writeContract isPending (wallet prompt shown)
  | 'submitting'        // writeContract isSuccess but not yet polling receipt
  | 'pending'           // Transaction submitted, waiting for confirmation
  | 'success'           // Transaction confirmed on blockchain
  | 'failed'            // Transaction rejected or reverted
  | 'cancelled'         // User cancelled in wallet
```

**Implementation**:
```typescript
const getTransactionStatus = (): TransactionStatus => {
  if (writeIsPending) return 'waitingApproval'
  if (writeError?.message.includes('User rejected')) return 'cancelled'
  if (writeError) return 'failed'
  if (receiptIsSuccess) return 'success'
  if (receiptIsError) return 'failed'
  if (receiptIsLoading) return 'pending'
  if (writeIsSuccess) return 'submitting'
  return 'idle'
}
```

**Usage**:
- Disable mint button when status !== 'idle'
- Show status message based on current status
- Allow retry (reset state) when status === 'failed' or 'cancelled'

---

### 3. Form Input State (Component useState)

User-controlled inputs for minting configuration.

**Entity: MintFormState**

```typescript
interface MintFormState {
  quantity: number  // Number of NFTs to mint (1-10)
}
```

**Fields**:

| Field    | Type   | Validation            | Default | Notes                           |
|----------|--------|-----------------------|---------|---------------------------------|
| quantity | number | min: 1, max: 10       | 1       | Controlled input with clamping  |

**State Management**:
```typescript
const [quantity, setQuantity] = useState<number>(1)

const handleQuantityChange = (value: string) => {
  const num = parseInt(value, 10)
  if (isNaN(num)) return
  const clamped = Math.max(1, Math.min(10, num))
  setQuantity(clamped)
}
```

**Validation Rules**:
- Minimum: 1 NFT (cannot mint zero or negative)
- Maximum: 10 NFTs (spec requirement FR-013)
- Integer only (no decimals)
- If user enters invalid value (empty, negative, >10), clamp to valid range
- No async validation needed (all client-side)

**Usage**:
- Bind input value to `quantity` state
- Pass `quantity` to `writeContract` as `args: [creatorAddress, quantity]`
- Calculate total cost: `mintPrice * BigInt(quantity)` (if price known)

---

### 4. Route Parameters (React Router)

Dynamic route parameter extracted from URL.

**Entity: RouteParams**

```typescript
interface RouteParams {
  creatorAddress: string  // Ethereum address from URL path
}
```

**Source**: `useParams()` hook from react-router-dom

```typescript
const { creatorAddress } = useParams<{ creatorAddress: string }>()
```

**Validation** (MVP: minimal):
- Check if `creatorAddress` is defined (not undefined)
- Optional: Basic format check (starts with `0x`, 42 characters)
- No on-chain validation (don't query if address has NFTs or if contract exists)
- Invalid address will fail at transaction time (contract call will revert)

**Usage**:
- Display creator address in page header or mint section
- Pass `creatorAddress` to `writeContract` as first argument (author parameter)
- If `creatorAddress` is undefined, show fallback UI or redirect to home

---

### 5. UI Feedback State (Component useState)

Additional component-level state for user feedback.

**Entity: StatusMessage**

```typescript
interface StatusMessage {
  text: string          // Message to display
  type: 'info' | 'success' | 'error' | 'warning'  // Visual style
}
```

**Derived from Transaction State**:
```typescript
const getStatusMessage = (status: TransactionStatus): StatusMessage | null => {
  switch (status) {
    case 'idle':
      return null
    case 'waitingApproval':
      return { text: 'Please approve the transaction in your wallet', type: 'info' }
    case 'submitting':
      return { text: 'Submitting transaction...', type: 'info' }
    case 'pending':
      return { text: 'Minting... waiting for confirmation', type: 'info' }
    case 'success':
      return { text: 'Success! NFTs minted.', type: 'success' }
    case 'failed':
      return { text: `Error: ${error?.message || 'Transaction failed'}`, type: 'error' }
    case 'cancelled':
      return { text: 'Transaction cancelled', type: 'warning' }
    default:
      return null
  }
}
```

**Usage**:
- Render status message below mint button
- Apply Tailwind classes based on type:
  - `info`: `text-blue-600`
  - `success`: `text-green-600`
  - `error`: `text-red-600`
  - `warning`: `text-yellow-600`

---

## State Flow Diagram

```
User visits /{creatorAddress}
  ↓
Component mounts
  ↓
useParams → extract creatorAddress
useAccount → check wallet connection
  ↓
User clicks "Connect Wallet" (if not connected)
  ↓
RainbowKit modal → user selects wallet → useAccount updates
  ↓
Wallet connected → mint button enabled
  ↓
User selects quantity (1-10) → useState updates
  ↓
User clicks "Mint"
  ↓
writeContract({ args: [creatorAddress, quantity], value: price * quantity })
  ↓
Wallet prompts approval → user approves/rejects
  ↓
If approved:
  Transaction hash returned → useWaitForTransactionReceipt polls
  ↓
  Transaction confirms → show success message

If rejected:
  Error set → show cancellation message

If reverted:
  Error set → show error message with reason
```

---

## No Persistent Storage

**Important**: This frontend does not persist any data. All state is lost on page refresh except:
- Wallet connection (wagmi stores connection preference in localStorage automatically)
- No transaction history
- No user preferences
- No cached NFT data

**Implications**:
- User must reconnect wallet if they clear localStorage
- Transaction history not shown (user can view on BaseScan via transaction hash)
- If user navigates away during pending transaction, they won't see confirmation (but transaction will complete on-chain)

**Future Enhancements** (out of scope):
- LocalStorage for recent transactions
- Backend integration for mint history
- IndexedDB for offline caching

---

## Type Definitions

**Comprehensive TypeScript types for implementation**:

```typescript
// lib/types.ts

import { Address } from 'viem'

// Route parameters
export interface CreatorMintPageParams {
  creatorAddress: Address
}

// Form state
export interface MintFormState {
  quantity: number
}

// Transaction status (derived state)
export type TransactionStatus =
  | 'idle'
  | 'waitingApproval'
  | 'submitting'
  | 'pending'
  | 'success'
  | 'failed'
  | 'cancelled'

// Status message
export interface StatusMessage {
  text: string
  type: 'info' | 'success' | 'error' | 'warning'
}

// Contract write args
export interface MintArgs {
  author: Address
  quantity: number
}

// Environment variables
export interface ImportMetaEnv {
  readonly VITE_CONTRACT_ADDRESS: Address
  readonly VITE_CHAIN_ID: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
```

---

## Edge Cases & Error States

### Wallet Connection Errors
- **User rejects connection**: `useAccount` returns `isDisconnected`, show "Connect Wallet" button
- **Wallet locked**: Same as rejected, user must unlock wallet first
- **Wrong network**: `chain.id !== 84532`, show "Please switch to Base Sepolia" message
- **No wallet extension**: RainbowKit shows install prompt automatically

### Transaction Errors
- **Insufficient balance**: Contract reverts, error message shows "insufficient funds"
- **Gas estimation failure**: Contract call fails before user approval, show error
- **User rejects transaction**: `writeContract` error with "User rejected request"
- **Transaction timeout**: `useWaitForTransactionReceipt` may take long time, keep showing "pending" (no custom timeout for MVP)
- **Contract revert**: `useWaitForTransactionReceipt` error shows revert reason

### Form Validation Errors
- **Quantity < 1**: Input clamped to 1
- **Quantity > 10**: Input clamped to 10
- **Non-numeric input**: Ignored, previous valid value retained

### Route Errors
- **Invalid creator address format**: Page loads but transaction will fail (acceptable for MVP)
- **Missing creator address**: Show fallback UI or redirect to home
- **Creator address with no NFTs**: Page loads, mint works (creator doesn't need existing NFTs to be in URL)

---

## Validation Summary

| Field          | Validation                          | Error Handling                          |
|----------------|-------------------------------------|-----------------------------------------|
| creatorAddress | Basic format check (optional)       | Contract revert if invalid              |
| quantity       | 1 ≤ quantity ≤ 10                   | Clamp to valid range                    |
| wallet         | Must be connected                   | Disable mint button                     |
| network        | Must be Base Sepolia (84532)        | Show network switch prompt              |
| balance        | Must have enough ETH (checked on-chain) | Contract revert, show error message |

All validation is either client-side (quantity, wallet check) or handled by smart contract (balance, address validity).
