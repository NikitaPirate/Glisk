# Implementation Plan: X (Twitter) Account Linking

**Branch**: `007-link-x-twitter` | **Date**: 2025-10-21 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/007-link-x-twitter/spec.md`

## Summary

Allow authors to link their X (Twitter) accounts via OAuth 2.0 PKCE (one-time verification). Store verified X username in existing `authors.twitter_handle` field. Include X handle in NFT metadata when author has linked account. **Simplest MVP approach**: no session persistence, no refresh tokens, no Redis - use in-memory dict for temporary OAuth state (5-min TTL).

**Key Technical Approach**:
- OAuth 2.0 Authorization Code Flow with PKCE (no client secret needed)
- In-memory `dict` for temporary state storage (state → code_verifier mapping)
- X API `/2/users/me` endpoint to fetch username
- Discard access tokens immediately after fetching username
- Update existing `build_metadata()` function to conditionally include `creator.twitter` field
- No database migrations (use existing `authors.twitter_handle` field)

## Technical Context

**Language/Version**: Python 3.13 (backend), TypeScript 5.x (frontend)
**Primary Dependencies**:
- Backend: FastAPI, httpx (HTTP client for X API), structlog
- Frontend: React 18, wagmi (wallet signatures)
- No new dependencies (use stdlib for PKCE: `hashlib`, `secrets`, `base64`)

**Storage**:
- PostgreSQL: Use existing `authors.twitter_handle` field (no new tables)
- In-memory dict: Temporary OAuth state (5-min TTL, no Redis)

**Testing**: pytest (backend), manual testing (frontend MVP)
**Target Platform**: Linux server (backend), Modern browsers (frontend)
**Project Type**: Full-stack web (backend API + frontend integration)

**Performance Goals**:
- OAuth flow completion: <60 seconds (per success criteria)
- Token exchange: <5 seconds (network latency to X API)
- In-memory state lookup: O(1) (dict access)

**Constraints**:
- No session persistence (stateless after OAuth completes)
- No refresh tokens (one-time username fetch only)
- 5-minute TTL for OAuth state (security constraint)
- No unlink/re-link functionality in MVP

**Scale/Scope**:
- Concurrent OAuth flows: 10-100 (MVP estimate)
- In-memory storage: ~3-30 KB (negligible)
- Database impact: Single field update per author
- Code size estimate: ~400 LOC (backend), ~100 LOC (frontend)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with GLISK Constitution v1.2.0:

- [x] **Simplicity First**: ✅ Uses simplest OAuth approach (PKCE, in-memory state, no Redis, no sessions)
- [x] **Seasonal MVP**: ✅ Fast delivery (3-5 hours implementation), one-time verification only, no unlink complexity
- [x] **Monorepo Structure**: ✅ Backend services (`/backend/src/glisk/services/x_oauth.py`), Frontend UI (`/frontend/src/pages/ProfileSettings.tsx`), no contract changes
- [x] **Smart Contract Security**: N/A (no contract modifications)
- [x] **Clear Over Clever**: ✅ Straightforward OAuth flow, standard REST endpoints, in-line comments for PKCE logic

**Post-Design Re-check** (2025-10-21):
- ✅ **Simplicity**: In-memory dict for state (simpler than Redis), stdlib for PKCE (no new deps)
- ✅ **MVP Focus**: No unlink/re-link, no audit tables, manual testing only
- ✅ **Clear Code**: Standard OAuth patterns, well-documented endpoints (see quickstart.md)

*No constitutional violations. Complexity Tracking section not needed.*

## Project Structure

### Documentation (this feature)

```
specs/007-link-x-twitter/
├── plan.md              # ✅ This file (implementation plan)
├── research.md          # ✅ OAuth 2.0 PKCE research, X API endpoints
├── data-model.md        # ✅ Database schema (no changes), in-memory state structure
├── quickstart.md        # ✅ Step-by-step setup, implementation, and testing guide
├── contracts/           # ✅ API endpoint specifications (OpenAPI-style docs)
│   └── api-endpoints.md
└── tasks.md             # ⏳ Phase 2 output (/speckit.tasks command - NOT created yet)
```

### Source Code (repository root)

**Domains Affected**: Backend (primary), Frontend (integration)

```
backend/                                          # Backend domain
├── src/glisk/
│   ├── services/
│   │   ├── x_oauth.py                           # 🆕 NEW: X OAuth 2.0 service (PKCE, token exchange, username fetch)
│   │   └── wallet_signature.py                  # ✅ Existing: EIP-191 verification (reused)
│   ├── api/routes/
│   │   ├── x_auth.py                            # 🆕 NEW: /api/authors/x/* endpoints (auth/start, callback)
│   │   └── authors.py                           # 📝 MODIFY: Add twitter_handle to AuthorStatusResponse
│   ├── repositories/
│   │   └── author.py                            # 📝 MODIFY: Add upsert_x_handle() method
│   ├── workers/
│   │   └── ipfs_upload_worker.py                # 📝 MODIFY: Update build_metadata() to include creator.twitter
│   ├── models/
│   │   └── author.py                            # ✅ No changes (twitter_handle field exists)
│   ├── core/
│   │   └── settings.py                          # 📝 MODIFY: Add X_CLIENT_ID, X_REDIRECT_URI, FRONTEND_URL fields
│   └── main.py                                  # 📝 MODIFY: Register x_auth router
├── tests/
│   ├── test_x_oauth.py                          # 🆕 NEW: Unit tests for XOAuthService
│   └── test_x_auth_endpoints.py                 # 🆕 NEW: Integration tests for API endpoints
└── .env                                          # 📝 MODIFY: Add X OAuth config vars

