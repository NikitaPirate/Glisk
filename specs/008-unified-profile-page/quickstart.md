# Quickstart: Unified Profile Page

**Feature Branch**: `008-unified-profile-page`
**Date**: 2025-10-22

This guide provides setup instructions and manual testing procedures for the unified profile page feature.

---

## Prerequisites

Ensure you have completed setup for previous features:

- [x] Backend running with database (003-003a-backend-foundation)
- [x] Frontend running with wallet integration (005-frontend-foundation)
- [x] Author management API working (006-author-profile-management)
- [x] X account linking working (007-link-x-twitter)
- [x] Tokens in database with author_id FK (003-003b-event-detection)

**New Requirements**:
- Coinbase Developer Platform API key (for OnchainKit metadata fetching)
- Test wallet with authored and owned NFTs (for manual testing)

---

## Environment Setup

### 1. Backend Configuration

No new environment variables required. Existing setup from previous features is sufficient.

**Verify `.env` file** (`backend/.env`):
```bash
# Database (003-003a-backend-foundation)
DATABASE_URL=postgresql+psycopg://glisk:glisk@localhost:5432/glisk

# RPC (for token recovery)
ALCHEMY_API_KEY=your_api_key
GLISK_NFT_CONTRACT_ADDRESS=0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0
NETWORK=BASE_SEPOLIA
```

---

### 2. Frontend Configuration

**Add OnchainKit API key** to `frontend/.env`:

```bash
# Existing variables (005-frontend-foundation, 007-link-x-twitter)
VITE_API_BASE_URL=http://localhost:8000
VITE_WALLETCONNECT_PROJECT_ID=your_project_id
VITE_CONTRACT_ADDRESS=0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0

# NEW: OnchainKit API key (for NFT metadata fetching)
VITE_ONCHAINKIT_API_KEY=your_coinbase_api_key
```

**How to get OnchainKit API key**:
1. Sign up at https://portal.cdp.coinbase.com
2. Create new project
3. Copy API key
4. Paste into `VITE_ONCHAINKIT_API_KEY`

**Optional: CDP Base Node RPC** (recommended for production):
```bash
# Override default Base Sepolia RPC with authenticated endpoint
VITE_CDP_BASE_RPC_URL=https://base-sepolia.node.coinbase.com/YOUR_API_KEY
```

---

## Installation

### 1. Backend Dependencies

No new backend dependencies required.

**Verify existing dependencies**:
```bash
cd backend
uv sync  # Installs all dependencies from pyproject.toml
```

---

### 2. Frontend Dependencies

OnchainKit is already installed (from 005-frontend-foundation).

**Verify installation**:
```bash
cd frontend
npm list @coinbase/onchainkit
# Expected: @coinbase/onchainkit@1.1.1 (or later)
```

If missing:
```bash
npm install @coinbase/onchainkit@^1.1.1
```

---

## Database Setup

**No migrations required**. This feature uses existing schema.

**Verify schema**:
```bash
cd backend
docker exec backend-postgres-1 psql -U glisk -d glisk <<EOF
\d authors
\d tokens_s0
EOF
```

**Expected output**:
- `authors` table with `wallet_address`, `prompt_text`, `twitter_handle`
- `tokens_s0` table with `author_id` foreign key to `authors.id`

---

## Running the Application

### 1. Start Backend

```bash
cd backend
uv run uvicorn glisk.main:app --reload
```

**Verify**:
- Server running on http://localhost:8000
- Swagger docs at http://localhost:8000/docs

---

### 2. Start Frontend

```bash
cd frontend
npm run dev
```

**Verify**:
- Frontend running on http://localhost:5173
- RainbowKit wallet connect working

---

## Manual Testing

### Test 1: Navigate to Profile Page (User Story 1)

**Objective**: Verify basic navigation and default tab behavior

