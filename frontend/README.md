# Glisk Frontend

React-based Web3 frontend for the Glisk NFT minting platform.

## Overview

This is a proof of concept frontend for the Glisk NFT platform with three main pages:

- **`/`** - Author leaderboard: Discover top NFT creators ranked by total tokens minted
- **`/{creatorAddress}`** - Mint page: Connect wallet, select quantity (1-10), mint AI-generated NFTs using the creator's prompt
- **`/profile`** - Unified profile: Manage your AI generation prompt, claim creator rewards, link X (Twitter) account, view your authored and owned NFT collections

**Technology Stack**:

- **Next.js 15** + **React 18** + **TypeScript** (App Router)
- **RainbowKit** (wallet connection UI)
- **wagmi** + **viem** (Ethereum interactions)
- **@farcaster/miniapp-sdk** (Base mini app integration)
- **Tailwind CSS** + **shadcn/ui** (styling)
- **Next.js App Router** (file-based routing with server/client components)

**Network**: Base Mainnet (chainId: 8453)

**Key Features**:

- File-based routing with dynamic routes
- Server-side rendering (SSR) and static generation (SSG) where appropriate
- Wallet connection via RainbowKit (MetaMask, Coinbase Wallet, WalletConnect)
- NFT minting with quantity selection (1-10 tokens per transaction)
- Author discovery leaderboard (top creators by token count)
- Profile management (set AI generation prompt for your NFTs)
- Creator rewards claiming (withdraw accumulated ETH from mints)
- X (Twitter) account linking via OAuth 2.0
- NFT collection views using OnchainKit components (authored vs owned tabs)
- **Base mini app integration** - Farcaster SDK for social discovery and identity
- **Dynamic Farcaster embeds** - Custom share cards with action buttons per page

## Base Mini App Integration

Glisk is integrated with the **Base App** ecosystem as a mini app, providing:

- **Social Discovery**: Your app appears in Base App search and categories
- **Farcaster Identity**: Users can authenticate with their Farcaster accounts (FID)
- **Rich Embeds**: Share your app with beautiful previews in Base feeds
- **Seamless Launch**: Users can launch Glisk directly from Base App
- **Dynamic Embeds**: Each page has custom `fc:miniapp` metadata (home: "Open Glisk", creator pages: "MINT")

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
cp .env.example .env.local

# Start development server
npm run dev
```

App runs at `http://localhost:3000`

### Environment Variables

Create `frontend/.env.local` file (gitignored):

```bash
NEXT_PUBLIC_NETWORK=BASE_MAINNET
NEXT_PUBLIC_CONTRACT_ADDRESS=0xb43185E67D4Fb27115AC419C9F8A335cC0B837B9
NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID=your_project_id
NEXT_PUBLIC_ONCHAINKIT_API_KEY=your_api_key
NEXT_PUBLIC_PINATA_GATEWAY=gateway.pinata.cloud
NEXT_PUBLIC_PINATA_GATEWAY_TOKEN=your_token
```

See `.env.example` for complete template with all variables.

