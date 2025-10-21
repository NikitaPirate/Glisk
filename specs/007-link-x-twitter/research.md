# Research: X (Twitter) Account Linking

**Feature**: 007-link-x-twitter
**Date**: 2025-10-21
**Research Focus**: Simplest OAuth 2.0 implementation for one-time X account verification

## Overview

This document captures research findings for implementing X (Twitter) account linking with the **simplest possible approach** for MVP. Key constraint: one-time verification only (no session persistence, no refresh tokens, no Redis).

## Technology Decisions

### OAuth 2.0 Authorization Code Flow with PKCE

**Decision**: Use OAuth 2.0 Authorization Code Flow with PKCE (Proof Key for Code Exchange)

**Rationale**:
- **Industry standard** for web applications
- **PKCE eliminates need for client secret** (secure for browser-based flows)
- **Simplest flow** for one-time verification (get username, discard tokens immediately)
- **No session storage required** (stateless - only state parameter for CSRF protection)
- **Supported by X API v2** (only OAuth method for `/2/users/me` endpoint)

**Alternatives Considered**:
1. **OAuth 1.0a**: More complex (signature generation, nonce management), requires server-side secrets
2. **Manual handle entry**: Violates requirement for ownership verification
3. **Third-party auth libraries (NextAuth, Passport)**: Overkill for MVP, adds dependencies, assumes session persistence

### X API Endpoints

**Authorization Endpoint**:
```
https://x.com/i/oauth2/authorize
```

**Parameters**:
- `response_type`: `code` (authorization code grant)
- `client_id`: From X Developer Portal (Keys and Tokens section)
- `redirect_uri`: Callback URL (must match X app configuration exactly)
- `scope`: `users.read` (access to user profile and username)
- `state`: Random string for CSRF protection (up to 500 chars)
- `code_challenge`: SHA256 hash of code_verifier (PKCE security)
- `code_challenge_method`: `S256` (SHA256 hashing)

**Token Exchange Endpoint**:
```
POST https://api.x.com/2/oauth2/token
Content-Type: application/x-www-form-urlencoded
```

**Parameters**:
- `code`: Authorization code from callback (valid 30 seconds)
- `grant_type`: `authorization_code`
- `client_id`: Same as authorization request
- `redirect_uri`: Same as authorization request (exact match required)
- `code_verifier`: Original random string (before SHA256 hash)

**Response**:
```json
{
  "access_token": "...",
  "token_type": "bearer",
  "expires_in": 7200,
  "scope": "users.read"
}
```

Note: No `refresh_token` in response (only if `offline.access` scope used, which we skip for MVP)

**User Info Endpoint**:
```
GET https://api.twitter.com/2/users/me
Authorization: Bearer <access_token>
```

**Response**:
```json
{
  "data": {
    "id": "123456789",
    "name": "Display Name",
    "username": "handle"
  }
}
```

### PKCE Implementation

**Code Verifier**:
- Random string (43-128 characters)
- Characters: `A-Z a-z 0-9 - . _ ~`
- Generated once per OAuth flow
- Stored temporarily (in-memory, expires after callback)

**Code Challenge**:
- SHA256 hash of code_verifier
- Base64-URL encoded (no padding)
- Sent in authorization request

**Why PKCE**:
1. **No client secret exposure** in browser/frontend code
2. **Prevents authorization code interception** attacks
3. **Required by X API** for public clients (web apps)

**Implementation**:
```python
import hashlib
import base64
import secrets

# Generate code verifier (cryptographically random)
code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')

# Generate code challenge (SHA256 hash)
code_challenge = base64.urlsafe_b64encode(
    hashlib.sha256(code_verifier.encode('utf-8')).digest()
).decode('utf-8').rstrip('=')
```

### Simplest MVP Flow (No Session Persistence)

