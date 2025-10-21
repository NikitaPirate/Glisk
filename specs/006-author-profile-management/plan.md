# Implementation Plan: Author Profile Management

**Branch**: `006-author-profile-management` | **Date**: 2025-10-20 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/006-author-profile-management/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement creator dashboard functionality allowing NFT authors to manage their AI generation prompts and claim accumulated ETH rewards. The feature spans both backend (API endpoints, wallet signature verification) and frontend (new `/creator-dashboard` page, wallet integration). Authors can set/update their prompt text (stored in database for backend image generation only - never exposed via API) and withdraw their 50% share of mint proceeds from the smart contract's `authorClaimable` mapping. Dashboard displays prompt status indicator (configured/not configured) but does not show saved prompt text.

## Technical Context

**Language/Version**:
- Backend: Python 3.13 (standard GIL-enabled version)
- Frontend: React 18 + TypeScript (via Vite)

**Primary Dependencies**:
- Backend: FastAPI, SQLModel, psycopg3 (async), Pydantic, structlog, pytest
- Frontend: wagmi + viem (Ethereum), RainbowKit (wallet UI), React Router, Tailwind CSS
- Web3: eth-account for signature verification (NEEDS CLARIFICATION: verify signature verification library choice)

**Storage**:
- PostgreSQL (existing `authors` table with wallet_address UNIQUE constraint)
- On-chain: Smart contract `authorClaimable` mapping (read-only from backend/frontend)

**Testing**:
- Backend: pytest + testcontainers for integration tests
- Frontend: Manual testing for MVP (automated tests deferred post-MVP per constitution)

**Target Platform**:
- Backend: Linux server (existing FastAPI app)
- Frontend: Web browser (Base Sepolia network via RPC)

**Project Type**: Web (monorepo with backend + frontend domains)

**Performance Goals**:
- Prompt save: <2 seconds end-to-end (signature + DB write)
- Balance query: <5 seconds (RPC call to contract)
- Claim transaction: <2 minutes (Base Sepolia confirmation time)

**Constraints**:
- Signature verification MUST use constant-time comparison (security)
- Frontend MUST handle wallet disconnection/reconnection gracefully
- Backend MUST validate wallet ownership before any state changes
- API responses <500ms p95 (excluding blockchain RPC calls)

**Scale/Scope**:
- Expected authors: ~100-1000 in Season 0
- Concurrent dashboard users: ~10-50
- Database: Existing `authors` table, no migrations needed (NEEDS CLARIFICATION: verify schema matches requirements)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with GLISK Constitution v1.2.0:

- [x] **Simplicity First**: Solution uses simplest approach, complexity is justified
  - ✅ Reuses existing `authors` table (no new tables)
  - ✅ Direct FastAPI endpoints (no complex patterns)
  - ✅ Direct wagmi hooks in frontend (no abstractions)
  - ✅ EIP-191 message signing (standard, well-understood)
  - ✅ Write-only prompts eliminate need for authenticated read endpoints (simpler auth model)

- [x] **Seasonal MVP**: Design targets fast delivery, optimized for ~1-3 month lifecycle
  - ✅ Two core features only (prompt management + reward claiming)
  - ✅ Manual frontend testing (no test infrastructure overhead)
  - ✅ No advanced features (analytics, galleries, social integrations deferred)
  - ✅ Leverages existing Author model and repository

- [x] **Monorepo Structure**: Respects `/contracts/`, `/backend/`, `/frontend/` separation
  - ✅ Backend: New routes in `backend/src/glisk/api/routes/`
  - ✅ Frontend: New page in `frontend/src/pages/CreatorDashboard.tsx`
  - ✅ No contract changes needed (reads existing `authorClaimable` mapping, calls existing `claimAuthorRewards()`)

- [x] **Smart Contract Security**: If contracts involved, security patterns are followed
  - ✅ No new contract code (reads state only)
  - ✅ Claim transaction uses existing `claimAuthorRewards()` function (already audited)
  - ✅ Wallet signature verification prevents unauthorized actions

- [x] **Clear Over Clever**: Implementation plan prioritizes clarity and maintainability
  - ✅ Standard REST endpoints (`POST /api/authors/prompt`, `GET /api/authors/{address}`)
  - ✅ Descriptive function names (verify_wallet_signature, update_author_prompt)
  - ✅ Explicit error handling with actionable messages
  - ✅ No complex state management (useState only)