**Important**: Next.js requires `NEXT_PUBLIC_` prefix for browser-accessible variables.

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
│   ├── app/                      # Next.js 15 App Router
│   │   ├── layout.tsx            # Root layout (providers, metadata)
│   │   ├── page.tsx              # Home page (server component)
│   │   ├── HomePageClient.tsx    # Home page client logic
│   │   ├── providers.tsx         # React context providers
│   │   ├── [creatorAddress]/
│   │   │   ├── page.tsx          # Creator page (server component + metadata)
│   │   │   └── ClientPage.tsx    # Creator page client logic
│   │   └── profile/
│   │       ├── page.tsx          # Profile page (server component)
│   │       └── ClientPage.tsx    # Profile page client logic
│   ├── components/
│   │   ├── ui/                   # shadcn/ui components (auto-generated)
│   │   ├── HeaderNext.tsx        # Wallet connection UI
│   │   ├── PromptAuthor.tsx      # Author profile management
│   │   ├── Collector.tsx         # Owned NFTs view
│   │   ├── NFTCard.tsx           # NFT display component
│   │   ├── NFTGrid.tsx           # NFT grid layout
│   │   └── TokenRevealCard.tsx   # Token reveal status
│   ├── lib/
│   │   ├── contract.ts           # Contract address/ABI constants
│   │   ├── wagmi.ts              # wagmi configuration
│   │   ├── utils.ts              # shadcn/ui utilities
│   │   └── glisk-nft-abi.json    # Contract ABI (synced from backend)
│   ├── hooks/
│   │   └── useGliskNFTData.ts    # Custom hooks for contract data
│   └── index.css                 # Global styles (Tailwind imports)
├── public/
│   ├── app-icon.png              # App icon for Farcaster embeds
│   └── favicon.svg
├── .env.local                    # Local config (gitignored)
├── .env.example                  # Config template (tracked)
├── Dockerfile                    # Docker configuration
├── package.json
├── tsconfig.json
├── next.config.ts                # Next.js configuration
├── tailwind.config.js
├── components.json               # shadcn/ui config
└── README.md                     # This file
```

**Key Differences from Vite**:

- `src/app/` directory contains routes (not `src/pages/`)
- Each route has `page.tsx` (server component) and optional `ClientPage.tsx` (client component)
- `layout.tsx` provides shared UI and metadata
- No `index.html` or `main.tsx` entry point (Next.js handles this)
- Server components by default (add `'use client'` directive when needed)

## Development

### Available Scripts

```bash
# Start dev server (hot reload enabled, port 3000)
npm run dev

# Build production bundle (optimized SSR + static assets)
npm run build

# Start production server (after build)
npm start

# Type-check without emitting files
npm run type-check

# Lint code (ESLint)
npm run lint

# Format code (Prettier)
npm run format
```

### Key Concepts

**Routing**: Next.js App Router with file-based routing:

- `/` - Home page (`src/app/page.tsx`)
- `/[creatorAddress]` - Dynamic mint page (`src/app/[creatorAddress]/page.tsx`)
- `/profile` - Profile page (`src/app/profile/page.tsx`)

**Server vs Client Components**:

- **Server components** (default): Rendered on server, no JavaScript sent to client (better performance)
- **Client components** (`'use client'`): Interactive components with hooks, event handlers (wallet connections, forms)

**Metadata**: Each page exports `generateMetadata()` for dynamic SEO and Farcaster embeds.

**Wallet Connection**: RainbowKit provides pre-built wallet modal (supports MetaMask, Coinbase Wallet, WalletConnect)

**Contract Interaction**: Uses wagmi hooks:

- `useAccount()` - wallet connection status
- `useReadContract()` - query contract data (e.g., `mintPrice`)
- `useWriteContract()` - trigger transactions (e.g., `mint()`)
- `useWaitForTransactionReceipt()` - track transaction confirmation

**State Management**: React `useState` and `useEffect` only (no Redux/Zustand)

**Styling**: Tailwind utility classes + shadcn/ui components (Button, Input, Card)

## Manual Testing

### Quick Test

**Test 1: Leaderboard**

1. Visit `http://localhost:3000/`
2. View list of top authors ranked by token count
3. Click on any author to navigate to their mint page

**Test 2: Minting**

1. Visit `http://localhost:3000/0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0` (example creator address)
2. Click "Connect Wallet" button
3. Select wallet and approve connection
4. Enter quantity (1-10)
5. Click "Mint"
6. Approve transaction in wallet
7. Wait for confirmation (~10-30 seconds)
8. Verify "Success!" message appears

**Test 3: Profile Management**

1. Connect wallet
2. Visit `http://localhost:3000/profile`
3. **Author Tab**: Set AI generation prompt, claim rewards (if available), link X account
4. **Collector Tab**: View your owned NFTs with pagination

**Test 4: Farcaster Embeds**

1. Share `https://glisk.xyz/` in Farcaster → Should show "Open Glisk" button
2. Share `https://glisk.xyz/0x...` (creator page) in Farcaster → Should show "MINT" button

## Production Deployment

### Docker Build

The project includes a multi-stage Dockerfile optimized for Next.js:

