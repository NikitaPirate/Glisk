# Tasks: X (Twitter) Account Linking

**Input**: Design documents from `/specs/007-link-x-twitter/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api-endpoints.md, quickstart.md

**Tests**: Not explicitly requested in spec - implementation tasks only

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

## Path Conventions
- Backend: `backend/src/glisk/`, `backend/tests/`
- Frontend: `frontend/src/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: X Developer Portal setup and environment configuration

- [ ] T001 Create X application in X Developer Portal (https://developer.x.com/)
  - Configure OAuth 2.0 with authorization code flow + PKCE
  - Set app type to "Web App", permissions to "Read"
  - Add callback URI: `http://localhost:8000/api/authors/x/callback` (dev)
  - Copy Client ID (no client secret needed for PKCE)

- [ ] T002 Configure backend environment variables in `backend/.env`
  - Add `X_CLIENT_ID=<client_id_from_x_portal>`
  - Add `X_REDIRECT_URI=http://localhost:8000/api/authors/x/callback`
  - Add `FRONTEND_URL=http://localhost:5173`

- [ ] T003 Verify database schema has `twitter_handle` field
  - Check `authors` table for `twitter_handle` column (should already exist)
  - No migration needed per data-model.md

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core OAuth service and shared utilities that MUST be complete before user stories

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Create X OAuth service in `backend/src/glisk/services/x_oauth.py`
  - Implement `XOAuthService` class with `__init__(client_id, redirect_uri)`
  - Implement `generate_pkce_pair()` method (code_verifier + code_challenge using SHA256)
  - Implement `generate_state()` method (random 32+ char string for CSRF)
  - Implement `build_authorization_url(wallet_address)` method
  - Create `OAuthState` dataclass (state, code_verifier, wallet_address, created_at, expires_at)
  - Create module-level `oauth_state_storage: dict[str, OAuthState]` for in-memory state
  - Store OAuth state with 5-minute TTL in authorization URL builder
  - Implement `exchange_code_for_token(code, code_verifier)` async method
  - Implement `fetch_username(access_token)` async method
  - Implement `cleanup_expired_oauth_states()` utility function
  - Add structured logging for OAuth flow events

- [ ] T005 [P] Update settings in `backend/src/glisk/core/settings.py`
  - Add `X_CLIENT_ID: str` field
  - Add `X_REDIRECT_URI: str` field
  - Add `FRONTEND_URL: str` field (default: "http://localhost:5173")

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - One-Time X Account Verification (Priority: P1) 🎯 MVP

**Goal**: Authors can link their X (Twitter) account via OAuth 2.0 flow, store verified X handle in author profile, and see X handle displayed in profile settings

**Independent Test**: Navigate to profile settings, click "Link X Account", complete OAuth flow on X, verify X handle appears in database (`authors.twitter_handle`) and UI button hides after linking

### Implementation for User Story 1

- [ ] T006 Create X OAuth API endpoints in `backend/src/glisk/api/routes/x_auth.py`
  - Create `XAuthStartRequest` Pydantic model (wallet_address, message, signature)
  - Create `XAuthStartResponse` Pydantic model (authorization_url)
  - Implement `POST /api/authors/x/auth/start` endpoint
    - Verify wallet signature using `verify_wallet_signature()` from `glisk.services.wallet_signature`
    - Check if author exists and `twitter_handle` is NULL (return 409 Conflict if already linked)
    - Call `XOAuthService.build_authorization_url(wallet_address)`
    - Return `XAuthStartResponse` with authorization URL
  - Implement `GET /api/authors/x/callback` endpoint
    - Handle OAuth error parameter (user denial) → redirect to error page
    - Validate state parameter against `oauth_state_storage` (CSRF protection)
    - Check OAuth state TTL (<5 minutes)
    - Call `XOAuthService.exchange_code_for_token(code, code_verifier)`
    - Call `XOAuthService.fetch_username(access_token)`
    - Call `AuthorRepository.upsert_x_handle(wallet_address, username)`
    - Delete OAuth state from in-memory storage (cleanup)
    - Discard access token (do not store)
    - Redirect to frontend success page with username query param
  - Add structured logging for OAuth events, security events, and errors

- [ ] T007 Update author repository in `backend/src/glisk/repositories/author.py`
  - Add `upsert_x_handle(wallet_address: str, twitter_handle: str)` async method
  - Fetch existing author by wallet address
  - If author exists: update `twitter_handle` field
  - If author doesn't exist: create new author with `twitter_handle` and empty `prompt_text`
  - Flush and refresh session, return updated Author entity

- [ ] T008 Extend author status endpoint in `backend/src/glisk/api/routes/authors.py`
  - Update `AuthorStatusResponse` model to include `twitter_handle: Optional[str]` field
  - Modify `GET /api/authors/{wallet_address}` response to include `twitter_handle` value

- [ ] T009 Register X OAuth router in `backend/src/glisk/main.py`
  - Import `x_auth` router from `glisk.api.routes`
  - Add `app.include_router(x_auth.router)` to register endpoints

- [ ] T010 Create profile settings page in `frontend/src/pages/ProfileSettings.tsx`
  - Add state for `twitterHandle: string | null` and `loading: boolean`
  - On mount: fetch author status from `GET /api/authors/{address}` and set `twitterHandle` state
  - Check URL query params for OAuth callback (`?x_linked=true&username=...`)
  - If `x_linked=true`: update `twitterHandle` state, show success message, clear query params
  - If `x_linked=false`: show error message with error type from query param
  - Implement `linkXAccount()` async function:
    - Sign message with wallet: `"Link X account for wallet: {address}"`
    - Call `POST /api/authors/x/auth/start` with wallet_address, message, signature
    - Handle errors (show alert)
    - Redirect to `authorization_url` using `window.location.href`
  - Render UI:
    - If `twitterHandle` exists: show "Linked: @{twitterHandle}" (no button)
    - If `twitterHandle` is null: show "Link X Account" button (calls `linkXAccount()`)
    - Disable button while `loading` is true

**Checkpoint**: At this point, User Story 1 should be fully functional - authors can link X accounts and see handle in profile settings

---

## Phase 4: User Story 2 - X Handle in NFT Metadata (Priority: P1)

**Goal**: NFT metadata on IPFS includes author's X handle in `creator.twitter` field when author has linked X account

**Independent Test**: Mint NFT for author with linked X account, fetch metadata from IPFS using metadata CID, verify `creator.twitter` field exists with correct username

### Implementation for User Story 2

- [ ] T011 Update IPFS metadata builder in `backend/src/glisk/workers/ipfs_upload_worker.py`
  - Modify `build_metadata(token, image_cid)` function signature to add `twitter_handle: Optional[str] = None` parameter
  - Add conditional logic: if `twitter_handle` is not None, add `"creator": {"twitter": twitter_handle}` to metadata dict
  - If `twitter_handle` is None, omit `creator` field entirely
  - Ensure metadata structure remains ERC721-compliant

- [ ] T012 Update IPFS upload worker to fetch author in `backend/src/glisk/workers/ipfs_upload_worker.py`
  - In `process_single_token()` function, add query to fetch Author entity by `token.author_wallet`
  - Import `Author` model and `select` from SQLModel
  - Execute query: `author = await session.scalar(select(Author).where(Author.wallet_address == token.author_wallet))`
  - Pass `twitter_handle=author.twitter_handle if author else None` to `build_metadata()` call
  - Handle case where author might not exist (pass None)

**Checkpoint**: All user stories should now be independently functional - X linking works AND metadata includes X handles

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T013 [P] Add comprehensive error handling for X API failures
  - Add try-except blocks around `httpx` calls in `XOAuthService`
  - Handle network timeouts (30s timeout configured)
  - Handle X API 4xx errors (invalid credentials, rate limits)
  - Handle X API 5xx errors (service degradation)
  - Add structured logging for all error types
  - Return user-friendly error messages in API responses

- [ ] T014 [P] Add structured logging for monitoring and observability
  - Log `x_oauth_flow_started` event with wallet_address and state (redacted)
  - Log `x_account_linked` event with wallet_address and twitter_handle
  - Log `x_oauth_denied` event with wallet_address and error
  - Log `x_oauth_state_mismatch` event with state_param and ip_address (security)
  - Log `x_oauth_state_expired` event with state and age_seconds
  - Log `x_token_exchange_failed` event with error and status_code
  - Log `x_username_fetch_failed` event with error and status_code

- [ ] T015 Manual testing per quickstart.md validation scenarios
  - Test 1: Complete OAuth flow (user approves)
  - Test 2: User denies authorization
  - Test 3: Re-link prevention (409 error when already linked)
  - Test 4: NFT metadata includes X handle
  - Test 5: CSRF protection (state mismatch)
  - Test 6: OAuth state expiry (>5 minutes)
  - Verify database updates correctly
  - Verify UI button visibility toggles correctly
  - Verify structured logs contain expected events

- [ ] T016 [P] Documentation and cleanup
  - Review quickstart.md for accuracy
  - Update CLAUDE.md with X linking section (usage, configuration, testing)
  - Add inline code comments for PKCE logic in `XOAuthService`
  - Add docstrings for all new public methods
  - Clean up unused imports

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational (Phase 2) - OAuth endpoints for linking X accounts
- **User Story 2 (Phase 4)**: Depends on User Story 1 completion (needs `twitter_handle` field populated) - metadata generation
- **Polish (Phase 5)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P1)**: Depends on User Story 1 (needs `twitter_handle` data to include in metadata)

