# Implementation Plan: Author Leaderboard Landing Page

**Branch**: `009-create-a-main` | **Date**: 2025-10-22 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/009-create-a-main/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Create a landing page (/) that displays a ranked list of NFT prompt authors sorted by total minted token count. The feature enables visitor discovery of popular creators by aggregating token counts from the database and presenting them in a simple, clickable list that links to existing author profile pages.

**Technical Approach**: Backend adds new GET /api/authors/leaderboard endpoint that queries tokens_s0 table with GROUP BY aggregation. Frontend creates new root route (/) with basic React component that fetches and displays the data with minimal Tailwind styling.

## Technical Context

**Languages/Versions**:
- Backend: Python 3.13
- Frontend: TypeScript 5.x + React 18

**Primary Dependencies**:
- Backend: FastAPI (existing API framework), SQLModel + psycopg3 (existing database layer)
- Frontend: React 18, react-router-dom (existing router), Tailwind CSS (existing styling)

**Storage**: PostgreSQL 14+ (existing database with tokens_s0 table)

**Testing**:
- Backend: pytest + testcontainers (focus on SQL aggregation query correctness)
- Frontend: Manual testing for MVP (automated tests deferred per constitution)

**Target Platform**: Web application (browser-based)

**Project Type**: Full-stack web (backend API + frontend SPA)

**Performance Goals**:
- API response time: <500ms for 50 authors (SC-005)
- Page load to first render: <3 seconds (SC-001)

**Constraints**:
- No database schema changes (use existing tokens_s0 table with author_id foreign key)
- No modifications to existing profile page (/{authorAddress})
- Minimal styling only (Simplicity First principle)

**Scale/Scope**:
- MVP: Top 50 authors maximum
- Expected dataset: <100 authors initially, <1000 tokens total
- 2 new files (backend route, frontend component)
- ~200 LOC total

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with GLISK Constitution v1.2.0:

- [x] **Simplicity First**: ✅ Uses simplest approach - direct SQL GROUP BY aggregation, basic React component with useState, no abstractions or design patterns
- [x] **Seasonal MVP**: ✅ Targets fast delivery (~1-2 days implementation), simple list UI with no pagination/search/filters for MVP
- [x] **Monorepo Structure**: ✅ Respects structure - backend route in `/backend/src/glisk/api/routes/`, frontend component in `/frontend/src/pages/`
- [x] **Smart Contract Security**: ✅ N/A - no smart contract changes required
- [x] **Clear Over Clever**: ✅ Direct implementation - SQL query in repository method, fetch + map in React component, descriptive names (`get_author_leaderboard`, `AuthorLeaderboard.tsx`)

**Additional Constitutional Compliance**:
- [x] **Frontend Standards (v1.2.0)**: Direct wagmi hooks not needed (no blockchain reads), useState for loading state, basic Tailwind only, manual testing
- [x] **Backend Standards (v1.1.0)**: Repository pattern (add method to existing AuthorRepository), pytest focus on aggregation query correctness

**Result**: ✅ ALL CHECKS PASSED - No violations, no complexity justification needed

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

This feature affects **backend** and **frontend** domains only. No contracts or shared types needed.

```
backend/
├── src/glisk/
│   ├── api/routes/
│   │   └── authors.py          # MODIFIED: Add GET /leaderboard endpoint
│   └── repositories/
│       └── author.py           # MODIFIED: Add get_author_leaderboard() method
└── tests/
    └── test_author_leaderboard.py  # NEW: Test aggregation query

frontend/
├── src/
│   ├── pages/
│   │   └── AuthorLeaderboard.tsx   # NEW: Landing page component
│   └── App.tsx                 # MODIFIED: Change root route from Navigate to AuthorLeaderboard
└── (manual testing - no test files)
```

**Files to Create** (2 new files):
- `backend/tests/test_author_leaderboard.py` - Test leaderboard aggregation query
- `frontend/src/pages/AuthorLeaderboard.tsx` - Landing page component

**Files to Modify** (3 existing files):
- `backend/src/glisk/api/routes/authors.py` - Add leaderboard endpoint
- `backend/src/glisk/repositories/author.py` - Add aggregation query method
- `frontend/src/App.tsx` - Change root route