**Step 1: Frontend Initiates OAuth** (User clicks "Link X Account")
- Frontend calls backend API: `POST /api/authors/x/auth/start`
- Backend generates:
  - `code_verifier` (random string) → stores in-memory cache (TTL: 5 minutes)
  - `code_challenge` (SHA256 of verifier)
  - `state` (random CSRF token) → stores in-memory cache (TTL: 5 minutes)
- Backend returns authorization URL with all parameters
- Frontend redirects user to X authorization page

**Step 2: User Authorizes on X**
- User approves/denies on X's authorization page
- X redirects to callback URL: `<redirect_uri>?code=<auth_code>&state=<state>`

**Step 3: Backend Receives Callback** (`GET /api/authors/x/callback`)
- Validate `state` parameter (CSRF protection) → retrieve from in-memory cache
- Retrieve `code_verifier` from in-memory cache using state as key
- Exchange authorization code for access token (POST to X token endpoint)
- Call `/2/users/me` with access token → get username
- **Discard access token immediately** (one-time use)
- Update author record with `twitter_handle = username`
- Redirect frontend to success page with wallet address

**Step 4: Frontend Displays Success**
- Show X handle in profile settings
- Hide "Link X Account" button

**No Redis/Database Session Storage**:
- Use in-memory dict for temporary storage (5-minute TTL):
  - Key: `state` (CSRF token)
  - Value: `{code_verifier, wallet_address, timestamp}`
- Cleanup on expiry or successful completion
- Simple `dict` with manual TTL checks (no external dependencies)

**Security**:
- State parameter prevents CSRF attacks
- PKCE prevents authorization code interception
- In-memory storage auto-expires (no persistent tokens)
- Wallet signature verification on OAuth start endpoint (prove wallet ownership before OAuth)

### Token Lifetime

- **Authorization code**: 30 seconds (use immediately)
- **Access token**: 2 hours (we use once, then discard)
- **No refresh tokens**: Not needed (one-time verification)

### Required Configuration

**Environment Variables** (`.env`):
```bash
# X OAuth Configuration
X_CLIENT_ID=your_client_id_from_x_developer_portal
X_REDIRECT_URI=http://localhost:5173/api/x/callback  # Development
# Production: https://glisk.com/api/x/callback
```

**X Developer Portal Setup**:
1. Create X app at https://developer.x.com/
2. Enable OAuth 2.0 in app settings
3. Set "Type of App": Web App
4. Add redirect URI (exact match required)
5. Enable "User authentication settings"
6. Permissions: Read-only (users.read scope)
7. Copy Client ID (no client secret needed for PKCE)

## Integration with Existing Code

### Database Schema

**No changes needed**: Author model already has `twitter_handle` field (Optional[str], max_length=255)

```python
class Author(SQLModel, table=True):
    __tablename__ = "authors"
    id: UUID
    wallet_address: str  # Unique, indexed
    twitter_handle: Optional[str] = Field(default=None, max_length=255)  # ✅ Already exists
    farcaster_handle: Optional[str]
    prompt_text: str
    created_at: datetime
```

### IPFS Metadata Integration

**Modify `build_metadata()` function** in `/backend/src/glisk/workers/ipfs_upload_worker.py`:

```python
def build_metadata(token: Token, image_cid: str, author: Author) -> dict:
    """Build ERC721 metadata JSON for token.

    Args:
        token: Token model instance
        image_cid: IPFS CID of uploaded image
        author: Author model instance (for twitter_handle)

    Returns:
        ERC721 metadata with optional creator.twitter field
    """
    metadata = {
        "name": f"GLISK S0 #{token.token_id}",
        "description": "GLISK Season 0. https://x.com/getglisk",
        "image": f"ipfs://{image_cid}",
        "attributes": [],
    }

    # Add creator info if twitter handle exists
    if author.twitter_handle:
        metadata["creator"] = {
            "twitter": author.twitter_handle
        }

    return metadata
```

**Note**: Must fetch author entity when processing token in IPFS upload worker

### API Endpoints

**New Routes** (add to `/backend/src/glisk/api/routes/authors.py` or new file):

