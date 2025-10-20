# Research: Frontend Foundation with Creator Mint Page

**Feature**: 005-frontend-foundation-with
**Date**: 2025-10-20
**Status**: All decisions locked (provided by user)

## Overview

This document records the technical decisions for the frontend foundation feature. All decisions were provided upfront - no research phase was needed. This feature establishes the React + Web3 infrastructure for NFT minting.

## Technical Decisions

### 1. Frontend Framework: Vite + React 18 + TypeScript

**Decision**: Use Vite as build tool with React 18 and TypeScript

**Rationale**:
- Vite provides fast dev server with HMR (hot module replacement)
- React 18 is industry standard for SPAs
- TypeScript prevents common runtime errors with static typing
- Vite's plugin ecosystem supports all needed tooling (Tailwind, path aliases)

**Alternatives Considered**: None (decision locked)

**Implementation Notes**:
- Initialize with `npm create vite@latest frontend -- --template react-ts`
- Configure path aliases in tsconfig.json for cleaner imports
- Use `npm run dev` for development, `npm run build` for production

**References**:
- Vite: https://vitejs.dev/
- React 18: https://react.dev/

---

### 2. Styling: Tailwind CSS + shadcn/ui

**Decision**: Use Tailwind CSS utility classes with shadcn/ui component primitives (Button, Input, Card only)

**Rationale**:
- Tailwind enables rapid development with utility classes
- No custom CSS needed for MVP (basic layouts, spacing, typography)
- shadcn/ui provides unstyled, accessible primitives (copy-paste components)
- Minimal dependencies (no full component library like MUI or Chakra)
- Aligns with "bare minimum" constraint (no gradients, animations, complex styling)

**Alternatives Considered**: None (decision locked)

**Implementation Notes**:
- Install Tailwind via `npm install -D tailwindcss postcss autoprefixer`
- Initialize shadcn/ui: `npx shadcn-ui@latest init`
- Add only needed components: `npx shadcn-ui@latest add button input card`
- Use basic utilities: `flex`, `p-4`, `text-lg`, `border`, etc.
- No custom Tailwind config beyond shadcn/ui defaults

**References**:
- Tailwind CSS: https://tailwindcss.com/
- shadcn/ui: https://ui.shadcn.com/

---

### 3. Web3 Stack: RainbowKit + OnchainKit + wagmi + viem

**Decision**: Use RainbowKit for wallet UI, wagmi for React hooks, viem for Ethereum interactions