### Within Each User Story

- **User Story 1**: T006 (endpoints) requires T004 (OAuth service); T009 (register router) requires T006 complete; T010 (frontend) can start in parallel with backend tasks
- **User Story 2**: T012 (fetch author) requires T011 (update metadata builder) to pass twitter_handle parameter

### Parallel Opportunities

- Phase 1: T001, T002, T003 can run sequentially (T001 generates credentials for T002)
- Phase 2: T004 and T005 can run in parallel (different files)
- Phase 3: T010 (frontend) can start in parallel with T006-T009 (backend) if using mocks/stubs
- Phase 5: T013, T014, T016 can run in parallel (different files/concerns)

---

## Parallel Example: Foundational Phase

```bash
# Launch foundational tasks together:
Task: "Create X OAuth service in backend/src/glisk/services/x_oauth.py"
Task: "Update settings in backend/src/glisk/core/settings.py"
```

---

## Parallel Example: User Story 1 Backend

```bash
# After T006 completes, these can run in parallel:
Task: "Update author repository in backend/src/glisk/repositories/author.py"
Task: "Extend author status endpoint in backend/src/glisk/api/routes/authors.py"
```

---

## Implementation Strategy

### MVP First (Both User Stories Required)

1. Complete Phase 1: Setup (X Developer Portal + environment)
2. Complete Phase 2: Foundational (OAuth service + settings) - BLOCKS all stories
3. Complete Phase 3: User Story 1 (OAuth endpoints + frontend linking UI)
4. **VALIDATE**: Test X account linking independently
5. Complete Phase 4: User Story 2 (metadata generation with X handle)
6. **VALIDATE**: Test NFT metadata includes X handle
7. Complete Phase 5: Polish (error handling, logging, testing)
8. Deploy/demo full feature

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Authors can link X accounts ✅
3. Add User Story 2 → Test independently → NFT metadata includes X handles ✅
4. Polish → Error handling, logging, comprehensive testing ✅

