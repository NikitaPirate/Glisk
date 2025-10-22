# Implementation Plan: Unified Profile Page with Author & Collector Tabs

**Branch**: `008-unified-profile-page` | **Date**: 2025-10-22 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/008-unified-profile-page/spec.md`

## Summary

Consolidate `/creator-dashboard` and `/profile-settings` into a unified `/profile` page with two tabs (Author/Collector). Author tab shows existing prompt management, X linking UI, and NEW authored NFTs list (from backend API). Collector tab shows NEW owned NFTs list (blockchain read via thirdweb ERC721Enumerable). Both tabs use 20-item pagination. Replace raw wagmi minting calls with OnchainKit Transaction component for improved UX (gas estimation, status tracking, batching support). **Minimal prototype design** - verify functionality works correctly before investing in UI polish (next spec).

**Key Technical Approach**:
- thirdweb v5 SDK for NFT display components (NFTMedia, NFTName) and blockchain reads
- Backend API endpoint `GET /api/authors/{wallet}/tokens` for authored NFTs
- Client-side blockchain read for owned NFTs using thirdweb's `getOwnedNFTs` (requires ERC721Enumerable)
- Tab routing via query params (`?tab=author` or `?tab=collector`)
- Direct code migration from existing pages (no refactoring - just copy/paste)
- OnchainKit Transaction component replaces raw wagmi calls in CreatorMintPage
- No database changes (use existing tokens.author_id foreign key)

## Technical Context

**Language/Version**: React 18 + TypeScript (via Vite), Python 3.13 (backend)

**Primary Dependencies**:
- Frontend NEW: `thirdweb` (NFT display, blockchain reads), `@coinbase/onchainkit` (transaction UX)
- Frontend Existing: React 18, wagmi v2, viem, RainbowKit, Tailwind CSS, shadcn/ui
- Backend Existing: FastAPI, SQLModel, psycopg3, Alembic

**Storage**:
- PostgreSQL: Use existing `tokens_s0` table with `author_id` foreign key (no migration)
- No new storage (frontend stateless)

**Testing**: Manual testing (frontend MVP), pytest (backend unit tests for new endpoint)

**Target Platform**: Modern browsers (Chrome, Safari, Firefox), Linux server (backend)

**Project Type**: Full-stack web (React frontend + FastAPI backend)

**Performance Goals**:
- Tab switching < 500ms (per success criteria SC-002)
- Authored NFTs load < 2 seconds (per success criteria SC-003)
- Owned NFTs load < 3 seconds (per success criteria SC-004)
- Handle up to 1000 NFTs per tab (50 pages pagination) without degradation (SC-007, SC-008)

**Constraints**:
- Minimal design (bare HTML, no polish - prototype only)
- No animations, skeletons, or decorative elements
- 20 NFTs per page (hardcoded)
- Client-side pagination for owned NFTs (all token IDs fetched once, paginated in memory)
- Server-side pagination for authored NFTs (SQL LIMIT/OFFSET)

**Scale/Scope**:
- Code size estimate: ~500 LOC frontend (new Profile page + header update), ~80 LOC backend (new API endpoint)
- Database impact: Read-only queries, no schema changes
- Contract verification: ERC721Enumerable implementation (already exists in GliskNFT.sol)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with GLISK Constitution v1.2.0:

- [x] **Simplicity First**: ✅ Direct code migration (no refactoring), client-side pagination for owned NFTs (simplest), server-side pagination for authored NFTs (standard pattern), minimal prototype design (no CSS complexity)
- [x] **Seasonal MVP**: ✅ Fast delivery (1-2 days implementation), no advanced features (filtering/sorting/analytics), manual testing only, acceptable to show all data without optimization
- [x] **Monorepo Structure**: ✅ Frontend (`/frontend/src/pages/Profile.tsx`), Backend (`/backend/src/glisk/api/routes/tokens.py`), No contract changes
- [x] **Smart Contract Security**: N/A (no contract modifications)
- [x] **Clear Over Clever**: ✅ Standard REST pagination, basic React hooks (useState, useEffect), straightforward tab switching logic

**Post-Design Re-check** (2025-10-22):
- ✅ **Simplicity**: No abstractions, direct thirdweb hooks, copy/paste existing code, basic pagination
- ✅ **MVP Focus**: Minimal design (no polish), manual testing only, no state persistence
- ✅ **Clear Code**: Standard patterns (query params for tabs, LIMIT/OFFSET pagination, thirdweb documented examples)

*No constitutional violations. Complexity Tracking section not needed.*

## Project Structure

### Documentation (this feature)

```
specs/008-unified-profile-page/
├── plan.md              # ✅ This file (implementation plan)
├── research.md          # ✅ thirdweb v5 SDK, OnchainKit Transaction, ERC721Enumerable patterns
├── data-model.md        # ✅ Database schema (no changes), pagination structures
├── quickstart.md        # ✅ Step-by-step setup, implementation, and testing guide
├── contracts/           # ✅ API endpoint specifications (OpenAPI-style docs)
│   ├── api-endpoints.md         # Backend API contract
│   └── internal-service-contracts.md  # Frontend-backend data contracts
└── tasks.md             # ⏳ Phase 2 output (/speckit.tasks command - NOT created yet)
```

### Source Code (repository root)

**Domains Affected**: Frontend (primary), Backend (new endpoint only)

```
frontend/                                         # Frontend domain
├── src/
│   ├── pages/
│   │   ├── Profile.tsx                          # 🆕 NEW: Unified profile page with tabs
│   │   ├── CreatorDashboard.tsx                 # ❌ DELETE: Functionality moved to Profile
│   │   ├── ProfileSettings.tsx                  # ❌ DELETE: Functionality moved to Profile
│   │   └── CreatorMintPage.tsx                  # 📝 MODIFY: Replace wagmi with OnchainKit Transaction
│   ├── components/
│   │   ├── Header.tsx                           # 📝 MODIFY: Single "Profile" button (remove Dashboard/Settings buttons)
│   │   └── ui/                                  # ✅ Existing: button, card, input
│   ├── lib/
│   │   ├── contract.ts                          # ✅ Existing: CONTRACT_ADDRESS, GLISK_NFT_ABI
│   │   └── thirdweb.ts                          # 🆕 NEW: thirdweb client setup
│   ├── App.tsx                                  # 📝 MODIFY: Update routes (remove old, add /profile)
│   └── main.tsx                                 # 📝 MODIFY: Add ThirdwebProvider wrapper
├── package.json                                  # 📝 MODIFY: Add thirdweb, @coinbase/onchainkit dependencies
└── ...

