# API Contracts: X (Twitter) Account Linking

**Feature**: 007-link-x-twitter
**Date**: 2025-10-21
**Protocol**: REST/HTTP
**Base URL**: `https://api.glisk.com` (production) | `http://localhost:8000` (development)

## Overview

This document defines the HTTP API contracts for X (Twitter) account linking functionality. All endpoints follow FastAPI conventions with Pydantic validation.

## Authentication

**Wallet Signature Verification** (EIP-191):
- `/auth/start` endpoint requires wallet signature to prove ownership
- No JWT or session tokens (stateless after OAuth completes)

## Endpoints

### 1. Initiate X OAuth Flow

**Endpoint**: `POST /api/authors/x/auth/start`

**Purpose**: Generate OAuth authorization URL for user to link X account

**Authentication**: EIP-191 wallet signature required

**Request**:
```http
POST /api/authors/x/auth/start
Content-Type: application/json

{
  "wallet_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
  "message": "Link X account for wallet: 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
  "signature": "0x1234567890abcdef..."
}
```

**Request Schema**:
```python
class XAuthStartRequest(BaseModel):
    wallet_address: str = Field(
        ...,
        description="Ethereum wallet address (0x + 40 hex characters)",
        min_length=42,
        max_length=42,
        pattern=r'^0x[a-fA-F0-9]{40}$'
    )
    message: str = Field(
        ...,
        description="Message that was signed by the wallet",
        min_length=1,
        max_length=500
    )
    signature: str = Field(
        ...,
        description="EIP-191 signature hex string (0x + 130 hex characters)",
        pattern=r'^0x[a-fA-F0-9]{130}$'
    )
```

**Response** (200 OK):
```json
{
  "authorization_url": "https://x.com/i/oauth2/authorize?response_type=code&client_id=XXX&redirect_uri=https%3A%2F%2Fapi.glisk.com%2Fapi%2Fauthors%2Fx%2Fcallback&scope=users.read&state=abc123xyz...&code_challenge=def456uvw...&code_challenge_method=S256"
}
```

**Response Schema**:
```python
class XAuthStartResponse(BaseModel):
    authorization_url: str = Field(
        ...,
        description="Full OAuth authorization URL to redirect user to X",
        min_length=1
    )
```

**Error Responses**:

- **400 Bad Request** - Invalid signature or validation error
  ```json
  {
    "detail": "Signature verification failed. Please ensure you're using the correct wallet."
  }
  ```

- **409 Conflict** - Author already has X account linked
  ```json
  {
    "detail": "X account already linked. Cannot re-link in MVP."
  }
  ```

- **500 Internal Server Error** - Unexpected error
  ```json
  {
    "detail": "Failed to initiate X OAuth. Please try again later."
  }
  ```

**Processing Logic**:
1. Validate wallet signature (EIP-191)
2. Check if author exists and twitter_handle is NULL (not already linked)
3. Generate PKCE code_verifier (random 43-128 chars)
4. Generate code_challenge (SHA256 hash of verifier)
5. Generate state parameter (random 32+ chars for CSRF protection)
6. Store in-memory: `oauth_state_storage[state] = OAuthState(...)`
7. Build authorization URL with all OAuth parameters
8. Return URL to frontend

**Example cURL**:
```bash
curl -X POST http://localhost:8000/api/authors/x/auth/start \
  -H "Content-Type: application/json" \
  -d '{
    "wallet_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
    "message": "Link X account for wallet: 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
    "signature": "0x..."
  }'
```

---

### 2. OAuth Callback Handler

**Endpoint**: `GET /api/authors/x/callback`

**Purpose**: Handle OAuth redirect from X, exchange code for token, fetch username, update author

**Authentication**: None (validated via OAuth state parameter)

**Request**:
```http
GET /api/authors/x/callback?code=ABC123XYZ&state=def456uvw
```

**Query Parameters**:
```python
class XCallbackParams(BaseModel):
    code: str = Field(
        ...,
        description="Authorization code from X (valid 30 seconds)",
        min_length=1
    )
    state: str = Field(
        ...,
        description="CSRF protection token (must match in-memory storage)",
        min_length=32
    )
    # Optional error parameters (if user denies)
    error: Optional[str] = Field(
        default=None,
        description="Error code if user denied authorization"
    )
    error_description: Optional[str] = Field(
        default=None,
        description="Human-readable error description"
    )
```

**Response** (302 Found - Redirect):
```http
HTTP/1.1 302 Found
Location: https://glisk.com/profile/settings?x_linked=true&username=gliskartist
```

