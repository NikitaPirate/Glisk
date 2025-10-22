# Research: Unified Profile Page with Author & Collector Tabs

**Date**: 2025-10-22
**Feature Branch**: `008-unified-profile-page`

This document consolidates research findings from Phase 0 to resolve all technical unknowns before implementation.

---

## 1. OnchainKit NFTCard Component

### Decision
Use `NFTCard` with custom subcomponents for flexibility. For the unified profile page, render NFTs using `NFTMedia`, `NFTTitle`, and basic layout.

### Rationale
- `NFTCardDefault` includes 5 subcomponents (too much for minimal prototype)
- Custom composition allows selective display (just image + title for cleaner UI)
- OnchainKit handles metadata fetching from Coinbase Developer Platform API
- Built-in loading states and error handling reduce boilerplate

### Code Example
```typescript
import { NFTCard } from '@coinbase/onchainkit/nft';
import { NFTMedia, NFTTitle } from '@coinbase/onchainkit/nft/view';

function NFTGrid({ tokens }: { tokens: { tokenId: string }[] }) {
  return (
    <div className="grid grid-cols-4 gap-4">
      {tokens.map((token) => (
        <NFTCard
          key={token.tokenId}
          contractAddress={CONTRACT_ADDRESS}
          tokenId={token.tokenId}
        >
          <NFTMedia />
          <NFTTitle />
        </NFTCard>
      ))}
    </div>
  );
}
```

### Required Setup
1. Wrap app in `OnchainKitProvider` with Base Sepolia chain
2. Obtain Coinbase Developer Platform API key (for metadata fetching)
3. Configure environment variable: `VITE_ONCHAINKIT_API_KEY`

### Performance Notes
- Each NFTCard makes API call to CDP (20 parallel requests for 20 NFTs)
- Images lazy-load by default (browser native `loading="lazy"`)
- Total load time: 1-2 seconds (metadata) + 2-4 seconds (images from IPFS)
- No virtualization needed for 20 items per page

### Alternative Considered
**Custom data hook with backend API**: Could fetch metadata from Glisk backend (PostgreSQL) instead of CDP API. Rejected for MVP to reduce backend complexity, but worth considering post-MVP for:
- Faster loads (no IPFS gateway resolution)
- No external API dependency
- Showing tokens before reveal (status-based placeholders)

### Documentation
- Official NFTCard Docs: https://docs.base.org/onchainkit/mint/nft-card
- OnchainKitProvider Setup: https://docs.base.org/onchainkit/config/onchainkit-provider

---

## 2. Reading Owned NFTs from ERC721Enumerable Contract

### Decision
Use `useInfiniteReadContracts` wagmi hook with multicall batching for pagination.

### Rationale
- Reduces RPC calls by ~95% via automatic Multicall3 batching (20 calls → 1 call)
- Native pagination support via `getNextPageParam` (TanStack Query integration)
- Type-safe with full ABI inference
- Stays well under 50 RPS rate limit on free CDP Base Node endpoint
- Handles wallets with 1000+ NFTs without performance degradation

### Code Example
```typescript
import { useInfiniteReadContracts } from 'wagmi';

const TOKENS_PER_PAGE = 20;

function useOwnedNFTs() {
  const { address } = useAccount();
  const { data: balance } = useReadContract({
    address: CONTRACT_ADDRESS,
    abi: GLISK_NFT_ABI,
    functionName: 'balanceOf',
    args: address ? [address] : undefined,
  });

  const { data, fetchNextPage, hasNextPage } = useInfiniteReadContracts({
    cacheKey: `owned-nfts-${address}`,
    contracts(pageParam) {
      const startIndex = pageParam as number;
      const tokensInBatch = Math.min(
        TOKENS_PER_PAGE,
        Number(balance || 0n) - startIndex
      );

      return Array.from({ length: tokensInBatch }, (_, i) => ({
        address: CONTRACT_ADDRESS,
        abi: GLISK_NFT_ABI,
        functionName: 'tokenOfOwnerByIndex',
        args: [address!, BigInt(startIndex + i)],
      }));
    },
    query: {
      enabled: !!address && !!balance && balance > 0n,
      initialPageParam: 0,
      getNextPageParam: (_, __, lastPageParam) => {
        const nextIndex = (lastPageParam as number) + TOKENS_PER_PAGE;
        return nextIndex < Number(balance || 0n) ? nextIndex : undefined;
      },
    },
  });

  const tokenIds = data?.pages.flatMap((page) =>
    page.map((result) => result.status === 'success' ? result.result : null)
  ).filter((id): id is bigint => id !== null) || [];

  return { tokenIds, fetchNextPage, hasNextPage };
}
```

### RPC Configuration
Current setup uses public Base Sepolia RPC (`https://sepolia.base.org`) via RainbowKit's `getDefaultConfig`. This is sufficient for MVP but limited to ~50 RPS.