```bash
# Build frontend image
docker build \
  --build-arg NEXT_PUBLIC_NETWORK=BASE_MAINNET \
  --build-arg NEXT_PUBLIC_CONTRACT_ADDRESS=0xb43185E67D4Fb27115AC419C9F8A335cC0B837B9 \
  --build-arg NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID=your_project_id \
  --build-arg NEXT_PUBLIC_ONCHAINKIT_API_KEY=your_api_key \
  --build-arg NEXT_PUBLIC_PINATA_GATEWAY=gateway.pinata.cloud \
  --build-arg NEXT_PUBLIC_PINATA_GATEWAY_TOKEN=your_token \
  -t glisk-frontend .

# Run container
docker run -p 3000:3000 glisk-frontend
```

**Alternative**: Use `docker-compose.yml` at repo root (includes backend, postgres, frontend).

### Next.js Standalone Build

For non-Docker deployments:

```bash
cd frontend
npm run build
npm start  # Starts Next.js production server on port 3000
```

**Build output**: `.next/` directory (Next.js optimized bundle)

### Environment Variables in Production

**IMPORTANT**: Next.js environment variables are handled differently than Vite:

- **Build-time variables**: Variables prefixed with `NEXT_PUBLIC_` are baked into the bundle at build time
- **Server-side variables**: Non-prefixed variables are available only on the server (not in browser)

For production, pass environment variables via:

1. **Docker build args** (recommended for containerized deployments)
2. **Environment file** (`.env.production.local`)
3. **System environment variables**

Example `.env.production.local`:

```bash
NEXT_PUBLIC_NETWORK=BASE_MAINNET
NEXT_PUBLIC_CONTRACT_ADDRESS=0xb43185E67D4Fb27115AC419C9F8A335cC0B837B9
# ... other NEXT_PUBLIC_ variables
```

### Hosting Options

**Recommended platforms**:

- **Vercel** (native Next.js support, zero config)
- **Railway** (Docker-based, easy setup)
- **Self-hosted** (Docker + reverse proxy like nginx/Caddy)

**Note**: Unlike Vite, Next.js is a **server-side framework** - you need a Node.js server running, not just static file hosting.

## Troubleshooting

### Common Issues

**"Module not found" errors**:

- Ensure `viem@2.x` installed (not v1.x)
- Run `npm install` again
- Clear `.next/` directory: `rm -rf .next && npm run build`

**RainbowKit modal doesn't appear**:

- Check RainbowKit styles imported in `providers.tsx`
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

- Ensure `.env.local` file exists in `frontend/` directory
- Restart dev server after editing `.env.local`
- Variables must start with `NEXT_PUBLIC_` prefix for browser access
- Check `next.config.ts` env configuration

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

**"'use client' directive" warnings**:

- Components using hooks (`useState`, `useEffect`, `useAccount`) need `'use client'` directive
- Server components (default) cannot use browser APIs or React hooks

**Hydration errors**:

- Ensure server and client render the same initial HTML
- Avoid using `window` or `localStorage` in server components
- Use `useEffect` for client-only logic

### Useful Links

- **BaseScan (Mainnet)**: https://basescan.org/address/0xb43185E67D4Fb27115AC419C9F8A335cC0B837B9
- **Base Mainnet RPC**: https://mainnet.base.org
- **Base Documentation**: https://docs.base.org/
- **Next.js Documentation**: https://nextjs.org/docs
- **WalletConnect Cloud**: https://cloud.walletconnect.com/ (for project ID)

## Documentation

- **Base Mini App Guide**: `BASE_MINIAPP.md` - Farcaster SDK integration and deployment
- **Migration Spec**: `openspec/specs/frontend-foundation/spec.md` - Next.js 15 migration details
- **Archived Vite Spec**: `specs/005-frontend-foundation-with/spec.md` - Original Vite implementation

## Smart Contract

**GliskNFT Contract** (Base Mainnet):

- **Address**: `0xb43185E67D4Fb27115AC419C9F8A335cC0B837B9`
- **ABI**: `frontend/src/lib/glisk-nft-abi.json`
- **Mint Function**: `mint(address promptAuthor, uint256 quantity) payable`
- **Network**: Base Mainnet (chainId: 8453)

## License

See repo root for license information.