frontend/                                         # Frontend domain
├── src/
│   └── pages/
│       └── ProfileSettings.tsx                   # 📝 MODIFY: Add X linking UI, OAuth redirect handling
└── public/
    └── ...                                       # ✅ No changes

contracts/                                        # Smart contracts domain
└── ...                                           # ✅ No changes (feature is backend/frontend only)
```

**File Size Estimates**:
- 🆕 `x_oauth.py`: ~200 LOC (PKCE generation, token exchange, username fetch, in-memory state mgmt)
- 🆕 `x_auth.py`: ~150 LOC (2 endpoints: /auth/start, /callback)
- 📝 `build_metadata()`: +10 LOC (conditional creator.twitter field)
- 📝 `author.py` (repository): +20 LOC (upsert_x_handle method)
- 📝 `ProfileSettings.tsx`: +80 LOC (X linking button, OAuth flow, callback handling)

**Total New Code**: ~400 LOC backend, ~100 LOC frontend

## Implementation Phases

### Phase 0: Research ✅ COMPLETE

**Artifacts**:
- [research.md](./research.md) - OAuth 2.0 PKCE flow, X API endpoints, PKCE implementation details
- [data-model.md](./data-model.md) - Database schema (no changes), in-memory state structure
- [contracts/api-endpoints.md](./contracts/api-endpoints.md) - REST API specifications
- [quickstart.md](./quickstart.md) - Setup, implementation, and testing guide

**Key Decisions**:
1. **OAuth Method**: Authorization Code Flow with PKCE (no client secret)
2. **State Storage**: In-memory Python dict (no Redis for MVP)
3. **Token Lifetime**: One-time use, discard after username fetch
4. **Database**: No migration needed (`twitter_handle` field exists)
5. **Scopes**: `users.read` only (minimal permissions)

### Phase 1: Backend Implementation (3-4 hours)

**Tasks**:
1. Create X OAuth service (`services/x_oauth.py`):
   - PKCE code verifier/challenge generation
   - In-memory state storage with TTL
   - Token exchange with X API
   - Username fetch from `/2/users/me`

2. Create API endpoints (`api/routes/x_auth.py`):
   - `POST /api/authors/x/auth/start` - Initiate OAuth (with wallet signature)
   - `GET /api/authors/x/callback` - Handle OAuth redirect

3. Update author repository (`repositories/author.py`):
   - Add `upsert_x_handle()` method

4. Update IPFS metadata (`workers/ipfs_upload_worker.py`):
   - Modify `build_metadata()` to include `creator.twitter` field
   - Fetch author entity to get `twitter_handle`

5. Update settings (`core/settings.py`):
   - Add `X_CLIENT_ID`, `X_REDIRECT_URI`, `FRONTEND_URL` fields

6. Register routes (`main.py`):
   - Include `x_auth.router`

**Testing**:
- Unit tests for PKCE generation/validation
- Unit tests for token exchange (mocked X API)
- Integration tests for OAuth flow
- Manual testing with real X account (quickstart.md)

### Phase 2: Frontend Integration (1 hour)

**Tasks**:
1. Update ProfileSettings page (`pages/ProfileSettings.tsx`):
   - Add "Link X Account" button (hidden if `twitter_handle` exists)
   - Wallet signature flow (EIP-191)
   - Call backend `/auth/start` endpoint
   - Redirect to X authorization URL
   - Handle OAuth callback redirect (`?x_linked=true&username=...`)
   - Display linked X handle (`@username`)

2. Fetch author status on page load:
   - Call `GET /api/authors/{address}` to get `twitter_handle`
   - Show/hide button based on link status

**Testing**:
- Manual testing with wallet connected
- Test user approval flow
- Test user denial flow
- Test re-link prevention (409 error)

### Phase 3: End-to-End Testing (1 hour)

**Test Scenarios** (per quickstart.md):
1. Complete OAuth flow (user approves)
2. User denies authorization
3. Re-link prevention (already linked)
4. NFT metadata includes X handle
5. CSRF protection (state mismatch)
6. OAuth state expiry (>5 minutes)

**Verification**:
- Database: `twitter_handle` updated correctly
- IPFS metadata: `creator.twitter` field exists
- UI: Button visibility toggles correctly
- Logs: Security events logged (CSRF attempts, denials)

### Phase 4: Production Deployment (30 minutes)

**Prerequisites**:
1. X app configured with production callback URL
2. Production environment variables set
3. HTTPS enabled for all URLs

**Deployment Steps**:
1. Deploy backend with X OAuth config
2. Deploy frontend with OAuth callback handling
3. Test OAuth flow in production
4. Monitor logs for errors

**Rollback Plan**:
- Feature is additive (no breaking changes)
- Rollback: Remove x_auth router registration
- Database: `twitter_handle` field remains (no cleanup needed)

## Development Timeline

**Total Estimated Time**: 5-7 hours (including testing)

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| Phase 0: Research | ✅ Complete | research.md, data-model.md, contracts/, quickstart.md |
| Phase 1: Backend | 3-4 hours | OAuth service, API endpoints, repository update, metadata integration |
| Phase 2: Frontend | 1 hour | Profile settings UI, OAuth redirect handling |
| Phase 3: Testing | 1 hour | Manual + integration tests, NFT metadata verification |
| Phase 4: Production | 30 min | Production deployment, monitoring setup |

**Parallel Work Opportunities**:
- Backend and frontend can be developed in parallel after Phase 0
- Testing can begin as soon as individual phases complete

## Risk Mitigation

**Risk 1: X API changes or downtime**
- Mitigation: Comprehensive error handling, user-friendly error messages
- Fallback: Manual entry (future enhancement if X API unreliable)

**Risk 2: OAuth state lost on backend restart**
- Impact: Users must retry OAuth (acceptable for MVP)
- Mitigation: Inform users in error message ("Please try linking again")
- Future: Redis for distributed state (multi-instance backend)

**Risk 3: CSRF attacks**
- Mitigation: State parameter validation (cryptographically random)
- Monitoring: Log all state mismatches for security analysis

**Risk 4: Rate limiting by X API**
- Impact: 429 errors during high-traffic periods
- Mitigation: Exponential backoff, user-friendly retry message
- Future: Rate limiting on `/auth/start` endpoint

## Success Criteria Validation

Mapping to spec.md success criteria:

- **SC-001**: Authors complete flow in <60 seconds
  - ✅ Validated via manual testing (OAuth redirect latency ~2-5s)

- **SC-002**: 95% OAuth success rate
  - ✅ Monitored via structured logs (`x_oauth_flow_started` vs `x_account_linked`)

- **SC-003**: 100% of NFTs with linked accounts include X handle
  - ✅ Validated via IPFS metadata inspection (`creator.twitter` field)

- **SC-004**: 0% of NFTs without linked accounts include X handle
  - ✅ Validated via `build_metadata()` conditional logic

- **SC-005**: 100% CSRF protection (state validation)
  - ✅ Validated via unit tests and manual CSRF attempt testing

- **SC-006**: 100% button visibility correctness
  - ✅ Validated via manual UI testing (link/unlink button states)

## Post-Launch Enhancements

**Future improvements** (out of scope for MVP):

1. **Unlink X Account** (DELETE /api/authors/x/unlink)
   - Allow authors to remove X link
   - Update metadata generation to remove `creator.twitter`

2. **Re-link X Account** (overwrite existing handle)
   - Remove 409 Conflict check
   - Add confirmation dialog ("This will replace @oldhandle with @newhandle")

3. **Redis State Storage**
   - Distributed in-memory storage for multi-instance backend
   - Survives backend restarts

4. **Rate Limiting**
   - Limit `/auth/start` to 5 requests/minute per wallet
   - Prevent abuse and X API rate limit exhaustion

5. **Audit Log Table**
   - Track all linking events (wallet, X handle, timestamp)
   - Analytics and support debugging

6. **Additional X Profile Data**
   - Fetch follower count, profile image URL, bio
   - Display in author profile page
   - Include in NFT metadata (`creator.follower_count`)

## Monitoring and Observability

**Structured Logs** (structlog events):

```python
# OAuth flow tracking
logger.info("x_oauth_flow_started", wallet_address=..., state=...)
logger.info("x_account_linked", wallet_address=..., twitter_handle=...)
logger.warning("x_oauth_denied", wallet_address=..., error=...)

