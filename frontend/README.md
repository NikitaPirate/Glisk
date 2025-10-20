# Glisk Frontend

React-based Web3 frontend for the Glisk NFT minting platform.

## Overview

This frontend allows users to mint NFTs by visiting creator-specific URLs (e.g., `/0x123...`). Users connect their Web3 wallet, select quantity (1-10), and mint NFTs that will be AI-generated based on the creator's prompt.

**Technology Stack**:

- **React 18** + **TypeScript** + **Vite** (build tool)
- **RainbowKit** (wallet connection UI)
- **wagmi** + **viem** (Ethereum interactions)
- **Tailwind CSS** + **shadcn/ui** (styling)
- **React Router** (client-side routing)

**Network**: Base Sepolia testnet (chainId: 84532)

## Quick Start

### Prerequisites

- **Node.js 18+** and **npm**
- **Web3 wallet** browser extension (MetaMask, Coinbase Wallet, etc.)
- **Base Sepolia testnet ETH** (get from [Base Sepolia faucet](https://www.coinbase.com/faucets/base-ethereum-sepolia-faucet))

### Setup Instructions

**From repo root** (`/Users/nikita/PycharmProjects/glisk`):

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Create local environment config
cp .env.example .env

# Start development server
npm run dev
```

App runs at `http://localhost:5173`

### Environment Variables

Create `frontend/.env` file (gitignored):

```bash
VITE_CONTRACT_ADDRESS=0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0
VITE_CHAIN_ID=84532
```

See `.env.example` for template.

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── ui/              # shadcn/ui components (auto-generated)
│   │   └── Header.tsx       # Wallet connection UI
│   ├── lib/
│   │   ├── contract.ts      # Contract address/ABI constants
│   │   ├── wagmi.ts         # wagmi configuration
│   │   ├── utils.ts         # shadcn/ui utilities
│   │   └── glisk-nft-abi.json  # Contract ABI (synced from backend)
│   ├── pages/
│   │   └── CreatorMintPage.tsx  # Main minting interface
│   ├── App.tsx              # Routing setup
│   ├── main.tsx             # App entry point with providers
│   └── index.css            # Global styles (Tailwind imports)
├── public/
│   └── vite.svg
├── .env                     # Local config (gitignored)
├── .env.example             # Config template (tracked)
├── .env.production          # Production config (tracked)
├── nginx/                   # Nginx config (at repo root)
│   └── frontend.conf
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.js
├── components.json          # shadcn/ui config
└── README.md                # This file
```

## Development

### Available Scripts

```bash
# Start dev server (hot reload enabled)
npm run dev

# Build production bundle
npm run build

# Preview production build locally
npm run preview

# Type-check without emitting files
npm run type-check

# Lint code (ESLint)
npm run lint

# Format code (Prettier)
npm run format
```

### Key Concepts

**Routing**: Dynamic route `/:creatorAddress` extracts creator address from URL

**Wallet Connection**: RainbowKit provides pre-built wallet modal (supports MetaMask, Coinbase Wallet, WalletConnect)

**Contract Interaction**: Uses wagmi hooks:

- `useAccount()` - wallet connection status
- `useReadContract()` - query contract data (e.g., `mintPrice`)
- `useWriteContract()` - trigger transactions (e.g., `mint()`)
- `useWaitForTransactionReceipt()` - track transaction confirmation

**State Management**: React `useState` only (no Redux/Zustand)

**Styling**: Tailwind utility classes + shadcn/ui components (Button, Input, Card)

## Manual Testing

See [quickstart.md](../specs/005-frontend-foundation-with/quickstart.md) for detailed testing guide.

### Quick Test

1. Visit `http://localhost:5173/0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0` (example creator address)
2. Click "Connect Wallet" button
3. Select wallet and approve connection
4. Enter quantity (1-10)
5. Click "Mint"
6. Approve transaction in wallet
7. Wait for confirmation (~10-30 seconds)
8. Verify "Success!" message appears

## Production Deployment

### Build

```bash
cd frontend
npm run build
```

Build output: `frontend/dist/`

### Nginx Configuration

Use `nginx/frontend.conf` (at repo root):

```bash
# Copy build to server
rsync -avz frontend/dist/ user@server:/usr/share/nginx/html/

# Copy nginx config
rsync nginx/frontend.conf user@server:/etc/nginx/conf.d/frontend.conf

# Restart nginx
ssh user@server 'sudo systemctl restart nginx'
```

**Key nginx features**:

- Static file serving with caching
- SPA fallback routing (`try_files $uri /index.html`)
- Security headers (CSP, X-Frame-Options, etc.)
- Blocks sensitive files (`.env`, `.git`, etc.)
- Cloudflare SSL support

### Environment Variables in Production

Environment variables are **baked into the bundle at build time** (not runtime). Ensure `.env.production` exists before building:

```bash
# frontend/.env.production
VITE_CONTRACT_ADDRESS=0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0
VITE_CHAIN_ID=84532
```

Vite automatically loads `.env.production` during `npm run build`.

## Troubleshooting

### Common Issues

**"Module not found" errors**:

- Ensure `viem@2.x` installed (not v1.x)
- Run `npm install` again

**RainbowKit modal doesn't appear**:

- Check RainbowKit styles imported in `main.tsx`
- Verify provider order: `WagmiProvider` → `QueryClientProvider` → `RainbowKitProvider`

**Transaction fails with "wrong network"**:

- Switch wallet to Base Sepolia network (chainId: 84532)
- Add Base Sepolia manually in wallet settings:
  - Network Name: Base Sepolia
  - RPC URL: https://sepolia.base.org
  - Chain ID: 84532
  - Currency Symbol: ETH

**Contract ABI not found**:

- Verify `glisk-nft-abi.json` exists in `frontend/src/lib/`
- Re-sync ABI: `./sync-abi.sh` (from repo root)

**Environment variables undefined**:

- Ensure `.env` file exists in `frontend/` directory
- Restart dev server after editing `.env`
- Variables must start with `VITE_` prefix

**"Invalid contract address" error**:

- Contract address must be checksummed (e.g., `0xFF215FD988498BB1CB390E307CDfC43B382c04DF`)
- Use address from BaseScan with correct checksum

**Mint button doesn't respond**:

- Wait for "Loading contract data..." to finish
- Check browser console for validation errors

**Transaction pending forever**:

- Check Base Sepolia network status (may be slow during congestion)
- View transaction on [BaseScan](https://sepolia.basescan.org/)
- Transaction will complete eventually (wagmi polls automatically)

### Useful Links

- **Base Sepolia Faucet**: https://www.coinbase.com/faucets/base-ethereum-sepolia-faucet
- **BaseScan Testnet**: https://sepolia.basescan.org/address/0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0
- **Base Sepolia RPC**: https://sepolia.base.org
- **WalletConnect Cloud**: https://cloud.walletconnect.com/ (for project ID)

## Documentation

- **Feature Spec**: `specs/005-frontend-foundation-with/spec.md`
- **Implementation Plan**: `specs/005-frontend-foundation-with/plan.md`
- **Quickstart Guide**: `specs/005-frontend-foundation-with/quickstart.md`
- **Research Notes**: `specs/005-frontend-foundation-with/research.md`
- **Data Model**: `specs/005-frontend-foundation-with/data-model.md`

## Smart Contract

**GliskNFT Contract** (Base Sepolia):

- **Address**: `0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0`
- **ABI**: `frontend/src/lib/glisk-nft-abi.json`
- **Mint Function**: `mint(address promptAuthor, uint256 quantity) payable`
- **Network**: Base Sepolia (chainId: 84532)

## License

See repo root for license information.