**Rationale**:
- RainbowKit provides pre-built wallet connection modal (supports MetaMask, Coinbase Wallet, WalletConnect, etc.)
- OnchainKit adds Coinbase-specific integrations (optional but requested)
- wagmi offers React hooks that abstract wallet/contract interactions
- viem is modern, type-safe alternative to ethers.js (wagmi's default transport)
- Stack is production-ready and well-documented

**Alternatives Considered**: None (decision locked)

**Implementation Notes**:
- Install: `npm install @rainbow-me/rainbowkit @coinbase/onchainkit wagmi viem@2.x`
- Wrap app in `WagmiProvider` → `QueryClientProvider` → `RainbowKitProvider`
- Configure wagmi with Base Sepolia chain and HTTP transport
- Use hooks: `useAccount`, `useWriteContract`, `useWaitForTransactionReceipt`

**Key Hooks**:
```typescript
// Wallet connection
const { address, isConnected } = useAccount()

// Trigger contract write
const { writeContract, data: hash } = useWriteContract()

// Wait for transaction confirmation
const { isLoading, isSuccess, error } = useWaitForTransactionReceipt({ hash })
```

**References**:
- RainbowKit: https://www.rainbowkit.com/
- wagmi: https://wagmi.sh/
- viem: https://viem.sh/

---

### 4. Routing: React Router v6

**Decision**: Use React Router for client-side routing with `/{creatorAddress}` dynamic route

**Rationale**:
- Industry standard for React SPAs
- Simple API for dynamic routes (`<Route path="/:creatorAddress" />`)
- Built-in hooks (`useParams`) for URL parameter extraction
- Works seamlessly with Vite (no special config needed)

**Alternatives Considered**: None (decision locked)

**Implementation Notes**:
- Install: `npm install react-router-dom`
- Define routes in App.tsx with BrowserRouter
- Use `useParams()` to extract `creatorAddress` from URL
- Root route `/` can redirect to example creator address or show landing page

**Example**:
```typescript
import { BrowserRouter, Routes, Route } from 'react-router-dom'

<BrowserRouter>
  <Routes>
    <Route path="/:creatorAddress" element={<CreatorMintPage />} />
  </Routes>
</BrowserRouter>
```

**References**:
- React Router: https://reactrouter.com/

---

### 5. Smart Contract Integration

**Decision**: Use deployed GliskNFT contract on Base Sepolia with ABI from backend repo

**Contract Details**:
- **Address**: `0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0`
- **Network**: Base Sepolia (chainId: 84532)
- **ABI Location**: `backend/src/glisk/contracts/GliskNFT.json`
- **Mint Function**: `mint(address promptAuthor, uint256 quantity) payable`
- **Mint Price**: Public `mintPrice` state variable (uint256)

**Rationale**:
- Contract already deployed and tested (no contract changes needed)
- ABI available in monorepo (can sync via `./sync-abi.sh` if needed)
- Base Sepolia is low-cost testnet for development
- `mint()` signature matches requirements (promptAuthor address from URL, quantity from user input)

**Alternatives Considered**: None (contract already deployed)

**Implementation Notes**:
- Copy ABI JSON from `backend/src/glisk/contracts/GliskNFT.json` to `frontend/src/lib/glisk-nft-abi.json`
- Store contract address in `.env` file: `VITE_CONTRACT_ADDRESS=0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0`
- Use wagmi's `useWriteContract` hook with contract address, ABI, and function name
- Use wagmi's `useReadContract` hook to query `mintPrice` state variable

**Contract Call Example**:
```typescript
// Query mint price
const { data: mintPrice } = useReadContract({
  address: contractAddress,
  abi: gliskNFTAbi,
  functionName: 'mintPrice'
})

// Trigger mint transaction
writeContract({
  address: contractAddress,
  abi: gliskNFTAbi,
  functionName: 'mint',
  args: [creatorAddress, quantity],
  value: mintPrice ? mintPrice * BigInt(quantity) : 0n
})
```

**References**:
- Base Sepolia RPC: https://sepolia.base.org
- Contract on BaseScan: https://sepolia.basescan.org/address/0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0

---

### 6. State Management: useState + useContext only

**Decision**: Use React's built-in useState and useContext hooks (no Redux, Zustand, or other libraries)

**Rationale**:
- App is simple with minimal state (wallet connection, form inputs, transaction status)
- wagmi handles wallet/contract state internally (no need to duplicate in global store)
- useState sufficient for component-level state (quantity selector, transaction status messages)
- useContext can share theme or app-level config if needed (likely not needed for MVP)
- Aligns with "minimal implementation" constraint

**Alternatives Considered**: None (decision locked)

**Implementation Notes**:
- Use `useState` in CreatorMintPage for quantity selector value
- Use `useState` for transaction status messages ("Minting...", "Success!", error text)
- Wallet state comes from wagmi's `useAccount` (no manual state management)
- Transaction state comes from `useWaitForTransactionReceipt` (automatic polling)

**Example**:
```typescript
const [quantity, setQuantity] = useState(1)
const [statusMessage, setStatusMessage] = useState('')
```

---

### 7. User Feedback: Simple Text Messages (No Toast Library)

**Decision**: Display transaction status with plain text messages (no react-hot-toast, react-toastify, etc.)

**Rationale**:
- MVP only needs basic feedback ("Minting...", "Success!", error messages)
- Text messages easier to implement than toast libraries
- Reduces bundle size and dependencies
- Aligns with "bare minimum" constraint
- Can upgrade to toasts in future if UX testing shows need

**Alternatives Considered**: None (decision locked)

**Implementation Notes**:
- Use conditional rendering based on transaction state
- Show "Minting..." text when `isLoading` is true
- Show "Success! Transaction confirmed." when `isSuccess` is true
- Show error message from `error` object when transaction fails
- Use simple `<p>` or `<div>` tags with basic Tailwind styling (e.g., `text-green-600` for success, `text-red-600` for errors)

**Example**:
```typescript
{isLoading && <p className="text-blue-600">Minting...</p>}
{isSuccess && <p className="text-green-600">Success! Transaction confirmed.</p>}
{error && <p className="text-red-600">Error: {error.message}</p>}
```

---

### 8. Deployment: Nginx Reverse Proxy

**Decision**: Use Nginx to serve static build files and handle client-side routing

**Rationale**:
- Standard production setup for React SPAs
- Nginx efficiently serves static files (HTML, CSS, JS bundles)
- `try_files` directive handles SPA routing (fallback to index.html for all routes)
- Can proxy API requests in future if backend integration added
- Production-ready with compression, caching headers

**Alternatives Considered**: None (decision locked)

**Implementation Notes**:
- Create `nginx/frontend.conf` with basic static file serving config
- Use `try_files $uri $uri/ /index.html;` to handle client-side routes
- Build frontend with `npm run build` (outputs to `frontend/dist/`)
- Point Nginx root to `frontend/dist/` directory

**Nginx Config Example**:
```nginx
server {
    listen 80;
    server_name localhost;

    root /path/to/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

**References**:
- Nginx documentation: https://nginx.org/en/docs/

---

### 9. Environment Configuration

**Decision**: Use Vite's built-in environment variable system with `.env` files

**Environment Variables**:
- `VITE_CONTRACT_ADDRESS` - GliskNFT contract address (0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0)
- `VITE_CHAIN_ID` - Chain ID for Base Sepolia (84532)

**Rationale**:
- Vite automatically loads `.env` files and exposes `VITE_*` prefixed vars to client code
- Type-safe access via `import.meta.env.VITE_CONTRACT_ADDRESS`
- `.env.example` template for team members (tracked in git)
- `.env` local overrides (gitignored for secrets)

**Alternatives Considered**: None (Vite default)

**Implementation Notes**:
- Create `.env.example` with placeholder values
- Create `.env` locally with actual values
- Access in code: `import.meta.env.VITE_CONTRACT_ADDRESS`
- Add validation check on app startup to ensure vars are defined

**References**:
- Vite env variables: https://vitejs.dev/guide/env-and-mode.html

---

## Best Practices Summary

### RainbowKit + wagmi Setup
- Wrap app in providers in correct order: WagmiProvider → QueryClientProvider → RainbowKitProvider
- Configure wagmi with `baseSepolia` chain from wagmi/chains
- Use `http()` transport with Base Sepolia RPC URL
- Enable wallet connectors in RainbowKit config (injected, WalletConnect, Coinbase)

### Contract Interactions
- Always validate contract address and ABI are loaded before rendering mint button
- Use BigInt for quantity and wei values (avoid floating point errors)
- Check wallet is connected before calling `writeContract`
- Disable mint button during pending transactions (`isLoading` state)
- Handle transaction errors gracefully (user rejection, insufficient funds, contract reverts)

### Transaction Flow
1. User clicks "Mint" → `writeContract()` called
2. Wallet prompts approval → user approves/rejects
3. If approved → transaction hash returned → store in state
4. `useWaitForTransactionReceipt` polls for confirmation
5. On success → show success message
6. On error → show error message, allow retry

### Error Handling
- Wallet not connected → disable mint button
- Wrong network (not Base Sepolia) → show network switch prompt
- Insufficient balance → show error from contract revert
- User rejection → show "Transaction cancelled by user"
- Network errors → show "Network error, please try again"

### Code Organization
- Keep wagmi config in separate file (`lib/wagmi.ts`)
- Keep contract constants in separate file (`lib/contract.ts`)
- One component per file (Header.tsx, CreatorMintPage.tsx)
- No custom hooks unless absolutely necessary (direct wagmi hooks preferred)

---

## Testing Strategy

**Manual Testing Only** (automated tests out of scope for MVP)

### Test Scenarios

1. **Wallet Connection**
   - Click "Connect Wallet" → modal appears
   - Select wallet → wallet prompts approval
   - Approve → address shown in header
   - Refresh page → wallet stays connected

2. **Creator Page Navigation**
   - Visit `/{validAddress}` → page loads
   - Visit `/{invalidAddress}` → page loads (no validation for MVP)
   - Change address in URL → page updates

3. **Mint Flow - Happy Path**
   - Connect wallet → select quantity (1-10) → click Mint
   - Approve transaction in wallet → see "Minting..." message
   - Wait for confirmation → see "Success!" message

4. **Mint Flow - Error Cases**
   - Mint without connecting wallet → button disabled
   - Reject transaction in wallet → see "cancelled" message
   - Insufficient ETH balance → see contract revert error
   - Switch to wrong network → see network switch prompt

5. **Edge Cases**
   - Disconnect wallet during pending transaction → UI handles gracefully
   - Navigate away during pending transaction → transaction continues on blockchain
   - Very large quantity (>10) → input clamped to max 10
   - Zero or negative quantity → input clamped to min 1

### Browser Testing
- Chrome + MetaMask
- Firefox + MetaMask
- Safari + Coinbase Wallet (if available)

---

## Open Questions / Future Enhancements

**For MVP**: All decisions locked, no open questions

**Future Considerations** (out of scope for current feature):
- Mint price: Currently hardcoded or needs manual contract query. Future: Add price display before minting.
- NFT preview: Show generated image after successful mint (requires backend integration).
- Transaction history: Show past mints for connected wallet (requires indexing or backend).
- Multi-chain support: Add Ethereum mainnet, Base mainnet (requires chain switcher UI).
- Mobile wallet support: Test WalletConnect on mobile browsers.
- Error analytics: Track failed transactions to identify common issues.