backend/                                          # Backend domain
├── src/glisk/
│   ├── api/routes/
│   │   └── tokens.py                            # 🆕 NEW: GET /api/authors/{wallet}/tokens endpoint
│   ├── repositories/
│   │   └── token.py                             # 📝 MODIFY: Add get_by_author_paginated() method
│   └── main.py                                  # 📝 MODIFY: Register tokens router
├── tests/
│   └── test_tokens_api.py                       # 🆕 NEW: Unit tests for new endpoint
└── ...

contracts/                                        # Smart contracts domain
└── ...                                           # ✅ No changes (ERC721Enumerable already implemented)
```

**File Size Estimates**:
- 🆕 `Profile.tsx`: ~400 LOC (tab navigation, 2 tab panels, pagination logic, NFT grids)
- 🆕 `thirdweb.ts`: ~10 LOC (client setup)
- 📝 `Header.tsx`: -20 LOC (remove 2 buttons, add 1 button)
- 📝 `App.tsx`: -5 LOC (remove 2 routes, add 1 route)
- 📝 `CreatorMintPage.tsx`: ~+50 LOC (OnchainKit Transaction component)
- 🆕 `tokens.py`: ~60 LOC (1 endpoint with Pydantic models)
- 📝 `token.py` (repository): +20 LOC (pagination query method)

**Total New Code**: ~550 LOC frontend, ~80 LOC backend

## Implementation Phases

### Phase 0: Research ✅ COMPLETE

**Artifacts**:
- [research.md](./research.md) - thirdweb v5 SDK (NFT components, ERC721Enumerable), OnchainKit Transaction component, pagination patterns
- [data-model.md](./data-model.md) - Database schema (no changes), pagination state structures
- [contracts/api-endpoints.md](./contracts/api-endpoints.md) - REST API specifications
- [contracts/internal-service-contracts.md](./contracts/internal-service-contracts.md) - Frontend-backend data contracts
- [quickstart.md](./quickstart.md) - Setup, implementation, and testing guide

**Key Decisions**:
1. **NFT Display**: thirdweb v5 SDK with NFTMedia/NFTName components (90% smaller than v4, works side-by-side with wagmi)
2. **Blockchain Reads**: thirdweb's `getOwnedNFTs` extension for ERC721Enumerable (automatic pagination handling)
3. **Transaction UX**: OnchainKit Transaction component replaces raw wagmi (auto gas estimation, status tracking, batching support)
4. **Tab Routing**: Query params (`?tab=author` | `?tab=collector`) with React Router's `useSearchParams` hook
5. **Pagination**: Client-side for owned NFTs (fetch all, paginate in memory), server-side for authored NFTs (SQL LIMIT/OFFSET)
6. **Database**: No migration (use existing `tokens_s0.author_id` foreign key to UUID)
7. **Code Migration**: Direct copy/paste from CreatorDashboard.tsx and ProfileSettings.tsx (no refactoring)

### Phase 1: Backend API Endpoint (1-2 hours)

**Tasks**:
1. Create tokens API routes (`api/routes/tokens.py`):
   - `GET /api/authors/{wallet_address}/tokens` endpoint
   - Query parameters: `page` (default 1), `limit` (default 20)
   - Response: `{ tokens: [...], total: number, page: number, limit: number }`

2. Update token repository (`repositories/token.py`):
   - Add `get_by_author_paginated(author_id: UUID, page: int, limit: int)` method
   - SQL query: `SELECT * FROM tokens_s0 WHERE author_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?`

3. Register routes (`main.py`):
   - Include `tokens.router` with `/api` prefix

**Testing**:
- Unit tests for pagination logic (page 1, page 2, boundary cases)
- Integration tests with test database (testcontainers)
- Manual testing with curl/Postman

**Success Criteria**:
- Endpoint returns correct tokens for given wallet address
- Pagination works (LIMIT/OFFSET logic)
- Returns 404 if author not found (empty list is valid response)

### Phase 2: Frontend Dependencies & Setup (30 minutes)

**Tasks**:
1. Install dependencies:
   ```bash
   cd frontend
   npm install thirdweb @coinbase/onchainkit
   ```

2. Create thirdweb client (`lib/thirdweb.ts`):
   ```typescript
   import { createThirdwebClient } from 'thirdweb';
   export const client = createThirdwebClient({
     clientId: import.meta.env.VITE_THIRDWEB_CLIENT_ID,
   });
   ```

3. Update main.tsx:
   - Wrap app with `<ThirdwebProvider>` (around RainbowKit provider)

4. Update .env:
   - Add `VITE_THIRDWEB_CLIENT_ID=your_client_id_here`

**Testing**:
- Verify app compiles without errors
- Verify providers render correctly
- Check browser console for thirdweb initialization

**Success Criteria**:
- No TypeScript errors
- App renders with new providers

### Phase 3: Profile Page Implementation (4-5 hours)

**Tasks**:
1. Create Profile page (`pages/Profile.tsx`):
   - Tab navigation with `useSearchParams()` hook
   - Default to `?tab=author` if no param
   - Two tab panels: Author (default), Collector

2. Author Tab Panel:
   - Copy prompt management UI from CreatorDashboard.tsx (lines 279-350)
   - Copy X account linking UI from ProfileSettings.tsx (lines 207-279)
   - NEW: Authored NFTs section:
     - Fetch from `GET /api/authors/{address}/tokens`
     - Display 20 per page with pagination controls
     - Use thirdweb NFTMedia/NFTName components

3. Collector Tab Panel:
   - Use thirdweb `useReadContract(getOwnedNFTs)` hook
   - Client-side pagination (slice array 20 at a time)
   - Display with thirdweb NFTMedia/NFTName components

4. Pagination Controls (shared component):
   - Previous/Next buttons
   - Disable when on first/last page
   - Disable during loading

**Testing**:
- Manual testing with wallet connected
- Test tab switching (URL updates, content changes)
- Test pagination (both tabs)
- Test wallet switching (data refreshes)
- Test no wallet (shows connection message)

**Success Criteria**:
- Tabs switch correctly, URL updates
- Authored NFTs load from backend
- Owned NFTs load from blockchain
- Pagination works (20 per page)
- Wallet changes trigger refresh

### Phase 4: Routing & Header Updates (1 hour)

**Tasks**:
1. Update App.tsx:
   - Remove `/creator-dashboard` route
   - Remove `/profile-settings` route
   - Add `/profile` route pointing to Profile component

2. Update Header.tsx:
   - Remove "Creator Dashboard" button
   - Remove "Profile Settings" button
   - Add single "Profile" button (navigates to `/profile`)

3. Delete old pages:
   - Delete `pages/CreatorDashboard.tsx`
   - Delete `pages/ProfileSettings.tsx`

**Testing**:
- Manual testing navigation from header
- Test direct URL navigation to `/profile`
- Test invalid tab params (should default to author)
- Verify old routes return 404

**Success Criteria**:
- Header shows single Profile button
- Navigation works correctly
- Old routes no longer accessible

### Phase 5: OnchainKit Transaction Integration (2 hours)

**Tasks**:
1. Update CreatorMintPage.tsx:
   - Replace `useWriteContract` with OnchainKit `<Transaction>` component
   - Keep existing prompt input, quantity selector
   - Replace mint button with `<TransactionButton>`
   - Add `<TransactionStatus>` for status display
   - Add `<TransactionToast>` for notifications
   - Remove manual `useWaitForTransactionReceipt` logic

2. Setup OnchainKit providers (if needed):
   - Wrap app with `<OnchainKitProvider>` in main.tsx
   - Configure API key in .env: `VITE_ONCHAINKIT_API_KEY`

**Testing**:
- Manual testing of mint flow
- Test gas estimation display
- Test transaction status updates
- Test success/error states
- Compare UX to old wagmi implementation

**Success Criteria**:
- Minting works correctly
- Gas estimation shows automatically
- Status updates in real-time
- Better UX than old implementation (loading states, error handling)

### Phase 6: Polish & Final Testing (1-2 hours)

**Tasks**:
1. Verify minimal design (prototype):
   - No fancy styling (keep basic Tailwind utilities)
   - No empty states with copy
   - No loading skeletons
   - Basic error text (no styled components)

2. End-to-end testing:
   - Test complete user flows (all user stories)
   - Test edge cases (no NFTs, exactly 20 NFTs, wallet switching)
   - Test error scenarios (API down, blockchain read fails)

3. Code cleanup:
   - Remove unused imports
   - Remove console.logs
   - Verify TypeScript strict mode compliance

**Testing**:
- Run through all acceptance scenarios from spec.md
- Test on different browsers (Chrome, Safari, Firefox)
- Test with different wallets (MetaMask, Coinbase Wallet)

**Success Criteria**:
- All acceptance scenarios pass
- No TypeScript errors
- No console errors
- Meets all success criteria from spec.md (SC-001 through SC-010)

## Complexity Tracking

*No violations - this section intentionally left blank.*

## Dependencies & Prerequisites

**External Dependencies**:
- thirdweb API key (free tier: https://thirdweb.com/dashboard)
- OnchainKit API key (Coinbase Developer Platform: https://portal.cdp.coinbase.com/)
- Existing backend API running (`http://localhost:8000`)
- Existing GliskNFT contract deployed with ERC721Enumerable

