# Research: Unified Profile Page with Author & Collector Tabs

**Date**: 2025-10-22
**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

## Overview

This document consolidates research findings for implementing a unified profile page that displays both authored NFTs (from backend database) and owned NFTs (from blockchain via ERC721Enumerable). Research covers thirdweb v5 SDK for NFT display/reads, OnchainKit Transaction component for improved minting UX, and pagination strategies.

---

## 1. thirdweb v5 SDK

### Decision

Use **thirdweb v5 unified SDK** (`thirdweb` package) for NFT display components and blockchain reads.

### Rationale

- **90% smaller bundle** compared to v4 (`@thirdweb-dev/react`)
- **10x faster execution**, 75% less memory usage
- **Works side-by-side with wagmi/viem** (no conflicts, both use viem internally)
- **Built-in ERC721Enumerable support** via `getOwnedNFTs` extension
- **React components for NFT display** (NFTMedia, NFTName, NFTDescription)
- **300+ wallet support** without bundle impact (tree-shaking)
- **Stateless, chain/wallet agnostic** architecture (simpler provider setup)

### Alternatives Considered

| Alternative | Pros | Cons | Rejected Because |
|-------------|------|------|------------------|
| **thirdweb v4** | Already familiar if used before | Heavy bundle (90% larger), slower execution, deprecated June 2025 | v5 is objectively better in all metrics, v4 deprecation timeline |
| **Raw wagmi + custom components** | Full control, no extra dependency | Must build NFT display logic, metadata parsing, IPFS resolution manually | Reinventing wheel, thirdweb v5 works with wagmi seamlessly |
| **Alchemy NFT API** | Robust indexing, fast queries | Requires API key, external dependency, costs at scale | Not needed for simple ownership reads, thirdweb is free |

### Installation

```bash
npm install thirdweb
```

**No breaking changes for existing wagmi setup** - both libraries coexist.

### Client Setup

```typescript
// frontend/src/lib/thirdweb.ts
import { createThirdwebClient } from 'thirdweb';

export const client = createThirdwebClient({
  clientId: import.meta.env.VITE_THIRDWEB_CLIENT_ID,
});
```

**Environment Variable**:
```bash
# .env
VITE_THIRDWEB_CLIENT_ID=your_client_id_here
```

Get free client ID at: https://thirdweb.com/dashboard

### Provider Setup

```typescript
// frontend/src/main.tsx
import { ThirdwebProvider } from 'thirdweb/react';

<ThirdwebProvider>
  <WagmiConfig>  {/* Existing wagmi provider */}
    <App />
  </WagmiConfig>
</ThirdwebProvider>
```

**Key Difference from v4**: No `activeChain` or `clientId` props on provider. Client is passed directly to components.

### Reading Owned NFTs (ERC721Enumerable)

**Core Hook**: `useReadContract` with `getOwnedNFTs` extension

```typescript
import { useReadContract } from 'thirdweb/react';
import { getOwnedNFTs } from 'thirdweb/extensions/erc721';
import { getContract, defineChain } from 'thirdweb';
import { client } from '@/lib/thirdweb';

// Define contract
const contract = getContract({
  client,
  chain: defineChain(84532), // Base Sepolia testnet
  address: '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0',
});

// In component
function OwnedNFTsList({ ownerAddress }: { ownerAddress: string }) {
  const { data: ownedNFTs, isLoading, error } = useReadContract(getOwnedNFTs, {
    contract,
    owner: ownerAddress,
  });

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <div>
      {ownedNFTs?.map((nft) => (
        <div key={nft.id.toString()}>
          <img src={nft.metadata.image} alt={nft.metadata.name} />
          <p>{nft.metadata.name}</p>
        </div>
      ))}
    </div>
  );
}
```

**Return Type**:
```typescript
interface NFT {
  id: bigint;
  tokenURI: string;
  metadata: {
    name?: string;
    description?: string;
    image?: string;
    attributes?: Array<{ trait_type: string; value: string }>;
  };
}
```

