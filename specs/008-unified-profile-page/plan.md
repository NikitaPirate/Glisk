# Implementation Plan: Unified Profile Page with Author & Collector Tabs

**Branch**: `008-unified-profile-page` | **Date**: 2025-10-22 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/008-unified-profile-page/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Consolidate two separate pages (`/creator-dashboard` and `/profile-settings`) into a single unified `/profile` page with two tabs: "Prompt Author" and "Collector". The Prompt Author tab displays existing prompt management and X linking functionality plus a new paginated list of authored NFTs (fetched from backend API). The Collector tab displays owned NFTs (fetched from blockchain via ERC721Enumerable). Uses OnchainKit NFTCard components for rendering and tab navigation via query parameters.

## Technical Context

**Language/Version**: TypeScript 5.x + React 18 (frontend), Python 3.13 (backend for new API endpoint)
**Primary Dependencies**: @coinbase/onchainkit (NFTCard components), wagmi + viem (blockchain reads), react-router-dom (query param navigation)
**Storage**: N/A (frontend reads from backend API and blockchain RPC)
**Testing**: Manual testing for MVP (per constitution frontend standards)
**Target Platform**: Web browsers (modern Chrome/Firefox/Safari)
**Project Type**: Web frontend SPA + backend API extension
**Performance Goals**: Tab switching <500ms, authored NFTs load <2s, owned NFTs load <3s, pagination support for 1000+ NFTs
**Constraints**: Minimal styling (basic utility classes only), no state management libraries (useState only), reuse existing components without refactoring
**Scale/Scope**: Single unified page replacing 2 pages, ~5 new components/hooks, 1 new backend API endpoint, support 1000+ NFTs per wallet with pagination

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with GLISK Constitution v1.2.0:

- [x] **Simplicity First**: Solution consolidates 2 pages into 1 using direct wagmi hooks and query param routing (no complex state management)
- [x] **Seasonal MVP**: Design reuses existing components via copy-paste, minimal new code, ships fast for time-limited season
- [x] **Monorepo Structure**: Respects separation - frontend changes in `/frontend/src/`, backend API in `/backend/src/glisk/api/`
- [x] **Smart Contract Security**: Not applicable (no contract changes, only reads via ERC721Enumerable)
- [x] **Clear Over Clever**: Direct hooks (useAccount, useReadContract), basic useState, no abstractions or design patterns

**Frontend-Specific Standards (Constitution v1.2.0)**:
- [x] **React + TypeScript + Vite**: Uses existing stack, no new build tools
- [x] **Direct wagmi hooks**: No abstractions - balanceOf/tokenOfOwnerByIndex called directly
- [x] **No state management libraries**: useState only for tab state and pagination
- [x] **Basic styling**: Minimal Tailwind utilities matching existing pages
- [x] **Manual testing for MVP**: No automated tests required (constitution standard)

*No violations - all constitutional principles satisfied.*

## Project Structure

### Documentation (this feature)

```
specs/008-unified-profile-page/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   └── api-endpoints.md # Backend API contract for authored NFTs endpoint
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```
# GLISK Monorepo Structure (008-unified-profile-page)

frontend/src/
├── pages/
│   ├── ProfilePage.tsx            # NEW: Unified profile page with tabs
│   ├── CreatorDashboard.tsx       # REMOVE: Consolidated into ProfilePage
│   └── ProfileSettings.tsx        # REMOVE: Consolidated into ProfilePage
├── components/
│   ├── Header.tsx                 # MODIFY: Update navigation links
│   ├── PromptAuthor.tsx           # NEW: Tab component with prompt/X/NFTs
│   ├── Collector.tsx              # NEW: Tab component with owned NFTs
│   └── NFTGrid.tsx                # NEW: Reusable NFT grid with pagination
└── App.tsx                        # MODIFY: Update routes

backend/src/glisk/api/routes/
├── authors.py                     # MODIFY: Add GET /api/authors/{wallet}/tokens endpoint
└── tokens.py                      # NEW: Token query endpoints (if needed)

backend/src/glisk/repositories/
└── token.py                       # MODIFY: Add get_tokens_by_author_paginated method

contracts/                         # NO CHANGES (reads only via ERC721Enumerable)
```

**Structure Decision**:

This feature affects **frontend** and **backend** domains:

**Frontend (primary)**:
- Create new `/profile` page with tab navigation
- Migrate existing UI from CreatorDashboard and ProfileSettings
- Add NFT list components using OnchainKit
- Update routing and header navigation

**Backend (minor)**:
- Add new API endpoint: `GET /api/authors/{wallet_address}/tokens` with pagination
- Extend token repository with authored NFT query method
- No database schema changes required (author_id FK already exists)

## Complexity Tracking

*No violations - all constitutional principles satisfied after Phase 1 design.*

**Post-Design Re-Evaluation**:

All design artifacts (research.md, data-model.md, contracts/, quickstart.md) completed. Reviewing compliance:

- ✅ **Simplicity First**: Final design uses direct hooks, no new abstractions. Backend adds 1 simple GET endpoint. Frontend uses copy-paste from existing components.
- ✅ **Seasonal MVP**: Fast delivery confirmed - reuses 90% existing code, adds minimal new functionality. Estimated 2-3 days implementation.
- ✅ **Monorepo Structure**: Clean separation maintained - frontend changes isolated to `/frontend/src/pages/`, backend to `/backend/src/glisk/api/routes/`.
- ✅ **Smart Contract Security**: N/A (read-only blockchain calls, no contract modifications)
- ✅ **Clear Over Clever**: Implementation plan uses standard patterns (wagmi hooks, FastAPI routes, useState). No clever optimizations.

**Technical Decisions Alignment**:
- OnchainKit NFTCard: Coinbase-provided component (no custom implementation)
- useInfiniteReadContracts: Wagmi built-in hook (no custom pagination logic)
- useSearchParams: React Router built-in hook (no custom routing)
- Copy-paste UI migration: Constitution explicitly encourages this for MVP

**No complexity violations identified.**