**Response** (Error - 302 Redirect to error page):
```http
HTTP/1.1 302 Found
Location: https://glisk.com/profile/settings?x_linked=false&error=user_denied
```

**Error Query Parameters** (in redirect URL):
- `x_linked=false` - Linking failed
- `error=user_denied` - User denied authorization
- `error=state_mismatch` - CSRF validation failed
- `error=token_exchange_failed` - X API token exchange failed
- `error=expired` - OAuth state expired (>5 min)

**Processing Logic**:
1. Check for error parameters (user denial) → redirect to error page
2. Validate state parameter (CSRF protection)
3. Retrieve OAuthState from in-memory storage using state
4. Check TTL (must be <5 minutes old)
5. Exchange authorization code for access token:
   ```http
   POST https://api.x.com/2/oauth2/token
   Content-Type: application/x-www-form-urlencoded

   code=ABC123XYZ&grant_type=authorization_code&client_id=XXX&redirect_uri=https://api.glisk.com/api/authors/x/callback&code_verifier=ZYX987CBA
   ```
6. Fetch username from X API:
   ```http
   GET https://api.twitter.com/2/users/me
   Authorization: Bearer <access_token>
   ```
7. Extract username from response: `data.username`
8. Update Author model: `twitter_handle = username`
9. Delete OAuthState from in-memory storage (cleanup)
10. **Discard access token** (do not store)
11. Redirect to frontend success page with username

**Error Handling**:
- State not found in storage → 400 Bad Request (CSRF)
- State expired (>5 min TTL) → 400 Bad Request
- Code exchange fails → Log error, redirect to error page
- Network timeout → Retry 3x with exponential backoff

**Example Redirect URLs**:
```
# Success
https://glisk.com/profile/settings?x_linked=true&username=gliskartist

# User denied
https://glisk.com/profile/settings?x_linked=false&error=user_denied

# CSRF attack detected
https://glisk.com/profile/settings?x_linked=false&error=state_mismatch
```

---

### 3. Get Author Status (Extended)

**Endpoint**: `GET /api/authors/{wallet_address}`

**Purpose**: Check if author has prompt and X account linked

**Authentication**: None (public read)

**Request**:
```http
GET /api/authors/0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0
```

**Response** (200 OK):
```json
{
  "has_prompt": true,
  "twitter_handle": "gliskartist"
}
```

**Response Schema** (Extended):
```python
class AuthorStatusResponse(BaseModel):
    has_prompt: bool = Field(
        ...,
        description="True if author has configured a prompt"
    )
    twitter_handle: Optional[str] = Field(
        default=None,
        description="X username if linked, null otherwise"
    )
```

**Example Responses**:

*Author with prompt and X linked*:
```json
{
  "has_prompt": true,
  "twitter_handle": "gliskartist"
}
```

*Author with prompt, no X linked*:
```json
{
  "has_prompt": true,
  "twitter_handle": null
}
```

*Author not found*:
```json
{
  "has_prompt": false,
  "twitter_handle": null
}
```

**Note**: This is an extension of existing endpoint - adds `twitter_handle` field to response.

---

## OAuth State Storage (Internal)

**Not exposed via API** - internal implementation detail

```python
# In-memory storage structure
oauth_state_storage: dict[str, OAuthState] = {}

class OAuthState:
    """Temporary OAuth state (5-min TTL)."""

    state: str              # Random CSRF token (dict key)
    code_verifier: str      # PKCE verifier (for token exchange)
    wallet_address: str     # Author wallet (for updating after OAuth)
    created_at: float       # Unix timestamp
    expires_at: float       # created_at + 300 seconds

# Example entry:
oauth_state_storage["abc123xyz..."] = OAuthState(
    state="abc123xyz...",
    code_verifier="ZYX987CBA...",
    wallet_address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
    created_at=1697123456.789,
    expires_at=1697123756.789  # +300 seconds
)
```

---

## Frontend Integration

### Flow Diagram

```
Frontend                    Backend                     X API
   │                           │                           │
   │──POST /auth/start────────►│                           │
   │  (wallet signature)        │                           │
   │                           │──Generate PKCE params     │
   │                           │──Store in-memory state    │
   │◄──authorization_url───────│                           │
   │                           │                           │
   │──window.location.href = url                          │
   │                                                       │
   │────────────────────────────────────────────────────►│
   │                           User authorizes on X       │
   │◄────────────────────────────────────────────────────│
   │  (redirect with code & state)                        │
   │                           │                           │
   │                           │◄────GET /callback?code=...│state=...
   │                           │──Validate state (CSRF)    │
   │                           │──Exchange code for token──►│
   │                           │◄──Access token────────────│
   │                           │──GET /users/me────────────►│
   │                           │◄──{username}──────────────│
   │                           │──Update author.twitter_handle
   │                           │──Delete in-memory state   │
   │◄────────302 Redirect──────│                           │
   │  (to success page)         │                           │
   │                           │                           │
```