## Complexity Tracking

*No violations - section not applicable*

---

## Implementation Phases

### Phase 0: Outline & Research ✅ COMPLETE

**Deliverable**: [research.md](./research.md)

**Key Findings**:
- SQL aggregation with GROUP BY is optimal approach (no new dependencies needed)
- React useState sufficient for state management (no Redux/TanStack Query)
- No database schema changes required (use existing tables)
- API response format: flat array of `{author_address, total_tokens}` objects
- Secondary sorting by wallet address for deterministic tie-breaking

**Time Estimate**: 1 hour (research completed during planning)

---

### Phase 1: Design & Contracts ✅ COMPLETE

**Deliverables**:
- [data-model.md](./data-model.md) - No new entities, documents existing tables and aggregation query
- [contracts/api-contract.md](./contracts/api-contract.md) - OpenAPI spec for GET /api/authors/leaderboard
- [quickstart.md](./quickstart.md) - Manual testing guide with database seeding scripts
- CLAUDE.md updated with new database reference

**Design Decisions**:
- Repository method: `AuthorRepository.get_author_leaderboard()` returns list of tuples
- API response model: `LeaderboardResponse = list[AuthorLeaderboardEntry]`
- Frontend component: `AuthorLeaderboard.tsx` with useState for data and loading
- Routing: Replace root path Navigate with direct AuthorLeaderboard component

**Time Estimate**: 1 hour (completed during planning)

---

### Phase 2: Implementation Tasks (Next Step)

**Command**: Run `/speckit.tasks` to generate detailed task breakdown

**Expected Tasks** (preview):

1. **Backend - Repository Layer**
   - Add `get_author_leaderboard()` method to `AuthorRepository`
   - Implement SQL aggregation query with JOIN, GROUP BY, ORDER BY, LIMIT
   - Write unit tests for aggregation correctness

2. **Backend - API Layer**
   - Add `GET /leaderboard` endpoint to `authors.py` router
   - Define `AuthorLeaderboardEntry` Pydantic model
   - Wire endpoint to repository method
   - Add error handling (500 for database errors)

3. **Frontend - Component**
   - Create `AuthorLeaderboard.tsx` page component
   - Implement fetch logic with useState for data and loading
   - Render list with Tailwind styling (borders, hover states)
   - Add click handlers for navigation to /{authorAddress}
   - Handle empty state ("No authors yet")

4. **Frontend - Routing**
   - Modify `App.tsx` to replace Navigate with AuthorLeaderboard at "/"
   - Import and register new component

5. **Testing**
   - Backend: Write pytest tests for repository aggregation query
   - Backend: Test API endpoint (200 OK, empty array, ordering)
   - Frontend: Manual testing per quickstart.md guide

**Estimated Total LOC**: ~200 lines
- Backend repository: ~40 lines
- Backend API route: ~50 lines
- Backend tests: ~60 lines
- Frontend component: ~50 lines

**Time Estimate**: 4-6 hours (implementation + testing)

---

## Success Metrics (Verification Plan)

After implementation, verify these success criteria from spec:

- ✅ **SC-001**: Page load < 3 seconds (measure in browser DevTools)
- ✅ **SC-002**: One-click navigation to profile (manual test)
- ✅ **SC-003**: 100% correct ordering (compare frontend to database query)
- ✅ **SC-004**: Graceful empty state (clear database, verify "No authors yet")
- ✅ **SC-005**: API response < 500ms (measure with curl + time)
- ✅ **SC-006**: Navigation baseline established (functional test)

**Acceptance Checklist**:
1. [ ] Backend tests pass (pytest)
2. [ ] API endpoint returns correct data (curl test)
3. [ ] Frontend displays leaderboard (manual browser test)
4. [ ] Clicking author navigates to profile (manual test)
5. [ ] Empty state shows correct message (manual test)
6. [ ] Loading state appears briefly (throttled network test)

---

## Next Command

Run `/speckit.tasks` to generate the implementation task breakdown (tasks.md).
