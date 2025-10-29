# Glisk Frontend

React-based Web3 frontend for the Glisk NFT minting platform.

## Overview

This is a proof of concept frontend for the Glisk NFT platform with three main pages:

- **`/`** - Author leaderboard: Discover top NFT creators ranked by total tokens minted
- **`/{creatorAddress}`** - Mint page: Connect wallet, select quantity (1-10), mint AI-generated NFTs using the creator's prompt
- **`/profile`** - Unified profile: Manage your AI generation prompt, claim creator rewards, link X (Twitter) account, view your authored and owned NFT collections

**Technology Stack**:

- **React 18** + **TypeScript** + **Vite** (build tool)
- **RainbowKit** (wallet connection UI)
- **wagmi** + **viem** (Ethereum interactions)
- **@farcaster/miniapp-sdk** (Base mini app integration)
- **Tailwind CSS** + **shadcn/ui** (styling)
- **React Router** (client-side routing)

**Network**: Base Mainnet (chainId: 8453)

**Key Features**:

- Multi-page navigation (leaderboard, mint, profile)
- Wallet connection via RainbowKit (MetaMask, Coinbase Wallet, WalletConnect)
- NFT minting with quantity selection (1-10 tokens per transaction)
- Author discovery leaderboard (top creators by token count)
- Profile management (set AI generation prompt for your NFTs)
- Creator rewards claiming (withdraw accumulated ETH from mints)
- X (Twitter) account linking via OAuth 2.0
- NFT collection views using OnchainKit components (authored vs owned tabs)
- **Base mini app integration** - Farcaster SDK for social discovery and identity

## Base Mini App Integration

Glisk is integrated with the **Base App** ecosystem as a mini app, providing:

- **Social Discovery**: Your app appears in Base App search and categories
- **Farcaster Identity**: Users can authenticate with their Farcaster accounts (FID)
- **Rich Embeds**: Share your app with beautiful previews in Base feeds
- **Seamless Launch**: Users can launch Glisk directly from Base App

**How it works**: Base mini apps use the Farcaster protocol for social identity and discovery. The `@farcaster/miniapp-sdk` handles app lifecycle (splash screen dismissal) and provides authentication/social features.

**Compatibility**: The SDK is fully compatible with your existing wallet stack (RainbowKit, wagmi, OnchainKit). No breaking changes.

**Learn more**: See [BASE_MINIAPP.md](BASE_MINIAPP.md) for deployment guide, manifest configuration, and account association setup.

## Quick Start

### Prerequisites

- **Node.js 18+** and **npm**
- **Web3 wallet** browser extension (MetaMask, Coinbase Wallet, etc.)
- **Base Mainnet ETH** (for minting NFTs and gas fees)

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
VITE_CONTRACT_ADDRESS=0xb43185E67D4Fb27115AC419C9F8A335cC0B837B9
VITE_CHAIN_ID=8453
```

See `.env.example` for template.

## Live Demo

**Production:** [glisk.xyz](https://glisk.xyz)
**Network:** Base Mainnet (chainId: 8453)
**Contract:** `0xb43185E67D4Fb27115AC419C9F8A335cC0B837B9`

**Example URLs:**

- Leaderboard: https://glisk.xyz/
- Mint page: https://glisk.xyz/0xb43185E67D4Fb27115AC419C9F8A335cC0B837B9
- Profile: https://glisk.xyz/profile

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── ui/              # shadcn/ui components (auto-generated)
│   │   ├── Header.tsx       # Wallet connection UI
│   │   ├── PromptAuthor.tsx # Author profile management
│   │   ├── Collector.tsx    # Owned NFTs view
│   │   ├── NFTCard.tsx      # NFT display component
│   │   ├── NFTGrid.tsx      # NFT grid layout
│   │   └── TokenRevealCard.tsx  # Token reveal status
│   ├── lib/
│   │   ├── contract.ts      # Contract address/ABI constants
│   │   ├── wagmi.ts         # wagmi configuration
│   │   ├── utils.ts         # shadcn/ui utilities
│   │   └── glisk-nft-abi.json  # Contract ABI (synced from backend)
│   ├── pages/
│   │   ├── AuthorLeaderboard.tsx  # Landing page with top authors
│   │   ├── CreatorMintPage.tsx    # Mint interface
│   │   └── ProfilePage.tsx        # Unified profile (author/collector tabs)
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

**Routing**: Three main routes:

- `/` - Author leaderboard
- `/:creatorAddress` - Dynamic mint page (extracts creator address from URL)
- `/profile` - Unified profile with tabs (`?tab=author` or `?tab=collector`)

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

**Test 1: Leaderboard**

1. Visit `http://localhost:5173/`
2. View list of top authors ranked by token count
3. Click on any author to navigate to their mint page

**Test 2: Minting**

1. Visit `http://localhost:5173/0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0` (example creator address)
2. Click "Connect Wallet" button
3. Select wallet and approve connection
4. Enter quantity (1-10)
5. Click "Mint"
6. Approve transaction in wallet
7. Wait for confirmation (~10-30 seconds)
8. Verify "Success!" message appears

**Test 3: Profile Management**

1. Connect wallet
2. Visit `http://localhost:5173/profile`
3. **Author Tab**: Set AI generation prompt, claim rewards (if available), link X account
4. **Collector Tab**: View your owned NFTs with pagination

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

- Switch wallet to Base Mainnet network (chainId: 8453)
- Add Base Mainnet manually in wallet settings:
  - Network Name: Base
  - RPC URL: https://mainnet.base.org
  - Chain ID: 8453
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

- Check Base Mainnet network status (may be slow during congestion)
- View transaction on [BaseScan](https://basescan.org/)
- Transaction will complete eventually (wagmi polls automatically)

### Useful Links

- **BaseScan (Mainnet)**: https://basescan.org/address/0xb43185E67D4Fb27115AC419C9F8A335cC0B837B9
- **Base Mainnet RPC**: https://mainnet.base.org
- **Base Documentation**: https://docs.base.org/
- **WalletConnect Cloud**: https://cloud.walletconnect.com/ (for project ID)

## Documentation

- **Base Mini App Guide**: `BASE_MINIAPP.md` - Farcaster SDK integration and deployment
- **Feature Spec**: `specs/005-frontend-foundation-with/spec.md`
- **Implementation Plan**: `specs/005-frontend-foundation-with/plan.md`
- **Quickstart Guide**: `specs/005-frontend-foundation-with/quickstart.md`
- **Research Notes**: `specs/005-frontend-foundation-with/research.md`
- **Data Model**: `specs/005-frontend-foundation-with/data-model.md`

## Smart Contract

**GliskNFT Contract** (Base Mainnet):

- **Address**: `0xb43185E67D4Fb27115AC419C9F8A335cC0B837B9`
- **ABI**: `frontend/src/lib/glisk-nft-abi.json`
- **Mint Function**: `mint(address promptAuthor, uint256 quantity) payable`
- **Network**: Base Mainnet (chainId: 8453)

## License

See repo root for license information.