1. `POST /api/authors/x/auth/start` - Initiate OAuth flow
   - Input: `{wallet_address, signature}` (EIP-191 signature verification)
   - Output: `{authorization_url}` (redirect to X)

2. `GET /api/authors/x/callback` - OAuth callback handler
   - Input: `?code=<auth_code>&state=<state>` (query params from X)
   - Process: Exchange code → get username → update author → redirect frontend
   - Output: Redirect to frontend success page

3. `GET /api/authors/{wallet_address}` - Already exists, extend response
   - Add `twitter_handle` field to response (if exists)

### Frontend Changes

**Profile Settings Page**:
- Show "Link X Account" button if `twitter_handle` is null
- Hide button if `twitter_handle` exists
- Display twitter handle: `@{username}` if linked
- No unlink/re-link functionality (MVP constraint)

**OAuth Flow** (Frontend):
1. User clicks "Link X Account" button
2. Frontend calls `POST /api/authors/x/auth/start` with wallet signature
3. Backend returns `authorization_url`
4. Frontend redirects: `window.location.href = authorization_url`
5. User authorizes on X → X redirects to callback
6. Callback endpoint updates author → redirects to success page
7. Success page shows linked X handle

## Best Practices

### Security

1. **CSRF Protection**: Always validate `state` parameter in callback
2. **Wallet Verification**: Require EIP-191 signature on `/auth/start` endpoint (prove wallet ownership)
3. **HTTPS Only**: OAuth redirect URIs must use HTTPS in production
4. **Token Hygiene**: Discard access tokens immediately after use (no storage)
5. **Short TTLs**: 5-minute expiry for in-memory OAuth state

### Error Handling

1. **User Denies Authorization**: Show friendly message, allow retry
2. **State Mismatch** (CSRF): Log security event, show error
3. **Code Expired** (30s timeout): Show "Please try again" message
4. **Token Exchange Failed**: Check X API status, show transient error
5. **Network Errors**: Retry with exponential backoff (max 3 attempts)

### UX Considerations

1. **Loading States**: Show spinner during OAuth redirect/callback
2. **Success Feedback**: "X account @username linked successfully"
3. **Error Messages**: User-friendly (avoid technical jargon)
4. **No Unlink**: Clearly communicate permanent linking in UI ("Cannot be changed")

## Dependencies

### Python Backend

**New dependencies** (`backend/pyproject.toml`):
- `httpx` (already installed) - HTTP client for X API calls
- No additional dependencies needed (use stdlib for PKCE: `hashlib`, `secrets`, `base64`)

### Frontend

**No new dependencies**:
- Use native `window.location.href` for redirect
- Standard `fetch()` API for backend calls

## Performance Considerations

- **OAuth flow**: ~2-5 seconds (network latency to X API)
- **In-memory state storage**: O(1) lookups, minimal memory footprint
- **Cleanup**: Manual TTL checks on access (no background jobs for MVP)

## Testing Strategy

1. **Unit Tests**:
   - PKCE code generation (verifier/challenge validation)
   - State parameter generation and validation
   - Token exchange request formatting
   - Metadata builder with/without twitter_handle

2. **Integration Tests**:
   - Mock X API responses (authorization, token, user info)
   - Test complete OAuth flow with in-memory state
   - Test CSRF protection (invalid state parameter)
   - Test expired authorization code

3. **Manual Testing** (Quickstart Guide):
   - Real X OAuth flow with test account
   - Verify username storage in database
   - Verify metadata includes twitter handle
   - Test error cases (user denial, network failure)

## Open Questions

None - all technical decisions resolved for MVP.

## References

- X OAuth 2.0 Documentation: https://docs.x.com/fundamentals/authentication/oauth-2-0/authorization-code
- X API v2 User Lookup: https://developer.x.com/en/docs/twitter-api/users/lookup
- PKCE RFC 7636: https://datatracker.ietf.org/doc/html/rfc7636
- OAuth 2.0 RFC 6749: https://datatracker.ietf.org/doc/html/rfc6749