**IMPORTANT**: `getOwnedNFTs` requires contract to implement `IERC721Enumerable > tokenOfOwnerByIndex`. Glisk's GliskNFT.sol already extends `ERC721Enumerable` from OpenZeppelin, so this works out of the box.

### NFT Display Components

```typescript
import { NFTProvider, NFTMedia, NFTName, NFTDescription } from 'thirdweb/react';

<NFTProvider tokenId={nft.id} contract={contract}>
  <NFTMedia className="w-40 h-40 rounded-md" />
  <NFTName />
  <NFTDescription />
</NFTProvider>
```

**Features**:
- `NFTMedia` - Auto-detects image/video/audio, handles IPFS resolution
- Custom className for Tailwind styling
- Optional `loadingComponent` prop
- `mediaResolver` prop to override media source (skip network requests)

### Integration with wagmi

**No special setup required** - both use viem internally:

```typescript
import { useAccount } from 'wagmi';  // wagmi for wallet state
import { useReadContract } from 'thirdweb/react';  // thirdweb for NFTs

function MyComponent() {
  const { address } = useAccount();  // wagmi hook

  const { data: nfts } = useReadContract(getOwnedNFTs, {
    contract: gliskContract,
    owner: address!,
  });  // thirdweb hook

  return <div>{/* Render NFTs */}</div>;
}
```

### Pagination Strategy for Owned NFTs

**Decision**: **Client-side pagination** (fetch all token IDs once, paginate in memory)