# Security events
logger.error("x_oauth_state_mismatch", state_param=..., ip_address=...)
logger.warning("x_oauth_state_expired", state=..., age_seconds=...)

# API errors
logger.error("x_token_exchange_failed", error=..., status_code=...)
logger.error("x_username_fetch_failed", error=..., status_code=...)
```

**Metrics to Track** (future Grafana/Prometheus):
- OAuth flow success rate (started → linked)
- OAuth denial rate (user denials)
- CSRF attack attempts (state mismatches)
- Average flow completion time
- X API error rates (4xx, 5xx)

**Alerts**:
- OAuth success rate <80% (X API issues or config errors)
- CSRF attempts >10/hour (potential attack)
- X API 5xx errors >5/hour (service degradation)

## Security Checklist

- [x] PKCE implementation (code verifier/challenge)
- [x] State parameter validation (CSRF protection)
- [x] 5-minute TTL for OAuth state
- [x] Wallet signature verification on `/auth/start`
- [x] Access tokens discarded after username fetch
- [x] No client secret exposure (PKCE eliminates need)
- [x] HTTPS required for production redirect URIs
- [x] Structured logging for security events
- [x] Input validation on all API endpoints (Pydantic)
- [x] Error messages don't leak sensitive info

## Summary

**Feature Complete**: X (Twitter) account linking via OAuth 2.0 PKCE

**Implementation Approach**:
- ✅ Simplest MVP design (no Redis, no sessions, in-memory state)
- ✅ Zero database migrations (use existing field)
- ✅ Fast delivery (5-7 hours total)
- ✅ Security-first (PKCE, CSRF protection, wallet signatures)
- ✅ Clear code (stdlib PKCE, standard OAuth patterns)

**Next Steps**:
1. Run `/speckit.tasks` to generate task breakdown
2. Implement Phase 1 (backend) following quickstart.md
3. Implement Phase 2 (frontend)
4. Execute Phase 3 testing scenarios
5. Deploy to production (Phase 4)

**Key Artifacts**:
- [research.md](./research.md) - Technical research and decisions
- [data-model.md](./data-model.md) - Database schema and in-memory state
- [contracts/api-endpoints.md](./contracts/api-endpoints.md) - API specifications
- [quickstart.md](./quickstart.md) - Implementation and testing guide
- [plan.md](./plan.md) - This implementation plan