**Steps**:
1. Open http://localhost:5173 in browser
2. Connect wallet (any wallet, doesn't need NFTs yet)
3. Click "Profile" button in header

**Expected**:
- [x] Browser navigates to `/profile?tab=author`
- [x] Prompt Author tab is active (highlighted)
- [x] Prompt management section visible
- [x] X linking section visible
- [x] Authored NFTs section visible (may be empty)

**Edge Case 1**: Navigate directly to `/profile` (no query param)
- [x] URL updates to `/profile?tab=author` (replace, no history entry)
- [x] Prompt Author tab displays

**Edge Case 2**: Navigate to `/profile?tab=invalid`
- [x] Prompt Author tab displays (fallback to default)
- [x] URL stays `/profile?tab=invalid` (no automatic correction)

---

### Test 2: Tab Switching (User Story 1)

**Objective**: Verify tab navigation updates URL without page reload

**Steps**:
1. On `/profile?tab=author` page
2. Click "Collector" tab button

**Expected**:
- [x] URL updates to `/profile?tab=collector`
- [x] Collector tab becomes active
- [x] Owned NFTs section displays
- [x] No full page reload (SPA behavior)

**Steps (continued)**:
3. Click "Author" tab button

**Expected**:
- [x] URL updates to `/profile?tab=author`
- [x] Prompt Author tab becomes active
- [x] No full page reload

**Edge Case**: Browser back button after tab switch
- [x] Clicking back from Collector tab returns to Author tab
- [x] URL updates correctly
- [x] No infinite loop

---

### Test 3: View Authored NFTs (User Story 2)

**Objective**: Verify authored NFTs fetch and display correctly

**Prerequisites**:
- Database has tokens with `author_id` matching connected wallet
- Run token recovery if needed: `cd backend && python -m glisk.cli.recover_tokens`

**Steps**:
1. Connect wallet with authored tokens
2. Navigate to Prompt Author tab

**Expected**:
- [x] "Loading..." message displays briefly
- [x] NFT grid displays within 2 seconds
- [x] Each NFT shows image (or placeholder if unrevealed)
- [x] Each NFT shows title/token ID
- [x] NFTs ordered by creation date (newest first)

**Edge Case 1**: Author has 0 tokens
- [x] No error message
- [x] Empty state displays (no NFTs)

**Edge Case 2**: Author has 25 tokens
- [x] First 20 tokens display on page 1
- [x] Pagination controls visible
- [x] "Next" button enabled

**Edge Case 3**: Switching wallets
- [x] NFT list updates to show new wallet's authored tokens
- [x] Pagination resets to page 1
- [x] No manual refresh required

---

### Test 4: Authored NFTs Pagination (User Story 2)

**Objective**: Verify pagination works correctly for large collections

**Prerequisites**:
- Test wallet with >20 authored tokens
- Seed database if needed:
  ```bash
  cd backend
  docker exec backend-postgres-1 psql -U glisk -d glisk <<EOF
  -- Insert test tokens for author (replace author_id with actual UUID)
  INSERT INTO tokens_s0 (token_id, author_id, status, created_at)
  SELECT
    1000 + generate_series,
    'author-uuid-here'::uuid,
    'revealed',
    NOW() - (generate_series || ' minutes')::interval
  FROM generate_series(1, 30);
  EOF
  ```

**Steps**:
1. On Prompt Author tab with 30 total tokens
2. Verify page 1 shows 20 tokens
3. Click "Next" pagination button

**Expected**:
- [x] Page 2 displays tokens 21-30 (10 tokens)
- [x] URL updates to `/profile?tab=author&page=2` (if deep linking implemented)
  - **OR** pagination state managed in component (no URL change)
- [x] "Previous" button enabled
- [x] "Next" button disabled (last page)

**Steps (continued)**:
4. Click "Previous" button

**Expected**:
- [x] Page 1 displays tokens 1-20
- [x] "Previous" button disabled (first page)
- [x] "Next" button enabled

**Edge Case**: Exactly 20 tokens
- [x] Pagination controls hidden (single page)

---

### Test 5: View Owned NFTs (User Story 3)

**Objective**: Verify owned NFTs fetch from blockchain correctly

**Prerequisites**:
- Test wallet that owns NFTs on Base Sepolia
- Mint tokens if needed via CreatorMintPage

**Steps**:
1. Connect wallet with owned tokens
2. Click "Collector" tab

**Expected**:
- [x] "Loading your collection..." message displays briefly
- [x] `balanceOf` call completes (<500ms)
- [x] `tokenOfOwnerByIndex` calls complete (<2 seconds for 20 tokens)
- [x] NFT grid displays owned tokens
- [x] Each NFT rendered using OnchainKit NFTCard component

**Edge Case 1**: Wallet owns 0 tokens
- [x] No error message
- [x] Empty state displays ("No NFTs owned")

**Edge Case 2**: Wallet owns 30 tokens
- [x] First 20 tokens display
- [x] "Load More" button visible
- [x] Click "Load More" → next 10 tokens append to list

**Edge Case 3**: RPC endpoint fails
- [x] Error message displays ("Failed to load NFTs")
- [x] Retry button available
- [x] Click retry → refetch balanceOf and tokenIds

---

### Test 6: Owned NFTs Pagination (User Story 3)

**Objective**: Verify infinite scroll / pagination for large collections

**Prerequisites**:
- Test wallet with >20 owned tokens
- Mint tokens if needed

**Steps**:
1. On Collector tab with 50 owned tokens
2. Verify first 20 tokens display
3. Scroll to bottom and click "Load More" button

**Expected**:
- [x] "Loading more..." message displays
- [x] Next 20 tokens append below existing tokens (no page reload)
- [x] Total 40 tokens visible
- [x] "Load More" button still visible (10 tokens remaining)

**Steps (continued)**:
4. Click "Load More" again

**Expected**:
- [x] Final 10 tokens append
- [x] Total 50 tokens visible
- [x] "Load More" button hidden (all tokens loaded)

---

### Test 7: Tab State Preservation (User Story 4)

**Objective**: Verify tab data persists when switching tabs

**Steps**:
1. On Prompt Author tab, navigate to page 2 (if >20 tokens)
2. Switch to Collector tab
3. Switch back to Prompt Author tab

**Expected**:
- [x] Prompt Author tab displays page 1 (state NOT preserved in MVP)
  - **Rationale**: Constitution allows this for MVP (no complex state management)

**Note**: State preservation is out of scope for MVP. Components unmount/remount on tab switch.

---

### Test 8: Wallet Change Behavior (User Story 2 & 3)

**Objective**: Verify data refreshes when wallet changes

**Prerequisites**:
- Two test wallets with different authored/owned tokens

**Steps**:
1. Connect Wallet A
2. On Prompt Author tab, verify Wallet A's authored tokens display
3. Switch to Wallet B via wallet provider

**Expected**:
- [x] Prompt Author tab immediately shows "Loading..."
- [x] Wallet B's authored tokens display
- [x] Pagination resets to page 1
- [x] No manual page refresh required

**Steps (continued)**:
4. Switch to Collector tab

**Expected**:
- [x] Collector tab shows "Loading your collection..."
- [x] Wallet B's owned tokens display
- [x] Pagination resets

---

### Test 9: Error Handling (Edge Cases)

**Objective**: Verify graceful error handling

**Test 9a: Backend API Error (Authored NFTs)**

**Steps**:
1. Stop backend server
2. Navigate to Prompt Author tab

**Expected**:
- [x] NFT section shows error message
- [x] Prompt management section still functional (independent)
- [x] X linking section still functional (independent)
- [x] Error message: "Failed to load NFTs. Please try again."

**Test 9b: RPC Endpoint Error (Owned NFTs)**

**Steps**:
1. Disconnect internet (or block RPC endpoint in browser DevTools)
2. Navigate to Collector tab

**Expected**:
- [x] Error message displays: "Network error. Failed to load NFTs."
- [x] Retry button available
- [x] Click retry → attempts to refetch
- [x] Reconnect internet → retry succeeds

**Test 9c: Wallet Not Connected**

**Steps**:
1. Disconnect wallet
2. Navigate to `/profile`

**Expected**:
- [x] Message displays: "Please connect your wallet to access Profile"
- [x] No errors in browser console
- [x] Connect wallet → page refreshes and shows tabs

---

### Test 10: OnchainKit NFTCard Rendering

**Objective**: Verify NFTs display correctly using OnchainKit components

**Prerequisites**:
- Wallet with revealed tokens (status="revealed", metadata_cid set)

**Steps**:
1. Navigate to Collector tab (or Prompt Author tab with revealed tokens)
2. Inspect NFT card rendering

**Expected**:
- [x] NFTMedia component displays image from IPFS
- [x] NFTTitle component displays token name from metadata
- [x] Loading skeleton displays before image loads
- [x] No broken image icons
- [x] Images lazy-load (only load when scrolled into view)

**Edge Case**: Unrevealed tokens (status="detected" or "generating")
- [x] Placeholder image displays (if implemented)
  - **OR** token excluded from list (if filtering by status)

---

## Performance Benchmarks

### Authored NFTs (Backend API)

**Target**: <2 seconds from tab click to full render

**Measure**:
```javascript
// In browser DevTools console on Prompt Author tab
performance.mark('start');
// Click Collector tab, then click Prompt Author tab
performance.mark('end');
performance.measure('tab-load', 'start', 'end');
console.log(performance.getEntriesByName('tab-load')[0].duration);
```

**Expected**:
- API response: <100ms (for <1000 tokens)
- Image loading: 1-2 seconds (IPFS gateway latency)
- **Total**: <2 seconds

---

### Owned NFTs (Blockchain RPC)

**Target**: <3 seconds from tab click to full render

**Measure**:
```javascript
// In browser DevTools console on Collector tab
performance.mark('start');
// Refresh page or switch from Author tab
performance.mark('end');
performance.measure('blockchain-load', 'start', 'end');
console.log(performance.getEntriesByName('blockchain-load')[0].duration);
```

**Expected**:
- `balanceOf` call: <500ms
- Multicall (20 tokens): <1 second
- OnchainKit metadata fetch: 1-2 seconds
- **Total**: <3 seconds

---

### Tab Switching

**Target**: <500ms for tab switch (excluding data fetch)

**Measure**:
```javascript
// Click Collector tab from Author tab (data already cached)
performance.mark('switch-start');
// Tab content appears
performance.mark('switch-end');
performance.measure('tab-switch', 'switch-start', 'switch-end');
```

**Expected**: <500ms (URL update + component remount)

---

## Troubleshooting

### Issue: OnchainKit NFTs Not Rendering

**Symptoms**: NFT cards show loading spinner indefinitely

**Diagnosis**:
1. Check browser DevTools console for errors
2. Verify `VITE_ONCHAINKIT_API_KEY` is set
3. Check Coinbase Developer Platform API quota

**Fix**:
```bash
# Verify API key in frontend/.env
cat frontend/.env | grep ONCHAINKIT

# Restart frontend dev server
cd frontend
npm run dev
```

---

### Issue: Authored NFTs Return Empty Array

**Symptoms**: Prompt Author tab shows "No NFTs" despite mints

**Diagnosis**:
```bash
# Check if author record exists
docker exec backend-postgres-1 psql -U glisk -d glisk <<EOF
SELECT * FROM authors WHERE wallet_address = '0xYOUR_WALLET_HERE';
EOF

# Check if tokens have author_id FK
docker exec backend-postgres-1 psql -U glisk -d glisk <<EOF
SELECT token_id, author_id FROM tokens_s0 LIMIT 10;
EOF
```

**Fix**:
- Run token recovery: `cd backend && python -m glisk.cli.recover_tokens`
- Verify author created: Navigate to `/creator-dashboard` and save prompt

---

### Issue: Owned NFTs RPC Timeout

**Symptoms**: "Failed to load NFTs" on Collector tab after 10+ seconds

**Diagnosis**:
- Check RPC endpoint latency in browser DevTools Network tab
- Public Base Sepolia RPC may be slow during high usage

**Fix**:
```bash
# Upgrade to CDP Base Node authenticated RPC
# Add to frontend/.env
VITE_CDP_BASE_RPC_URL=https://base-sepolia.node.coinbase.com/YOUR_API_KEY

# Update wagmi config in frontend/src/lib/wagmi.ts
# (See research.md Section 2: RPC Configuration)
```

---

### Issue: Pagination Doesn't Work

**Symptoms**: Clicking "Next" does nothing

**Diagnosis**:
- Check browser console for JavaScript errors
- Verify `total` field in API response

**Fix**:
- Ensure backend endpoint returns `total` field
- Ensure frontend calculates `totalPages = Math.ceil(total / 20)`
- Check pagination state management in component

---

### Issue: Tab State Not Preserved

**Symptoms**: Switching tabs resets pagination to page 1

**Expected Behavior**: This is correct for MVP (per constitution). Tab state preservation is out of scope.

**Future Enhancement** (post-MVP):
- Implement `sessionStorage` persistence
- OR keep components mounted but hidden (CSS `display: none`)

---

## Validation Checklist

Before marking feature complete, verify:

**Functional Requirements**:
- [ ] FR-001: Single `/profile` route accessible from header
- [ ] FR-002: Tab navigation via `?tab=author` or `?tab=collector`
- [ ] FR-003: Defaults to Author tab when no/invalid query param
- [ ] FR-004: URL updates without full page reload
- [ ] FR-005: Prompt management UI displays in Author tab
- [ ] FR-006: X linking UI displays in Author tab
- [ ] FR-007: Authored NFTs paginated list displays
- [ ] FR-008: Authored NFTs fetched from backend API
- [ ] FR-009: Owned NFTs paginated list displays
- [ ] FR-010: Owned NFTs fetched via ERC721Enumerable
- [ ] FR-011: 20 NFTs per page in both tabs
- [ ] FR-012: Pagination controls for >20 NFTs
- [ ] FR-013: OnchainKit NFTCard components used
- [ ] FR-014: Data refreshes on wallet change
- [ ] FR-015: Pagination resets on wallet change
- [ ] FR-016: Requires wallet connection
- [ ] FR-017: Pagination hidden for ≤20 NFTs
- [ ] FR-018: Pagination disabled during loading
- [ ] FR-019: Backend errors handled gracefully
- [ ] FR-020: Blockchain errors handled with retry
- [ ] FR-021: Minimal styling (basic HTML/Tailwind)

**Success Criteria**:
- [ ] SC-001: Navigation <1 second
- [ ] SC-002: Tab switching <500ms
- [ ] SC-003: Authored NFTs load <2s
- [ ] SC-004: Owned NFTs load <3s
- [ ] SC-005: Pagination 100% functional
- [ ] SC-006: Wallet change refresh <3s
- [ ] SC-007: 1000 authored NFTs no degradation
- [ ] SC-008: 1000 owned NFTs no degradation
- [ ] SC-009: Prompt management 100% functional
- [ ] SC-010: X linking 100% functional

**User Stories**:
- [ ] User Story 1: Navigate to unified profile page
- [ ] User Story 2: View authored NFTs
- [ ] User Story 3: View owned NFTs
- [ ] User Story 4: Tab switching (state NOT preserved - expected for MVP)

**Edge Cases** (from spec.md):
- [ ] Invalid tab query param → defaults to author
- [ ] Backend API error → error state in NFT section only
- [ ] Blockchain RPC error → error state with retry
- [ ] Exactly 20 NFTs → pagination hidden
- [ ] 0 authored, 10 owned → both valid states
- [ ] Rapid tab switching → debounced/cancelled requests
- [ ] Pagination clicks during loading → disabled

---

## Next Steps

After validation complete:
1. Delete old files: `CreatorDashboard.tsx`, `ProfileSettings.tsx`
2. Update header navigation to single "Profile" button
3. Remove old routes from `App.tsx`
4. Commit changes on `008-unified-profile-page` branch
5. Create pull request with test evidence (screenshots)
6. Merge to main after review

**Post-MVP Enhancements** (future specs):
- Tab state preservation via sessionStorage
- Deep linking to specific tab + page: `/profile?tab=collector&page=3`
- Polished UI with colors, typography, loading skeletons
- Filtering NFTs by status (detected, revealed, failed)
- Sorting NFTs by date, token ID
- Individual NFT detail pages