### Frontend Code Example

```typescript
// Step 1: User clicks "Link X Account" button
async function linkXAccount() {
  // Sign message with wallet
  const message = `Link X account for wallet: ${walletAddress}`;
  const signature = await signMessage(message);

  // Call backend to get authorization URL
  const response = await fetch('/api/authors/x/auth/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      wallet_address: walletAddress,
      message,
      signature
    })
  });

  if (!response.ok) {
    const error = await response.json();
    alert(error.detail);
    return;
  }

  const { authorization_url } = await response.json();

  // Redirect to X authorization page
  window.location.href = authorization_url;
}

// Step 2: Handle callback redirect (on success page)
const params = new URLSearchParams(window.location.search);
if (params.get('x_linked') === 'true') {
  const username = params.get('username');
  console.log(`X account @${username} linked successfully!`);
}
```

---

## Security Considerations

1. **CSRF Protection**: State parameter validated against in-memory storage
2. **PKCE**: Code verifier prevents authorization code interception
3. **Short TTLs**: OAuth state expires after 5 minutes
4. **No Token Storage**: Access tokens discarded immediately after username fetch
5. **Wallet Signature**: Proves wallet ownership before OAuth initiation
6. **HTTPS Only**: Production redirect URIs must use HTTPS

---

## Rate Limiting

**Future Enhancement** (out of scope for MVP):
- Limit `/auth/start` to 5 requests/minute per wallet address
- Limit `/callback` to 10 requests/minute per IP

**MVP**: No explicit rate limiting (rely on X API rate limits)

---

## Monitoring and Logging

**Structured Logs** (structlog):

```python
# OAuth flow initiated
logger.info(
    "x_oauth_flow_started",
    wallet_address=wallet_address,
    state=state[:8]  # Redacted for privacy
)

# Successful linking
logger.info(
    "x_account_linked",
    wallet_address=wallet_address,
    twitter_handle=username
)

# User denied authorization
logger.warning(
    "x_oauth_denied",
    wallet_address=wallet_address,
    error=error_description
)

# CSRF attack detected
logger.error(
    "x_oauth_state_mismatch",
    state_param=state[:8],
    ip_address=request.client.host
)
```

---

## Testing

### Unit Tests

```python
def test_auth_start_valid_signature():
    """Test OAuth initiation with valid wallet signature."""
    response = client.post("/api/authors/x/auth/start", json={
        "wallet_address": "0x742d35Cc...",
        "message": "Link X account...",
        "signature": "0x1234..."
    })
    assert response.status_code == 200
    assert "authorization_url" in response.json()
    assert "x.com/i/oauth2/authorize" in response.json()["authorization_url"]

def test_callback_valid_state():
    """Test callback with valid state parameter."""
    # Setup in-memory state
    state = "abc123"
    oauth_state_storage[state] = OAuthState(...)

    # Mock X API responses
    with patch_x_api_responses():
        response = client.get(f"/api/authors/x/callback?code=XYZ&state={state}")
        assert response.status_code == 302
        assert "x_linked=true" in response.headers["Location"]

def test_callback_csrf_protection():
    """Test callback rejects invalid state (CSRF protection)."""
    response = client.get("/api/authors/x/callback?code=XYZ&state=invalid")
    assert response.status_code == 302
    assert "error=state_mismatch" in response.headers["Location"]
```

### Integration Tests

- Test complete OAuth flow with mocked X API
- Test PKCE code verifier/challenge validation
- Test TTL expiry handling
- Test concurrent OAuth flows (race conditions)

---

## Migration Path

**From MVP to Full Features** (future):

1. Add unlink endpoint: `DELETE /api/authors/x/unlink`
2. Add re-link endpoint (overwrite existing handle)
3. Add rate limiting middleware
4. Add Redis for distributed state storage (multi-instance backend)
5. Add audit log table for linking events

---

## Summary

- **2 new endpoints**: `/auth/start`, `/callback`
- **1 extended endpoint**: `/authors/{wallet}` (add twitter_handle field)
- **Stateless design**: No session persistence (in-memory state only during OAuth)
- **Security**: EIP-191 signatures + PKCE + CSRF protection
- **Simple integration**: Standard OAuth 2.0 redirect flow