For production, configure authenticated CDP Base Node:
```typescript
import { createConfig, http } from 'wagmi';

export const config = createConfig({
  chains: [baseSepolia],
  transports: {
    [baseSepolia.id]: http(import.meta.env.VITE_CDP_BASE_RPC_URL, {
      batch: { batchSize: 1000, wait: 0 },
      retryCount: 3,
      timeout: 10_000,
    }),
  },
});
```

### Performance Impact
| Scenario | Without Batching | With Batching | Reduction |
|----------|------------------|---------------|-----------|
| 20 NFTs | 21 RPC calls | 2 RPC calls | 90% |
| 100 NFTs | 101 RPC calls | 6 RPC calls | 94% |
| 200 NFTs | 201 RPC calls | 11 RPC calls | 95% |

### Documentation
- useInfiniteReadContracts: https://wagmi.sh/react/api/hooks/useInfiniteReadContracts
- HTTP Transport Configuration: https://wagmi.sh/react/api/transports/http
- Viem Multicall: https://viem.sh/docs/contract/multicall

---

## 3. React Router Query Parameter Navigation

### Decision
Use `useSearchParams` hook with validation and `replace: true` for defaults.

### Rationale
- Query params preserve tab state across refreshes (shareable URLs)
- Validation against `VALID_TABS` prevents rendering errors from invalid URLs
- `replace: true` when setting default prevents back button loop
- Built-in React Router feature (no external dependencies)

### Code Example
```typescript
import { useSearchParams } from 'react-router';

const VALID_TABS = ['author', 'collector'] as const;
type TabType = typeof VALID_TABS[number];

function ProfilePage() {
  const [searchParams, setSearchParams] = useSearchParams();

  const tabParam = searchParams.get('tab');
  const activeTab: TabType = VALID_TABS.includes(tabParam as TabType)
    ? (tabParam as TabType)
    : 'author';

  // Set default on first render (prevents back button loop)
  useEffect(() => {
    if (!tabParam) {
      setSearchParams({ tab: 'author' }, { replace: true });
    }
  }, []);

  const handleTabChange = (tab: TabType) => {
    setSearchParams({ tab }); // Creates history entry for back button
  };

  return (
    <div>
      <button onClick={() => handleTabChange('author')}>Author</button>
      <button onClick={() => handleTabChange('collector')}>Collector</button>
      {activeTab === 'author' ? <AuthorTab /> : <CollectorTab />}
    </div>
  );
}
```

### Edge Cases Handled
- **Invalid tab param** (`?tab=invalid`): Fallback to "author", no automatic URL correction
- **Missing tab param** (`/profile`): Set to "author" with `replace: true` (no history entry)
- **Back button**: Works correctly for user-initiated tab changes (no loop)
- **Tab state preservation**: Components unmount/remount on switch (clean state)

### Alternative Considered
**useState for tab state**: Simpler but loses state on refresh and isn't shareable. Rejected because users expect bookmarkable tabs (e.g., "Send user to Collector tab" in support requests).

### Documentation
- useSearchParams API: https://reactrouter.com/api/hooks/useSearchParams
- URLSearchParams MDN: https://developer.mozilla.org/en-US/docs/Web/API/URLSearchParams

---

## 4. Backend API Endpoint for Authored NFTs

### Decision
Add `GET /api/authors/{wallet_address}/tokens` endpoint with pagination query params.

### Rationale
- Reuses existing `AuthorRepository` pattern (no new architecture)
- Pagination via `offset` and `limit` query params (standard REST pattern)
- Database query uses existing `author_id` foreign key on `tokens_s0` table
- No schema changes required (author_id FK already exists from 003-003b)

### API Contract
```
GET /api/authors/0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0/tokens?offset=0&limit=20

Response 200:
{
  "tokens": [
    {
      "token_id": 1,
      "status": "revealed",
      "image_cid": "QmXyz...",
      "metadata_cid": "QmAbc...",
      "created_at": "2025-10-22T12:34:56Z"
    }
  ],
  "total": 45,
  "offset": 0,
  "limit": 20
}
```

### Repository Method
```python
# backend/src/glisk/repositories/token.py

async def get_tokens_by_author_paginated(
    self,
    author_id: UUID,
    offset: int = 0,
    limit: int = 20
) -> tuple[list[Token], int]:
    """Get paginated tokens for author with total count."""
    # Total count query
    count_stmt = select(func.count(Token.id)).where(Token.author_id == author_id)
    total = await self.session.scalar(count_stmt)

    # Paginated data query
    stmt = (
        select(Token)
        .where(Token.author_id == author_id)
        .order_by(Token.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await self.session.execute(stmt)
    tokens = result.scalars().all()

    return (tokens, total or 0)
```