**Contract Verification** (Phase 0):
```solidity
// Verify GliskNFT.sol implements IERC721Enumerable
interface IERC721Enumerable {
  function balanceOf(address owner) external view returns (uint256 balance);
  function tokenOfOwnerByIndex(address owner, uint256 index) external view returns (uint256 tokenId);
  function totalSupply() external view returns (uint256);
}
```

**Database Prerequisites**:
- No migration needed
- Existing `tokens_s0` table with `author_id UUID REFERENCES authors(id)`
- Existing `authors` table with `wallet_address TEXT UNIQUE`

## Risk Mitigation

**Potential Issues**:
1. **thirdweb v5 breaking changes from v4**:
   - Mitigation: Use latest docs, test thoroughly, v5 works side-by-side with wagmi

2. **ERC721Enumerable gas costs for large collections**:
   - Mitigation: Client-side pagination reduces on-chain reads, fetch once and cache

3. **Backend pagination performance with 1000+ tokens**:
   - Mitigation: Use indexed `author_id` column, LIMIT/OFFSET is fast for <1M rows

4. **OnchainKit Transaction component compatibility**:
   - Mitigation: Test with existing wagmi setup, use documented integration patterns

**Rollback Plan**:
- Keep old pages in git history (easy revert)
- Feature flag not needed (MVP fast delivery)
- If thirdweb fails, fallback to raw wagmi contract reads
- If OnchainKit fails, revert to raw wagmi writes

## Timeline Estimate

**Total**: 9-12 hours (1-2 days with testing)

| Phase | Tasks | Time Estimate |
|-------|-------|---------------|
| Phase 0 | Research (already complete) | ✅ Done |
| Phase 1 | Backend API endpoint | 1-2 hours |
| Phase 2 | Frontend dependencies | 30 minutes |
| Phase 3 | Profile page implementation | 4-5 hours |
| Phase 4 | Routing & header updates | 1 hour |
| Phase 5 | OnchainKit integration | 2 hours |
| Phase 6 | Polish & testing | 1-2 hours |

**Blockers**:
- None (all dependencies available, no breaking changes expected)

**Next Steps After Implementation**:
- Run `/speckit.tasks` to generate granular task breakdown
- Implement tasks in order (backend first, then frontend)
- Manual testing after each phase
- Final verification against all acceptance scenarios