*All constitutional principles satisfied. No complexity violations.*

## Project Structure

### Documentation (this feature)

```
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```
# GLISK Monorepo Structure - Author Profile Management Changes

backend/
├── src/glisk/
│   ├── api/routes/
│   │   └── authors.py                 # NEW: Author API endpoints
│   ├── models/
│   │   └── author.py                  # EXISTING: No changes (already has wallet_address + prompt_text)
│   ├── repositories/
│   │   └── author.py                  # EXISTING: May add update_prompt() method
│   ├── services/
│   │   └── wallet_signature.py        # NEW: EIP-191 signature verification
│   └── core/
│       └── blockchain.py              # EXISTING: May add get_author_claimable_balance() helper
└── tests/
    ├── test_wallet_signature.py       # NEW: Signature verification tests
    └── test_author_routes.py          # NEW: API endpoint tests

frontend/
├── src/
│   ├── pages/
│   │   └── CreatorDashboard.tsx       # NEW: Dashboard page component
│   ├── components/
│   │   ├── PromptEditor.tsx           # NEW: Prompt management component
│   │   └── RewardsClaim.tsx           # NEW: Rewards claiming component
│   ├── hooks/
│   │   ├── useAuthorPrompt.ts         # NEW: Fetch/update prompt hook
│   │   └── useClaimableBalance.ts     # NEW: Read contract balance hook
│   └── App.tsx                        # MODIFY: Add /creator-dashboard route

contracts/                              # NO CHANGES
└── src/GliskNFT.sol                   # Read-only: authorClaimable mapping, claimAuthorRewards()
```

**Structure Decision**:
- **Backend domain**: New API routes + signature verification service
- **Frontend domain**: New dashboard page + supporting components/hooks
- **No contract changes**: Reads existing state, calls existing functions

## Complexity Tracking

*No constitutional violations. Feature adheres to all principles.*

**Post-Design Re-Evaluation**:
- ✅ **Simplicity First**: Confirmed - reuses existing models, standard REST endpoints, direct wagmi hooks, write-only prompts simplify auth
- ✅ **Seasonal MVP**: Confirmed - 2-3 day implementation, no advanced features, manual testing only
- ✅ **Monorepo Structure**: Confirmed - clean backend/frontend separation, no contract changes
- ✅ **Smart Contract Security**: Confirmed - reads existing state only, uses audited claim function
- ✅ **Clear Over Clever**: Confirmed - explicit error messages, descriptive function names, standard patterns

**Technology Choices Rationale**:
- `eth-account`: Already installed as web3.py dependency (zero new dependencies)
- `useSignMessage` + `useReadContract`: Existing wagmi patterns from CreatorMintPage.tsx (consistency)
- UPSERT logic in repository: Simpler than separate create/update endpoints (reduces API surface)

---

## Phase 0: Research Findings

All unknowns resolved. See [research.md](research.md) for details.

**Key Decisions**:
1. **Signature Library**: `eth-account` (existing dependency via web3.py)
2. **Database Schema**: No changes needed (existing `authors` table sufficient)
3. **Frontend Signature**: `useSignMessage` hook (standard wagmi pattern)
4. **Error Handling**: Structured errors with actionable messages
5. **Blockchain RPC**: `useReadContract` + `useWriteContract` (matches existing patterns)

---

## Phase 1: Design Artifacts

All design artifacts generated:
- ✅ [data-model.md](data-model.md) - Entity design, repository methods, API schemas
- ✅ [contracts/api-contracts.md](contracts/api-contracts.md) - HTTP API specifications with examples
- ✅ [quickstart.md](quickstart.md) - Developer setup and testing guide

**Implementation Scope**:
- **Backend**: 3 new files (signature service, API routes, repository method)
- **Frontend**: 1 new page (CreatorDashboard.tsx with status indicator) + route registration
- **No Migrations**: Reuses existing database schema (prompts stored but not exposed via API)
- **Estimated LOC**: ~500 total (200 backend, 300 frontend)

---

## Next Steps

**Phase 2** (not included in `/speckit.plan` output):
- Run `/speckit.tasks` to generate tasks.md with dependency-ordered implementation tasks
- Tasks will break down implementation into 6 phases (Setup, Foundational, User Stories 1-3, Polish)
