# Quickstart: Unified Profile Page

**Date**: 2025-10-22
**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

## Prerequisites

- Backend running (`http://localhost:8000`)
- Frontend running (`http://localhost:5173`)
- Wallet with Base Sepolia ETH
- GliskNFT contract deployed on Base Sepolia

## Setup (15 minutes)

### 1. Install Dependencies

```bash
# Frontend
cd frontend
npm install thirdweb @coinbase/onchainkit

# Backend (no new dependencies)
cd backend
# All dependencies already installed
```

### 2. Environment Variables

**Frontend** (`.env`):
```bash
# Get from https://thirdweb.com/dashboard
VITE_THIRDWEB_CLIENT_ID=your_thirdweb_client_id

# Get from https://portal.cdp.coinbase.com/
VITE_ONCHAINKIT_API_KEY=your_onchainkit_api_key

# Existing
VITE_API_BASE_URL=http://localhost:8000
```

**Backend** (`.env`):
```bash
# No changes needed - uses existing config
```

### 3. Verify Contract (ERC721Enumerable)

```bash
# Check GliskNFT.sol implements ERC721Enumerable
cd contracts
cat src/GliskNFT.sol | grep "ERC721Enumerable"

# Expected output:
# import "@openzeppelin/contracts/token/ERC721/extensions/ERC721Enumerable.sol";
# contract GliskNFT is ERC721Enumerable, ...
```

## Implementation (8-10 hours)

### Phase 1: Backend API (1-2 hours)

**Step 1**: Create tokens router

```bash
cd backend/src/glisk/api/routes
# Create tokens.py with GET /authors/{wallet}/tokens endpoint
```

**Step 2**: Update token repository

```python
# backend/src/glisk/repositories/token.py
# Add get_by_author_paginated() method
```

**Step 3**: Register router

```python
# backend/src/glisk/main.py
from glisk.api.routes import tokens
app.include_router(tokens.router, prefix="/api")
```

**Test**:
```bash
curl "http://localhost:8000/api/authors/0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0/tokens?page=1&limit=20"
```

### Phase 2: Frontend Setup (30 min)

**Step 1**: Create thirdweb client

```typescript
// frontend/src/lib/thirdweb.ts
import { createThirdwebClient } from 'thirdweb';

export const client = createThirdwebClient({
  clientId: import.meta.env.VITE_THIRDWEB_CLIENT_ID,
});
```

**Step 2**: Update providers

```typescript
// frontend/src/main.tsx
import { ThirdwebProvider } from 'thirdweb/react';
import '@coinbase/onchainkit/styles.css';

<ThirdwebProvider>
  <OnchainKitProvider apiKey={...} chain={baseSepolia}>
    <App />
  </OnchainKitProvider>
</ThirdwebProvider>
```

**Test**: Verify app compiles

### Phase 3: Profile Page (4-5 hours)

**Step 1**: Create Profile.tsx

```typescript
// frontend/src/pages/Profile.tsx
// - Tab navigation (useSearchParams)
// - Author tab panel (copy from CreatorDashboard + ProfileSettings)
// - Collector tab panel (thirdweb useReadContract)
// - Pagination controls
```

**Step 2**: Update routing

```typescript
// frontend/src/App.tsx
import { Profile } from './pages/Profile';

<Route path="/profile" element={<Profile />} />
// Remove /creator-dashboard and /profile-settings routes
```

**Step 3**: Update header

```typescript
// frontend/src/components/Header.tsx
// Replace Dashboard/Settings buttons with single Profile button
```

**Test**: Manual navigation and tab switching

### Phase 4: OnchainKit Transaction (2 hours)

**Step 1**: Update CreatorMintPage.tsx

```typescript
// Replace useWriteContract with OnchainKit Transaction component
import { Transaction, TransactionButton, TransactionToast } from '@coinbase/onchainkit/transaction';

const calls = [{
  to: CONTRACT_ADDRESS,
  data: encodeFunctionData({
    abi: GLISK_NFT_ABI,
    functionName: 'batchMint',
    args: [address, promptText],
  }),
}];

<Transaction chainId={84532} calls={calls}>
  <TransactionButton />
  <TransactionToast />
</Transaction>
```

**Test**: Mint NFT with new UI

### Phase 5: Testing (1-2 hours)

**Manual Test Checklist**:
- [ ] Connect wallet → see Profile button
- [ ] Click Profile → navigate to `/profile?tab=author`
- [ ] Author tab shows prompt management UI
- [ ] Author tab shows X linking section
- [ ] Author tab shows authored NFTs (if any)
- [ ] Pagination works (20 per page)
- [ ] Click Collector tab → URL updates to `?tab=collector`
- [ ] Collector tab shows owned NFTs
- [ ] Pagination works (both tabs)
- [ ] Switch wallet → data refreshes
- [ ] Mint NFT → OnchainKit UI works
- [ ] Gas estimation shows
- [ ] Transaction status updates

## Common Issues

**"thirdweb client ID invalid"**:
- Verify `VITE_THIRDWEB_CLIENT_ID` in .env
- Get free key at https://thirdweb.com/dashboard

**"Contract doesn't support ERC721Enumerable"**:
- GliskNFT already implements it (verified in 001-full-smart-contract)
- Check deployed contract address matches .env

**"Backend API 500 error"**:
- Check PostgreSQL is running
- Verify author exists in database (created via prompt save)

**"No owned NFTs showing"**:
- Verify wallet owns NFTs on Base Sepolia
- Check contract address is correct
- Check RPC endpoint is responding

## Success Criteria

✅ All user stories pass (see spec.md)
✅ Tab switching < 500ms
✅ Authored NFTs load < 2 seconds
✅ Owned NFTs load < 3 seconds
✅ Pagination works correctly
✅ 100% feature parity with old pages

## Next Steps

After implementation:
1. Run `/speckit.tasks` to generate granular task breakdown
2. Implement tasks in order
3. Manual testing after each phase
4. Commit and push

**Future spec**: UI/UX polish (next feature after this prototype)