**Rationale**:
- `getOwnedNFTs` returns all NFTs in single call (uses ERC721Enumerable's `balanceOf` + loop over `tokenOfOwnerByIndex`)
- Typical collections: <100 NFTs per user (performance acceptable)
- Simpler code (no RPC pagination complexity)
- Acceptable for MVP (constitution principle: simplicity first)

**Implementation**:
```typescript
// Fetch all owned NFTs once
const { data: allNFTs } = useReadContract(getOwnedNFTs, { contract, owner });

// Paginate in memory
const pageSize = 20;
const currentPageNFTs = allNFTs?.slice(
  (currentPage - 1) * pageSize,
  currentPage * pageSize
);
```

**If collection grows beyond 1000 NFTs** (edge case):
- Consider switching to `tokensOfOwner` (returns bigint[] only, lighter)
- Fetch metadata for current page only (20 at a time)
- Future optimization, not needed for MVP

---

## 2. OnchainKit Transaction Component

### Decision

Use **OnchainKit Transaction component** from Coinbase to replace raw wagmi transaction calls in CreatorMintPage.

### Rationale

- **Automatic gas estimation** (no manual `useEstimateGas` needed)
- **7 lifecycle states** with built-in status tracking (init → building → pending → success/error)
- **Transaction batching** support (if wallet supports ERC-4337 Smart Accounts)
- **Gas sponsorship** via Paymaster integration (future feature, easy to enable)
- **Better UX** than raw wagmi (loading states, toasts, error handling built-in)
- **Fully compatible with wagmi v2** (builds on top of wagmi, no conflicts)
- **React 18 + TypeScript** support with full type safety

### Alternatives Considered

| Alternative | Pros | Cons | Rejected Because |
|-------------|------|------|------------------|
| **Keep raw wagmi calls** | No new dependency, full control | Manual gas estimation, manual status tracking, worse UX | OnchainKit is objectively better UX, already uses wagmi internally |
| **Rainbowkit Transactions** | Already use Rainbowkit for wallet connection | Rainbowkit doesn't have transaction components | Feature doesn't exist |
| **thirdweb TransactionButton** | Would consolidate to single SDK | Less mature than OnchainKit, Coinbase backing is stronger | OnchainKit is more feature-rich (batching, sponsorship) |

### Installation

```bash
npm install @coinbase/onchainkit
```

**Peer Dependencies** (already installed for glisk):
- `react` & `react-dom` (React 18+)
- `wagmi` (v2.x)
- `viem` (v2.x)
- `@tanstack/react-query` (required by wagmi)

### Provider Setup

**Update main.tsx**:

```typescript
import { OnchainKitProvider } from '@coinbase/onchainkit';
import { base, baseSepolia } from 'viem/chains';
import '@coinbase/onchainkit/styles.css';  // Import styles

<WagmiConfig config={wagmiConfig}>
  <QueryClientProvider client={queryClient}>
    <OnchainKitProvider
      apiKey={import.meta.env.VITE_ONCHAINKIT_API_KEY}
      chain={baseSepolia}  // or base for mainnet
    >
      <ThirdwebProvider>
        <App />
      </ThirdwebProvider>
    </OnchainKitProvider>
  </QueryClientProvider>
</WagmiConfig>
```

**Environment Variable**:
```bash
# .env
VITE_ONCHAINKIT_API_KEY=your_api_key_here
```

Get API key at: https://portal.cdp.coinbase.com/

**IMPORTANT**: Place custom Wagmi and Query providers **outside** OnchainKitProvider (initialization order matters).

### Basic Usage Example

**Before (raw wagmi)**:
```typescript
const { writeContract, data: txHash } = useWriteContract();
const { isLoading, isSuccess } = useWaitForTransactionReceipt({ hash: txHash });

const handleMint = () => {
  writeContract({
    address: CONTRACT_ADDRESS,
    abi: GLISK_NFT_ABI,
    functionName: 'batchMint',
    args: [address, promptText],
  });
};

<Button onClick={handleMint} disabled={isLoading}>
  {isLoading ? 'Confirming...' : 'Mint NFT'}
</Button>
```

**After (OnchainKit)**:
```typescript
import {
  Transaction,
  TransactionButton,
  TransactionStatus,
  TransactionToast
} from '@coinbase/onchainkit/transaction';
import { encodeFunctionData } from 'viem';

const calls = [{
  to: CONTRACT_ADDRESS,
  data: encodeFunctionData({
    abi: GLISK_NFT_ABI,
    functionName: 'batchMint',
    args: [address, promptText],
  }),
}];

const handleStatus = (status: LifecycleStatus) => {
  if (status.statusName === 'success') {
    console.log('Minted!', status.statusData);
  }
};

<Transaction chainId={baseSepolia.id} calls={calls} onStatus={handleStatus}>
  <TransactionButton />  {/* Auto-styled, handles states */}
  <TransactionStatus />  {/* Shows status label */}
  <TransactionToast />   {/* Toast notifications */}
</Transaction>
```

**Benefits**:
- No manual `writeContract` + `useWaitForTransactionReceipt` orchestration
- Gas estimation automatic
- Status updates automatic (7 lifecycle states)
- Toast notifications built-in
- Better loading/error UI

### Transaction Component Hierarchy

```typescript
<Transaction>                // Main container
  <TransactionButton />       // Initiate tx (auto-styled)
  <TransactionStatus />       // Display status text
    <TransactionStatusLabel />
    <TransactionStatusAction />
  <TransactionSponsor />      // Gas sponsorship info (if enabled)
  <TransactionToast />        // Toast notifications
    <TransactionToastIcon />
    <TransactionToastLabel />
    <TransactionToastAction />
</Transaction>
```

**Shorthand** (automatically includes button and toast):
```typescript
<Transaction chainId={8453} calls={calls}>
  {/* TransactionButton and TransactionToast auto-included */}
</Transaction>
```

### Lifecycle States

```typescript
type LifecycleStatus =
  | { statusName: 'init' }  // Initial state
  | { statusName: 'error'; statusData: TransactionError }
  | { statusName: 'transactionIdle' }  // Before mutation
  | { statusName: 'buildingTransaction' }  // Resolving calls
  | { statusName: 'transactionPending' }  // Submitted, waiting
  | { statusName: 'transactionLegacyExecuted'; statusData: { transactionHashList } }
  | { statusName: 'success'; statusData: TransactionReceipt };  // Confirmed!
```

**State Flow**:
1. `init` → 2. `transactionIdle` → 3. `buildingTransaction` → 4. `transactionPending` → 5. `success` ✅ / `error` ❌

### Gas Estimation

**Automatic** - handled internally by OnchainKit. No manual `useEstimateGas` needed.

**How it works**:
- Calls are simulated during `buildingTransaction` state
- Gas estimate displayed in UI automatically
- If simulation fails, shows error before transaction submission

### Transaction Batching

**Automatic** if user's wallet supports ERC-4337 (Smart Accounts):

```typescript
const calls = [
  { to: '0xContract1', data: '0x...' },  // Call 1
  { to: '0xContract2', data: '0x...' },  // Call 2
  { to: '0xContract3', data: '0x...' },  // Call 3
];

<Transaction chainId={8453} calls={calls}>
  <TransactionButton />  // Single click executes all 3 calls in one tx
</Transaction>
```

**Benefits**:
- Reduced gas costs (one transaction instead of three)
- Better UX (one approval instead of three)
- Automatic fallback to sequential if wallet doesn't support batching

**For glisk**: Currently single call per mint, but useful for future multi-step flows (e.g., approve + mint).

### Gas Sponsorship (Paymaster)

**Future feature** - easy to enable:

```typescript
<OnchainKitProvider
  apiKey={process.env.VITE_ONCHAINKIT_API_KEY}
  chain={base}
  config={{
    paymaster: 'https://api.developer.coinbase.com/rpc/v1/base/YOUR_PAYMASTER_URL',
  }}
>
  ...
</OnchainKitProvider>

<Transaction chainId={8453} calls={calls} isSponsored={true}>
  <TransactionButton />
  <TransactionSponsor />  {/* Shows "Gas sponsored" message */}
</Transaction>
```

**Not implemented in MVP** but foundation is ready.

### wagmi v2 Integration

**Fully compatible** - OnchainKit uses wagmi internally:

```typescript
import { useAccount } from 'wagmi';  // wagmi hook
import { Transaction } from '@coinbase/onchainkit/transaction';  // OnchainKit component

function MintPage() {
  const { address, isConnected } = useAccount();  // wagmi

  const calls = [/* ... */];

  return isConnected ? (
    <Transaction chainId={8453} calls={calls}>
      <TransactionButton />
    </Transaction>
  ) : (
    <div>Connect wallet</div>
  );
}
```

**No conflicts** - both share same WagmiProvider and wagmi config.

### TypeScript Support

**Full type safety**:

```typescript
import type { LifecycleStatus, Call } from '@coinbase/onchainkit/transaction';
import type { Address } from 'viem';

interface MintProps {
  contractAddress: Address;
  recipient: Address;
}

const MintButton: React.FC<MintProps> = ({ contractAddress, recipient }) => {
  const calls: Call[] = [{  // Type-safe calls array
    to: contractAddress,
    data: encodeFunctionData({
      abi: myABI,
      functionName: 'mint',
      args: [recipient],
    }),
  }];

  const handleStatus = (status: LifecycleStatus): void => {  // Type-safe status
    if (status.statusName === 'success') {
      console.log(status.statusData.transactionHash);  // Full type inference
    }
  };

  return (
    <Transaction chainId={8453} calls={calls} onStatus={handleStatus}>
      <TransactionButton />
    </Transaction>
  );
};
```

---

## 3. Backend API Pagination

### Decision

Use **server-side pagination** with SQL LIMIT/OFFSET for authored NFTs.

### Rationale

- **Standard REST pattern** (page, limit query params)
- **Efficient for large datasets** (only fetch 20 rows per request)
- **Database-indexed query** (author_id has foreign key index)
- **Simpler than cursor-based** for MVP (constitution: simplicity first)
- **Performance acceptable** for <100k rows (typical collection size)

### Implementation

**Repository Method**:
```python
# backend/src/glisk/repositories/token.py

async def get_by_author_paginated(
    self,
    author_id: UUID,
    page: int = 1,
    limit: int = 20
) -> tuple[list[Token], int]:
    """Get tokens by author with pagination.

    Returns:
        Tuple of (tokens, total_count)
    """
    # Count query
    count_result = await self.session.execute(
        select(func.count(Token.id))
        .where(Token.author_id == author_id)
    )
    total = count_result.scalar_one()

    # Data query with LIMIT/OFFSET
    offset = (page - 1) * limit
    result = await self.session.execute(
        select(Token)
        .where(Token.author_id == author_id)
        .order_by(Token.created_at.desc())  # Newest first
        .limit(limit)
        .offset(offset)
    )
    tokens = list(result.scalars().all())

    return tokens, total
```

**API Endpoint**:
```python
# backend/src/glisk/api/routes/tokens.py

@router.get("/authors/{wallet_address}/tokens")
async def get_author_tokens(
    wallet_address: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    uow_factory=Depends(get_uow_factory),
) -> AuthorTokensResponse:
    """Get tokens authored by wallet address with pagination."""
    # 1. Normalize wallet address
    checksummed = Web3.to_checksum_address(wallet_address)

    # 2. Get author by wallet
    async with await uow_factory() as uow:
        author = await uow.authors.get_by_wallet(checksummed)
        if not author:
            return AuthorTokensResponse(tokens=[], total=0, page=page, limit=limit)

        # 3. Get paginated tokens
        tokens, total = await uow.tokens.get_by_author_paginated(
            author_id=author.id,
            page=page,
            limit=limit,
        )

        return AuthorTokensResponse(
            tokens=[TokenResponse.from_token(t) for t in tokens],
            total=total,
            page=page,
            limit=limit,
        )
```

**Response Model**:
```python
class TokenResponse(BaseModel):
    token_id: int
    status: TokenStatus
    image_url: Optional[str]
    metadata_cid: Optional[str]
    created_at: datetime

    @classmethod
    def from_token(cls, token: Token) -> "TokenResponse":
        return cls(
            token_id=token.token_id,
            status=token.status,
            image_url=token.image_url,
            metadata_cid=token.metadata_cid,
            created_at=token.created_at,
        )

class AuthorTokensResponse(BaseModel):
    tokens: list[TokenResponse]
    total: int
    page: int
    limit: int
```

### Alternatives Considered

| Alternative | Pros | Cons | Rejected Because |
|-------------|------|------|------------------|
| **Cursor-based pagination** | Better for real-time data, no offset skipping | More complex, harder to jump to page N | LIMIT/OFFSET simpler for MVP, data doesn't change frequently |
| **Fetch all tokens (no pagination)** | Simplest code | Slow for 1000+ tokens, wasteful | Violates performance goals (SC-007) |
| **GraphQL pagination** | Flexible queries | Requires GraphQL server setup | Overkill for simple REST endpoint |

### Frontend Integration

```typescript
// frontend/src/pages/Profile.tsx

const [authoredNFTs, setAuthoredNFTs] = useState<NFT[]>([]);
const [totalAuthored, setTotalAuthored] = useState(0);
const [currentPage, setCurrentPage] = useState(1);
const [isLoading, setIsLoading] = useState(false);

useEffect(() => {
  if (!address) return;

  const fetchAuthoredNFTs = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/authors/${address}/tokens?page=${currentPage}&limit=20`
      );
      const data = await response.json();
      setAuthoredNFTs(data.tokens);
      setTotalAuthored(data.total);
    } catch (error) {
      console.error('Failed to fetch authored NFTs:', error);
    } finally {
      setIsLoading(false);
    }
  };

  fetchAuthoredNFTs();
}, [address, currentPage]);

