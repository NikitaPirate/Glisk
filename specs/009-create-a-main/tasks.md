# Tasks: Author Leaderboard Landing Page

**Feature**: 009-create-a-main
**Input**: Design documents from `/specs/009-create-a-main/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: Backend tests included (pytest). Frontend testing is manual per GLISK Constitution v1.2.0.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization - no new dependencies or infrastructure needed, using existing FastAPI + React stack

**Status**: All setup already exists from previous features
- ✅ Backend: FastAPI, SQLModel, pytest configured
- ✅ Frontend: React 18, TypeScript, Vite, react-router-dom, Tailwind CSS
- ✅ Database: PostgreSQL with authors and tokens_s0 tables

**Tasks**: None - proceed directly to Foundational phase

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Verify database schema and indexes needed for aggregation query

**⚠️ CRITICAL**: Must verify schema before implementing user stories

- [ ] T001 [P] Verify database schema has tokens_s0.author_id foreign key to authors.id (use `\d tokens_s0` in psql)
- [ ] T002 [P] Verify tokens_s0.author_id has index (PostgreSQL FK auto-indexes, confirm with `\di` in psql)
- [ ] T003 [P] Verify authors.wallet_address has unique index (confirm with `\d authors` in psql)

**Checkpoint**: Database schema verified - user story implementation can begin

---

## Phase 3: User Story 1 - Discover Top Authors (Priority: P1) 🎯 MVP

**Goal**: Display ranked list of authors by token count on landing page, clickable to navigate to author profiles

**Independent Test**: Load landing page at `/`, verify authors appear in descending order by token count, click any author to navigate to their profile page

### Tests for User Story 1

**NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T004 [P] [US1] Create backend/tests/test_author_leaderboard.py with test fixtures for seeding authors and tokens
- [ ] T005 [US1] Add test_get_leaderboard_basic() to verify basic aggregation query returns correct order (3 authors with 5, 3, 1 tokens)
- [ ] T006 [US1] Add test_get_leaderboard_tie_breaking() to verify alphabetical secondary sort when token counts are equal
- [ ] T007 [US1] Add test_get_leaderboard_limit() to verify only top 50 authors returned (seed 60 authors)
- [ ] T008 [US1] Add test_api_leaderboard_endpoint() to verify GET /api/authors/leaderboard returns 200 OK with correct JSON schema
- [ ] T009 [US1] Run tests to confirm they FAIL (pytest backend/tests/test_author_leaderboard.py -v)

### Implementation for User Story 1

**Backend - Repository Layer**:

- [ ] T010 [US1] Add get_author_leaderboard() method to backend/src/glisk/repositories/author.py
  - Use SQLModel select() with join(Author, Token.author_id == Author.id)
  - Aggregate with func.count(Token.id).label("total_tokens")
  - Group by Author.id, Author.wallet_address
  - Order by total_tokens DESC, Author.wallet_address ASC
  - Limit 50
  - Return list of tuples (wallet_address: str, total_tokens: int)

**Backend - API Layer**:

- [ ] T011 [US1] Create AuthorLeaderboardEntry Pydantic model in backend/src/glisk/api/routes/authors.py
  - Fields: author_address (str, 42 chars), total_tokens (int, ≥1)
  - Add field validation and example values
- [ ] T012 [US1] Add GET /leaderboard endpoint to backend/src/glisk/api/routes/authors.py
  - Mount at router path: @router.get("/leaderboard", response_model=list[AuthorLeaderboardEntry])
  - Call repository.get_author_leaderboard()
  - Map tuples to AuthorLeaderboardEntry DTOs
  - Add try/except for database errors (return 500 with detail message)
  - Add structured logging for endpoint calls

**Backend - Verification**:

- [ ] T013 [US1] Run backend tests to verify all pass (pytest backend/tests/test_author_leaderboard.py -v)
- [ ] T014 [US1] Manual API test: Start backend, curl http://localhost:8000/api/authors/leaderboard, verify response format

**Frontend - Component**:

- [ ] T015 [US1] Create frontend/src/pages/AuthorLeaderboard.tsx component
  - Import useState, useEffect, useNavigate from react/react-router-dom
  - Define AuthorLeaderboardEntry interface (author_address: string, total_tokens: number)
  - Add state: authors (array), isLoading (boolean)
  - Implement useEffect to fetch from /api/authors/leaderboard on mount
  - Render loading state: "Loading..." text when isLoading is true
  - Render list: map authors array to div elements with Tailwind styling
  - Display format: "{author_address} - {total_tokens} tokens"
  - Add click handler: onClick={() => navigate(`/${author.author_address}`)}
  - Add basic Tailwind styling: borders, padding, hover states (bg-gray-100 on hover)

**Frontend - Routing**:

- [ ] T016 [US1] Modify frontend/src/App.tsx to change root route from Navigate to AuthorLeaderboard
  - Import AuthorLeaderboard component
  - Replace current <Route path="/" element={<Navigate to="/profile" replace />} /> with <Route path="/" element={<AuthorLeaderboard />} />
  - Keep existing profile routes unchanged

**Frontend - Verification**:

- [ ] T017 [US1] Manual frontend test: npm run dev, open http://localhost:5173/, verify leaderboard displays
- [ ] T018 [US1] Manual navigation test: Click author entry, verify navigation to /{authorAddress} profile page
- [ ] T019 [US1] Manual performance test: Use browser DevTools Network tab to verify page load < 3s and API response < 500ms

**Checkpoint**: At this point, User Story 1 should be fully functional - visitors can see ranked authors and navigate to profiles

---

## Phase 4: User Story 2 - Empty State Experience (Priority: P2)

**Goal**: Display clear "No authors yet" message when database has no data, preventing user confusion

**Independent Test**: Clear database (TRUNCATE tables), load landing page, verify "No authors yet" message appears instead of empty list

### Tests for User Story 2

- [ ] T020 [US1] Add test_get_leaderboard_empty() to backend/tests/test_author_leaderboard.py
  - Clear all tokens and authors from database
  - Call repository.get_author_leaderboard()
  - Verify returns empty list []
- [ ] T021 [US1] Add test_api_leaderboard_empty() to backend/tests/test_author_leaderboard.py
  - Clear database
  - Call GET /api/authors/leaderboard
  - Verify returns 200 OK with empty array []
- [ ] T022 [US1] Run tests to confirm they FAIL before implementation

### Implementation for User Story 2

**Frontend - Empty State**:

- [ ] T023 [US2] Update frontend/src/pages/AuthorLeaderboard.tsx to handle empty state
  - After fetch completes, check if authors.length === 0
  - If empty, render "No authors yet" message instead of empty list
  - Style with Tailwind text-gray-500 for subtle appearance

**Frontend - Verification**:

- [ ] T024 [US2] Manual empty state test: Clear database, reload page, verify "No authors yet" appears
- [ ] T025 [US2] Manual recovery test: Seed database, reload page, verify leaderboard returns (no broken state)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work - normal display and graceful empty state

---

## Phase 5: User Story 3 - Loading State Feedback (Priority: P3)

**Goal**: Show "Loading..." text while data is being fetched, improving user confidence during network requests

**Independent Test**: Throttle network to "Slow 3G" in browser DevTools, reload page, verify "Loading..." text appears before data loads

### Implementation for User Story 3

**Frontend - Loading State** (already implemented in T015, verify it works):

- [ ] T026 [US3] Verify loading state implementation in frontend/src/pages/AuthorLeaderboard.tsx
  - Confirm isLoading state is initialized to true
  - Confirm "Loading..." text renders when isLoading is true
  - Confirm isLoading is set to false after fetch completes

**Frontend - Verification**:

- [ ] T027 [US3] Manual loading test: Throttle network to "Slow 3G", reload page, verify "Loading..." appears briefly
- [ ] T028 [US3] Manual error test: Stop backend server, reload frontend, verify "Loading..." persists (acceptable MVP behavior per spec edge case)

**Checkpoint**: All three user stories complete - ranking display, empty state, and loading feedback all work independently

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final verification, documentation, and cleanup

- [ ] T029 [P] Run full backend test suite to verify no regressions (pytest backend/tests/ -v)
- [ ] T030 [P] Follow quickstart.md guide end-to-end to verify all manual test scenarios pass
- [ ] T031 Update CLAUDE.md with new leaderboard feature documentation
  - Add section under "Backend Features" or "Frontend Features"
  - Document GET /api/authors/leaderboard endpoint
  - Document landing page route (/)
  - Include usage examples and test commands
- [ ] T032 Code review: Verify all code follows GLISK Constitution (Simplicity First, no unnecessary abstractions)
- [ ] T033 Verify all success criteria met (SC-001 through SC-006 from spec.md)
- [ ] T034 Final integration test: Seed realistic data (50 authors), verify leaderboard loads and performs correctly

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: ✅ Already complete - no tasks
- **Foundational (Phase 2)**: Verify database schema (T001-T003) - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - User Story 1 (P1): MVP - implements core functionality
  - User Story 2 (P2): Builds on US1 - adds empty state to existing component
  - User Story 3 (P3): Verifies US1 - loading state already implemented, just verify it works
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (T001-T003) - No dependencies on other stories
- **User Story 2 (P2)**: Depends on US1 frontend component existing (T015) - Modifies same component to add empty state
- **User Story 3 (P3)**: Depends on US1 frontend component existing (T015) - Verifies loading state already implemented

### Within Each User Story

**User Story 1 flow**:
1. Write tests first (T004-T008) → Run to verify they FAIL (T009)
2. Backend repository (T010) and API (T011-T012) in sequence (repository must exist before API)
3. Backend verification (T013-T014)
4. Frontend component (T015) and routing (T016) in sequence (component before routing)
5. Frontend verification (T017-T019)

**User Story 2 flow**:
1. Write tests first (T020-T021) → Run to verify they FAIL (T022)
2. Update frontend component (T023) - modifies T015 output
3. Verify (T024-T025)

**User Story 3 flow**:
1. Verify existing implementation (T026) - no new code needed
2. Manual tests (T027-T028)

### Parallel Opportunities

**Phase 2 (Foundational)**: All 3 schema verification tasks (T001, T002, T003) marked [P] can run in parallel

**Phase 3 (User Story 1)**:
- Tests (T004) can start immediately (independent file)
- Test cases (T005-T008) must run after T004 (same file)
- Backend models (T010, T011) can be written in parallel (independent logic)
- Frontend component (T015) can be written in parallel with backend work (different domain)

**Phase 6 (Polish)**: T029, T030 marked [P] can run in parallel

---

## Parallel Example: User Story 1

```bash
# Phase 2: Verify schema in parallel
Task: "Verify tokens_s0.author_id foreign key (psql \\d tokens_s0)"
Task: "Verify author_id index (psql \\di)"
Task: "Verify wallet_address unique index (psql \\d authors)"