### Parallel Team Strategy

With 2 developers after Foundational phase completes:
- **Developer A**: User Story 1 (OAuth endpoints + frontend)
- **Developer B**: User Story 2 (metadata generation) - starts after US1 backend tasks complete

Note: User Story 2 has dependency on User Story 1 data (`twitter_handle` field), so true parallelism is limited to frontend/backend split within US1.

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- User Story 1 and 2 are both P1 priority (required for MVP)
- No database migration needed (`twitter_handle` field already exists)
- No Redis dependency (in-memory `dict` for OAuth state)
- OAuth state stored temporarily (5-min TTL), auto-cleanup on access
- Access tokens discarded immediately after username fetch (one-time verification only)
- No unlink/re-link functionality in MVP (permanent linking)
- No test tasks included (not explicitly requested in spec)
- Commit after each task or logical group
- Stop at checkpoints to validate stories independently
- Follow quickstart.md for detailed implementation guidance and manual testing

---

## Summary

**Total Tasks**: 16 tasks
- Phase 1 (Setup): 3 tasks
- Phase 2 (Foundational): 2 tasks
- Phase 3 (User Story 1): 5 tasks
- Phase 4 (User Story 2): 2 tasks
- Phase 5 (Polish): 4 tasks

**Parallel Opportunities**:
- Foundational phase: 2 tasks can run in parallel (T004, T005)
- User Story 1: Frontend (T010) can partially overlap with backend (T006-T009)
- Polish phase: 3 tasks can run in parallel (T013, T014, T016)

**MVP Scope**: Both User Stories required (P1 priority)
- User Story 1: X account linking via OAuth
- User Story 2: X handle in NFT metadata

**Estimated Implementation Time**: 5-7 hours (per plan.md)
- Setup: 30 min
- Foundational: 1 hour
- User Story 1: 2-3 hours
- User Story 2: 30 min
- Polish: 1-2 hours