const totalPages = Math.ceil(totalAuthored / 20);

// Pagination controls
<div>
  <button
    onClick={() => setCurrentPage(p => p - 1)}
    disabled={currentPage === 1 || isLoading}
  >
    Previous
  </button>
  <span>Page {currentPage} of {totalPages}</span>
  <button
    onClick={() => setCurrentPage(p => p + 1)}
    disabled={currentPage === totalPages || isLoading}
  >
    Next
  </button>
</div>
```

---

## 4. Tab Navigation

### Decision

Use **React Router's `useSearchParams`** hook with query params (`?tab=author` or `?tab=collector`).

### Rationale

- **Standard web pattern** (shareable URLs)
- **Browser history support** (back/forward buttons work)
- **No client-side state** (URL is source of truth)
- **Already using React Router** in glisk frontend

### Implementation

```typescript
// frontend/src/pages/Profile.tsx
import { useSearchParams } from 'react-router-dom';

function Profile() {
  const [searchParams, setSearchParams] = useSearchParams();
  const activeTab = searchParams.get('tab') || 'author';  // Default to author

  const switchTab = (tab: 'author' | 'collector') => {
    setSearchParams({ tab });  // Updates URL without reload
  };

  return (
    <div>
      <div>
        <button
          onClick={() => switchTab('author')}
          style={{ fontWeight: activeTab === 'author' ? 'bold' : 'normal' }}
        >
          Prompt Author
        </button>
        <button
          onClick={() => switchTab('collector')}
          style={{ fontWeight: activeTab === 'collector' ? 'bold' : 'normal' }}
        >
          Collector
        </button>
      </div>

      {activeTab === 'author' && <AuthorTabPanel />}
      {activeTab === 'collector' && <CollectorTabPanel />}
    </div>
  );
}
```

**URL Examples**:
- `/profile` → redirects to `/profile?tab=author`
- `/profile?tab=author` → shows Author tab
- `/profile?tab=collector` → shows Collector tab
- `/profile?tab=invalid` → defaults to `/profile?tab=author`

### Alternatives Considered

| Alternative | Pros | Cons | Rejected Because |
|-------------|------|------|------------------|
| **Client-side state only** | Simpler code | Not shareable, no browser history support | Worse UX, violates web conventions |
| **Separate routes** | Clear separation (/profile/author, /profile/collector) | More routes to manage, overkill for 2 tabs | Query params simpler for MVP |
| **Hash-based routing** | Works without server config | Ugly URLs (#author, #collector), less standard | Query params cleaner |

---

## 5. Contract Verification (GliskNFT.sol)

### Decision

Verify that deployed GliskNFT contract implements **ERC721Enumerable** (required for thirdweb's `getOwnedNFTs`).

### Verification

```solidity
// contracts/src/GliskNFT.sol
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721Enumerable.sol";