# Phase 3: Launch backend and frontend work in parallel
Task: "Create test_author_leaderboard.py with fixtures"
Task: "Add get_author_leaderboard() to AuthorRepository"
Task: "Create AuthorLeaderboard.tsx component"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 2: Foundational (T001-T003) - 5 minutes
2. Complete Phase 3: User Story 1 (T004-T019) - 3-4 hours
3. **STOP and VALIDATE**: Test User Story 1 independently per quickstart.md
4. Deploy/demo landing page showing top authors
5. **Deliverable**: Working landing page at `/` with clickable author leaderboard

### Incremental Delivery

1. Foundation (Phase 2) → Schema verified
2. User Story 1 (Phase 3) → Test independently → **Deploy MVP!**
3. User Story 2 (Phase 4) → Test empty state → Deploy enhanced version
4. User Story 3 (Phase 5) → Verify loading state → Deploy final version
5. Polish (Phase 6) → Code review and documentation → Ready for production

### Sequential Strategy (Solo Developer)

1. T001-T003: Verify schema (5 min)
2. T004-T009: Write and verify tests fail (30 min)
3. T010-T012: Implement backend (1 hour)
4. T013-T014: Verify backend works (15 min)
5. T015-T016: Implement frontend (1 hour)
6. T017-T019: Verify frontend works (15 min)
7. **Checkpoint**: MVP complete, landing page works
8. T020-T025: Add empty state handling (30 min)
9. T026-T028: Verify loading state (15 min)
10. T029-T034: Polish and document (1 hour)

**Total Estimated Time**: 4-6 hours

---

## Notes

- [P] tasks = different files/domains, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently testable
- Tests written first (TDD approach) to define expected behavior
- Backend tests are automated (pytest), frontend tests are manual (per constitution)
- Stop at User Story 1 completion for fastest MVP delivery
- Database schema requires no changes (uses existing tables)
- Total new code: ~200 LOC (repository: 40, API: 50, tests: 60, frontend: 50)
- No new dependencies required
- Feature aligns with Simplicity First principle (no abstractions, direct SQL aggregation)