### Frontend Integration
```typescript
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

async function fetchAuthoredNFTs(address: string, page: number) {
  const offset = (page - 1) * 20;
  const response = await fetch(
    `${API_BASE_URL}/api/authors/${address}/tokens?offset=${offset}&limit=20`
  );
  return response.json();
}
```

### Performance
- Query uses existing indexes (author_id FK index, created_at for ordering)
- Expected latency: <100ms for 1000 tokens
- No N+1 queries (single paginated query)

---

## 5. Component Migration Strategy

### Decision
Copy-paste existing UI from `CreatorDashboard.tsx` and `ProfileSettings.tsx` into new tab components. Delete old files after migration complete.

### Rationale
- Constitution v1.2.0 encourages copy-paste for MVP (avoid premature abstraction)
- Existing components are already tested and working
- Refactoring risk > copy-paste technical debt for time-boxed season
- Can refactor post-MVP if duplication becomes maintenance burden

### Migration Plan
1. Create `PromptAuthor.tsx` component
   - Copy prompt management UI from CreatorDashboard (lines 247-350)
   - Copy X linking UI from ProfileSettings (lines 199-289)
   - Add new NFT grid section below X linking
2. Create `Collector.tsx` component
   - New component using `useOwnedNFTs` hook
   - NFTGrid with pagination controls
3. Create `ProfilePage.tsx`
   - Tab navigation with query params
   - Render PromptAuthor or Collector based on activeTab
4. Update `App.tsx` routes
   - Remove `/creator-dashboard` and `/profile-settings`
   - Add `/profile` route
5. Update `Header.tsx`
   - Replace "Creator Dashboard" and "Profile Settings" buttons
   - Add single "Profile" button linking to `/profile?tab=author`
6. Delete old files after testing

### No Refactoring
- Prompt management logic stays identical (signature flow, save status, validation)
- X linking logic stays identical (OAuth flow, callback handling)
- No new abstractions or hooks beyond pagination

---

## Technology Stack Summary

| Component | Technology | Version | Justification |
|-----------|-----------|---------|---------------|
| Frontend Framework | React + TypeScript | 18 / 5.x | Existing stack (no changes) |
| Routing | react-router-dom | ^7.9.4 | Already installed, v7 API |
| Blockchain Reads | wagmi + viem | ^2.18.1 / ^2.38.3 | Existing wallet integration |
| NFT Display | @coinbase/onchainkit | ^1.1.1 | Already installed, Base-native |
| Backend Framework | FastAPI + Python | 3.13 | Existing API infrastructure |
| Database | PostgreSQL | 14+ | Existing schema with author_id FK |
| Styling | Tailwind CSS | ^4.1.15 | Existing utility-first setup |

**No new dependencies required** - all libraries already installed.

---

## Open Questions (All Resolved)

### Q1: Does OnchainKit require additional API keys?
**A**: Yes, requires Coinbase Developer Platform API key for metadata fetching. Configure via `VITE_ONCHAINKIT_API_KEY` environment variable.

### Q2: Can wagmi handle wallets with 500+ NFTs without timeouts?
**A**: Yes, multicall batching reduces RPC calls by 95%. For 500 NFTs across 25 pages, total RPC calls: 26 (well under 50 RPS limit).

### Q3: How to prevent back button loop with default tab?
**A**: Use `setSearchParams({ tab: 'author' }, { replace: true })` when setting default. This replaces the current history entry instead of adding a new one.

### Q4: Should we fetch all token IDs upfront or paginate API calls?
**A**: Fetch on-demand (20 per page). `useInfiniteReadContracts` handles pagination automatically. Reduces initial load time for large collections.

### Q5: Do we need a separate tokens API route or extend authors route?
**A**: Extend authors route with `/api/authors/{wallet}/tokens` endpoint. Keeps related functionality grouped and reuses existing repository patterns.

---

## Risk Mitigation

| Risk | Mitigation | Fallback |
|------|-----------|----------|
| OnchainKit metadata slow (>5s) | Implement loading skeletons | Show token IDs without metadata |
| RPC rate limits on free tier | Use multicall batching (95% reduction) | Upgrade to paid CDP plan |
| Large wallets (1000+ NFTs) timeout | Client-side pagination (20 per page) | Add server-side caching |
| Back button UX issues | Extensive manual testing per checklist | Remove query params, use hash routing |
| Copy-paste creates maintenance burden | Constitution allows this for MVP | Refactor post-MVP if needed |

---

## Next Steps

With all research complete, proceed to Phase 1:
1. Generate `data-model.md` (entities and relationships)
2. Generate `contracts/api-endpoints.md` (backend API spec)
3. Generate `quickstart.md` (setup and testing guide)
4. Update agent context with new learnings