contract GliskNFT is ERC721Enumerable, AccessControl, ReentrancyGuard {
  // ...contract code
}
```

**Interface Methods** (from OpenZeppelin ERC721Enumerable):
- `balanceOf(address owner) returns (uint256)` ✅
- `tokenOfOwnerByIndex(address owner, uint256 index) returns (uint256)` ✅
- `totalSupply() returns (uint256)` ✅

**Confirmed**: GliskNFT.sol already extends `ERC721Enumerable` (verified in 001-full-smart-contract spec). No changes needed.

**Impact**:
- thirdweb's `getOwnedNFTs` will work out of the box
- No need for custom indexing or subgraph
- Client-side pagination acceptable (enumerable contracts return all token IDs efficiently)

---

## Summary

| Technology | Decision | Key Benefit | Complexity | Status |
|------------|----------|-------------|------------|--------|
| **thirdweb v5 SDK** | Use for NFT display + blockchain reads | 90% smaller bundle, works with wagmi | Low | ✅ Researched |
| **OnchainKit Transaction** | Replace raw wagmi minting calls | Auto gas estimation, better UX | Low | ✅ Researched |
| **Backend Pagination** | SQL LIMIT/OFFSET for authored NFTs | Standard pattern, efficient | Low | ✅ Researched |
| **Frontend Pagination** | Client-side for owned NFTs | Simplest for <100 NFTs | Low | ✅ Researched |
| **Tab Navigation** | React Router query params | Shareable URLs, browser history | Low | ✅ Researched |
| **ERC721Enumerable** | Already implemented in GliskNFT | No changes needed | N/A | ✅ Verified |

**Total New Dependencies**: 2 (thirdweb, @coinbase/onchainkit)

**Risk Level**: Low (both libraries mature, well-documented, compatible with existing stack)

**Next Steps**: Proceed to Phase 1 design artifacts (data-model.md, contracts/, quickstart.md)
