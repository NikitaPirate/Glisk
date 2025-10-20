# Quickstart: Frontend Foundation with Creator Mint Page

**Feature**: 005-frontend-foundation-with
**Date**: 2025-10-20
**Estimated Setup Time**: 15-20 minutes

## Overview

This guide walks you through setting up the frontend development environment, running the app locally, and testing the wallet connection + minting flow.

## Prerequisites

Before starting, ensure you have:

- **Node.js 18+** and **npm** installed (check with `node -v` and `npm -v`)
- **Web3 wallet browser extension** (MetaMask, Coinbase Wallet, or similar)
- **Base Sepolia testnet ETH** for gas fees (get from [Base Sepolia faucet](https://www.coinbase.com/faucets/base-ethereum-sepolia-faucet))
- **Git** for cloning the repo (if not already cloned)
- **Code editor** (VS Code, WebStorm, etc.)

## Quick Setup (5 minutes)

### 1. Initialize Project

From the **repo root** (`/Users/nikita/PycharmProjects/glisk`):

```bash
# Create frontend directory
npm create vite@latest frontend -- --template react-ts

# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Install Web3 libraries
npm install @rainbow-me/rainbowkit @coinbase/onchainkit wagmi viem@2.x

# Install routing
npm install react-router-dom

# Install Tailwind CSS
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p

# Install shadcn/ui
npx shadcn-ui@latest init
# When prompted:
# - TypeScript: Yes
# - Style: Default
# - Base color: Slate
# - CSS variables: Yes

# Add shadcn/ui components
npx shadcn-ui@latest add button input card
```

### 2. Configure Environment Variables

Create `.env` file in `frontend/` directory:

```bash
# frontend/.env
VITE_CONTRACT_ADDRESS=0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0
VITE_CHAIN_ID=84532
```

Create `.env.example` template (committed to git):

```bash
# frontend/.env.example
VITE_CONTRACT_ADDRESS=0x...
VITE_CHAIN_ID=84532
```

### 3. Copy Contract ABI

The GliskNFT contract ABI is already in the backend repo. Copy it to frontend:

```bash
# From repo root
mkdir -p frontend/src/lib
cp backend/src/glisk/contracts/GliskNFT.json frontend/src/lib/glisk-nft-abi.json
```

**Alternative** (if ABI needs to be synced from contracts):

```bash
# From repo root (if sync-abi.sh exists and updates backend/src/glisk/contracts/)
./sync-abi.sh
cp backend/src/glisk/contracts/GliskNFT.json frontend/src/lib/glisk-nft-abi.json
```

### 4. Update Tailwind Config

Edit `frontend/tailwind.config.js` to include source files:

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

### 5. Start Development Server

```bash
cd frontend
npm run dev
```

App should be running at `http://localhost:5173`

## Project Structure After Setup

```
frontend/
├── public/
│   └── vite.svg
├── src/
│   ├── components/
│   │   └── ui/              # shadcn/ui components (auto-generated)
│   ├── lib/
│   │   └── glisk-nft-abi.json  # Contract ABI (copied from backend)
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css
├── .env                      # Local config (gitignored)
├── .env.example             # Template (committed)
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.js
└── components.json          # shadcn/ui config
```

## Implementation Steps (Follow During Development)

Once setup is complete, implement components in this order:

### Step 1: Configure wagmi + RainbowKit

Create `frontend/src/lib/wagmi.ts`:

```typescript
import { getDefaultConfig } from '@rainbow-me/rainbowkit'
import { baseSepolia } from 'wagmi/chains'

export const config = getDefaultConfig({
  appName: 'Glisk NFT',
  projectId: 'YOUR_WALLETCONNECT_PROJECT_ID', // Get from https://cloud.walletconnect.com/
  chains: [baseSepolia],
})
```

**Note**: Get WalletConnect project ID from https://cloud.walletconnect.com/ (free, required for RainbowKit)

### Step 2: Wrap App with Providers

Update `frontend/src/main.tsx`:

```typescript
import '@rainbow-me/rainbowkit/styles.css'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { WagmiProvider } from 'wagmi'
import { RainbowKitProvider } from '@rainbow-me/rainbowkit'
import { config } from './lib/wagmi'

const queryClient = new QueryClient()

createRoot(document.getElementById('root')!).render(
  <WagmiProvider config={config}>
    <QueryClientProvider client={queryClient}>
      <RainbowKitProvider>
        <App />
      </RainbowKitProvider>
    </QueryClientProvider>
  </WagmiProvider>
)
```

### Step 3: Add Routing

Update `frontend/src/App.tsx`:

```typescript
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import CreatorMintPage from './pages/CreatorMintPage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/:creatorAddress" element={<CreatorMintPage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
```

### Step 4: Implement Components

**Header Component** (`frontend/src/components/Header.tsx`):
- Import `ConnectButton` from RainbowKit
- Show connected wallet address

**CreatorMintPage** (`frontend/src/pages/CreatorMintPage.tsx`):
- Use `useParams()` to extract `creatorAddress`
- Use `useAccount()` to check wallet connection
- Use `useWriteContract()` to trigger mint
- Use `useWaitForTransactionReceipt()` to track transaction
- Quantity selector with validation (1-10)
- Mint button (disabled if wallet not connected)
- Transaction status messages

### Step 5: Add Contract Integration

Create `frontend/src/lib/contract.ts`:

```typescript
import { Address } from 'viem'
import gliskNFTAbi from './glisk-nft-abi.json'

export const CONTRACT_ADDRESS = import.meta.env.VITE_CONTRACT_ADDRESS as Address
export const CHAIN_ID = parseInt(import.meta.env.VITE_CHAIN_ID)
export const GLISK_NFT_ABI = gliskNFTAbi.abi
```

## Manual Testing Checklist

### Test 1: Wallet Connection

1. Open app at `http://localhost:5173/0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0` (example creator address)
2. Click "Connect Wallet" button
3. Select wallet from RainbowKit modal (e.g., MetaMask)
4. Approve connection in wallet extension
5. **Expected**: Wallet address shown in header, mint button enabled

**Success Criteria**:
- [✓] Wallet modal appears on button click
- [✓] Wallet address displays after connection
- [✓] Connection persists on page refresh

### Test 2: Network Validation

1. Connect wallet on wrong network (e.g., Ethereum mainnet)
2. **Expected**: Network switch prompt or warning message
3. Switch to Base Sepolia in wallet settings
4. **Expected**: App recognizes correct network, mint button enabled

**Success Criteria**:
- [✓] App detects wrong network
- [✓] App works correctly on Base Sepolia

### Test 3: Mint Flow - Happy Path

1. Ensure wallet connected on Base Sepolia with sufficient ETH (>0.001 ETH for gas)
2. Enter quantity: 5
3. Click "Mint" button
4. **Expected**: Wallet prompts transaction approval
5. Approve transaction in wallet
6. **Expected**: "Minting..." message appears
7. Wait for transaction confirmation (10-30 seconds)
8. **Expected**: "Success! NFTs minted." message appears

**Success Criteria**:
- [✓] Wallet prompts with correct parameters (author address, quantity 5)
- [✓] "Minting..." status shown during pending transaction
- [✓] Success message appears after confirmation
- [✓] Mint button re-enabled after success

### Test 4: Mint Flow - User Rejection

1. Connect wallet, select quantity
2. Click "Mint"
3. **Reject** transaction in wallet
4. **Expected**: "Transaction cancelled" message appears
5. **Expected**: Mint button re-enabled, can try again

**Success Criteria**:
- [✓] Cancellation message shown (not generic error)
- [✓] UI returns to idle state
- [✓] Can retry mint without page refresh

### Test 5: Mint Flow - Insufficient Balance

1. Connect wallet with very low ETH balance (<0.0001 ETH)
2. Click "Mint"
3. **Expected**: Transaction fails with "insufficient funds" error

**Success Criteria**:
- [✓] Error message explains insufficient balance
- [✓] UI returns to idle state

### Test 6: Quantity Validation

1. Try entering quantity = 0
   - **Expected**: Input clamped to 1
2. Try entering quantity = 15
   - **Expected**: Input clamped to 10
3. Try entering quantity = -5
   - **Expected**: Input clamped to 1
4. Try entering quantity = "abc"
   - **Expected**: Input ignored or clamped to previous valid value

**Success Criteria**:
- [✓] Quantity always between 1-10
- [✓] Invalid inputs handled gracefully

### Test 7: Different Creator Addresses

1. Visit `/0x1234567890123456789012345678901234567890` (any valid address)
2. **Expected**: Page loads, can mint
3. Visit `/invalid` (invalid address format)
4. **Expected**: Page loads (may show error on mint attempt - acceptable for MVP)

**Success Criteria**:
- [✓] Dynamic routes work for any address
- [✓] Invalid addresses fail gracefully (contract revert is acceptable)

### Test 8: Edge Cases

1. Disconnect wallet during pending transaction
   - **Expected**: UI shows disconnected, but transaction continues on-chain
2. Switch to different wallet address during mint
   - **Expected**: App recognizes new address
3. Navigate away during pending transaction
   - **Expected**: Transaction continues on-chain (user can view on BaseScan)

**Success Criteria**:
- [✓] No crashes on unexpected wallet changes
- [✓] State updates reflect current wallet

## Debugging Tips

### Common Issues

**Issue**: "Module not found" errors for wagmi/viem
- **Fix**: Ensure `viem@2.x` installed (v2 required for wagmi compatibility)
- **Fix**: Run `npm install` again

**Issue**: RainbowKit modal doesn't appear
- **Fix**: Check that RainbowKit styles imported in `main.tsx`
- **Fix**: Verify provider order (WagmiProvider → QueryClientProvider → RainbowKitProvider)

**Issue**: Transaction fails with "wrong network"
- **Fix**: Switch wallet to Base Sepolia network
- **Fix**: Add Base Sepolia manually in wallet settings:
  - Network Name: Base Sepolia
  - RPC URL: https://sepolia.base.org
  - Chain ID: 84532
  - Currency Symbol: ETH

**Issue**: Contract ABI not found
- **Fix**: Verify `glisk-nft-abi.json` exists in `frontend/src/lib/`
- **Fix**: Re-sync ABI: `./sync-abi.sh` (if script exists) or copy manually from backend

**Issue**: Environment variables undefined
- **Fix**: Ensure `.env` file exists in `frontend/` directory
- **Fix**: Restart dev server after adding/editing `.env`
- **Fix**: Variables must start with `VITE_` prefix

**Issue**: "Invalid contract address" error on load
- **Fix**: Contract address must be checksummed (e.g., `0xFF215FD988498BB1CB390E307CDfC43B382c04DF`, not `0xff215...`)
- **Fix**: Use address from BaseScan with correct checksum

**Issue**: "Invalid creator address" shown on page
- **Fix**: URL must contain valid Ethereum address (40 hex chars starting with 0x)
- **Fix**: Check address format in URL path

**Issue**: Mint button doesn't respond (no wallet popup)
- **Fix**: Wait for "Loading contract data..." to finish
- **Fix**: Check console for contract/address validation errors

**Issue**: Transaction pending forever
- **Fix**: Check Base Sepolia network status (may be slow during congestion)
- **Fix**: View transaction on [Base Sepolia Explorer](https://sepolia.basescan.org/)
- **Fix**: Transaction will complete eventually (wagmi polls automatically)

### Browser Console Errors

Enable browser DevTools (F12) and check Console tab for errors:

- **Wallet errors**: Check if wallet extension is unlocked
- **Network errors**: Check if RPC endpoint is responsive (https://sepolia.base.org)
- **Contract errors**: Check if contract exists at `VITE_CONTRACT_ADDRESS`

### Useful Blockchain Tools

- **Base Sepolia Faucet**: https://www.coinbase.com/faucets/base-ethereum-sepolia-faucet
- **BaseScan Testnet**: https://sepolia.basescan.org/address/0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0
- **Base Sepolia RPC**: https://sepolia.base.org
- **WalletConnect Cloud**: https://cloud.walletconnect.com/ (for project ID)

## Build and Deployment

### Local Build

```bash
cd frontend
npm run build
```

Build output in `frontend/dist/` directory.

### Production Deployment (Nginx)

Create `nginx/frontend.conf`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    root /path/to/glisk/frontend/dist;
    index index.html;

    # SPA fallback routing
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
}
```

Deploy steps:

```bash
# Build frontend
cd frontend
npm run build

# Copy build to server (example)
rsync -avz dist/ user@server:/var/www/glisk-frontend/

# Restart nginx
sudo systemctl restart nginx
```

### Environment Variables in Production

Create `.env.production`:

```bash
VITE_CONTRACT_ADDRESS=0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0
VITE_CHAIN_ID=84532
```

Build with production env:

```bash
npm run build
```

Vite automatically uses `.env.production` during build.

## Next Steps After Quickstart

Once the frontend is working:

1. **Test on different browsers** (Chrome, Firefox, Safari)
2. **Test on mobile** with WalletConnect (if mobile wallet available)
3. **Verify transaction on BaseScan** to confirm mints are working
4. **Add error analytics** to track common user issues (future enhancement)
5. **Optimize bundle size** (check with `npm run build` and analyze bundle)

## Support and Troubleshooting

If you encounter issues not covered in this guide:

1. Check feature spec (`spec.md`) for requirements
2. Review data model (`data-model.md`) for state management
3. Check research notes (`research.md`) for technical decisions
4. Search wagmi/RainbowKit docs for hook usage examples
5. Check Base Sepolia network status and faucet availability

## Success Verification

After completing quickstart, verify:

- [✓] Dev server runs without errors
- [✓] Wallet connection works (address shown in UI)
- [✓] Can navigate to `/{creatorAddress}` routes
- [✓] Quantity selector validates input (1-10)
- [✓] Mint button triggers wallet approval
- [✓] Transaction status updates shown ("Minting...", "Success!")
- [✓] Can view transaction on BaseScan

If all items checked, frontend foundation is ready for development!
