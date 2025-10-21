# Quickstart Guide: X (Twitter) Account Linking

**Feature**: 007-link-x-twitter
**Date**: 2025-10-21
**Audience**: Developers and Testers

## Overview

This guide walks you through setting up, implementing, and testing X (Twitter) account linking for glisk authors. Follow steps sequentially for fastest MVP delivery.

## Prerequisites

Before starting implementation:

1. **X Developer Account** (create at https://developer.x.com/)
2. **Backend running** (FastAPI server on `http://localhost:8000`)
3. **Frontend running** (React app on `http://localhost:5173`)
4. **Database migrated** (PostgreSQL with authors table)
5. **Wallet connected** (MetaMask or similar for signature testing)

## Setup (30 minutes)

### Step 1: Create X Application

1. **Go to X Developer Portal**: https://developer.x.com/en/portal/dashboard
2. **Create New App** (or use existing app)
3. **Navigate to App Settings** → "User authentication settings"
4. **Enable OAuth 2.0**
5. **Configure Settings**:
   ```
   Type of App: Web App
   App permissions: Read
   Callback URI / Redirect URL:
     - Development: http://localhost:8000/api/authors/x/callback
     - Production: https://api.glisk.com/api/authors/x/callback
   Website URL: https://glisk.com
   ```
6. **Save Settings**
7. **Copy Client ID** (you'll need this)

**Important**: Do NOT generate Client Secret (not needed for PKCE)

### Step 2: Configure Backend Environment

Edit `backend/.env`:

```bash
# X OAuth Configuration
X_CLIENT_ID=your_client_id_from_step_1
X_REDIRECT_URI=http://localhost:8000/api/authors/x/callback

# Existing configuration (no changes)
DATABASE_URL=postgresql://glisk:password@localhost:5432/glisk
ALCHEMY_API_KEY=...
# ...
```

### Step 3: Verify Database Schema

The `twitter_handle` field already exists in the `authors` table. No migration needed!

```sql
-- Verify field exists (run in psql)
\d authors;

-- Should show:
--  twitter_handle | character varying(255) |
```

If missing, check migration history:
```bash
cd backend
uv run alembic history
uv run alembic upgrade head
```

## Implementation (2-4 hours)

### Phase 1: Backend OAuth Service

**File**: `backend/src/glisk/services/x_oauth.py` (new file)

```python
"""X (Twitter) OAuth 2.0 service with PKCE flow."""

import hashlib
import base64
import secrets
import time
from typing import Optional
from dataclasses import dataclass

import httpx
import structlog

logger = structlog.get_logger()

# In-memory OAuth state storage (5-minute TTL)
oauth_state_storage: dict[str, "OAuthState"] = {}


@dataclass
class OAuthState:
    """Temporary OAuth state for PKCE flow."""

    state: str
    code_verifier: str
    wallet_address: str
    created_at: float
    expires_at: float


class XOAuthService:
    """X OAuth 2.0 client with PKCE support."""

    def __init__(self, client_id: str, redirect_uri: str):
        self.client_id = client_id
        self.redirect_uri = redirect_uri
        self.auth_base_url = "https://x.com/i/oauth2/authorize"
        self.token_url = "https://api.x.com/2/oauth2/token"
        self.user_me_url = "https://api.twitter.com/2/users/me"

    def generate_pkce_pair(self) -> tuple[str, str]:
        """Generate PKCE code_verifier and code_challenge."""
        # Code verifier: 43-128 chars, base64url-encoded random bytes
        code_verifier = base64.urlsafe_b64encode(
            secrets.token_bytes(32)
        ).decode('utf-8').rstrip('=')

        # Code challenge: SHA256 hash of verifier
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('utf-8')).digest()
        ).decode('utf-8').rstrip('=')

        return code_verifier, code_challenge

    def generate_state(self) -> str:
        """Generate random state parameter for CSRF protection."""
        return base64.urlsafe_b64encode(
            secrets.token_bytes(32)
        ).decode('utf-8').rstrip('=')

    def build_authorization_url(
        self,
        wallet_address: str,
    ) -> tuple[str, str, str]:
        """Build OAuth authorization URL and store state.

        Returns:
            (authorization_url, state, code_verifier)
        """
        code_verifier, code_challenge = self.generate_pkce_pair()
        state = self.generate_state()

        # Store OAuth state in-memory (5-min TTL)
        now = time.time()
        oauth_state_storage[state] = OAuthState(
            state=state,
            code_verifier=code_verifier,
            wallet_address=wallet_address,
            created_at=now,
            expires_at=now + 300,  # 5 minutes
        )

        # Build authorization URL
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "users.read",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        authorization_url = f"{self.auth_base_url}?{query_string}"

        logger.info(
            "x_oauth_flow_started",
            wallet_address=wallet_address,
            state=state[:8],  # Redacted
        )

        return authorization_url, state, code_verifier

    async def exchange_code_for_token(
        self,
        code: str,
        code_verifier: str,
    ) -> str:
        """Exchange authorization code for access token.

        Returns:
            access_token (str)

        Raises:
            HTTPException on failure
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.token_url,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "code": code,
                    "grant_type": "authorization_code",
                    "client_id": self.client_id,
                    "redirect_uri": self.redirect_uri,
                    "code_verifier": code_verifier,
                },
            )
            response.raise_for_status()
            return response.json()["access_token"]

    async def fetch_username(self, access_token: str) -> str:
        """Fetch username from X API using access token.

        Returns:
            username (str) - X handle without @ symbol

        Raises:
            HTTPException on failure
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                self.user_me_url,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return response.json()["data"]["username"]


def cleanup_expired_oauth_states():
    """Remove expired OAuth state entries (TTL > 5 minutes)."""
    now = time.time()
    expired_keys = [
        state for state, data in oauth_state_storage.items()
        if now > data.expires_at
    ]
    for key in expired_keys:
        del oauth_state_storage[key]
        logger.debug("x_oauth_state_expired", state=key[:8])
```

### Phase 2: Backend API Endpoints

**File**: `backend/src/glisk/api/routes/x_auth.py` (new file)

```python
"""X (Twitter) OAuth API endpoints."""

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from glisk.api.dependencies import get_uow_factory
from glisk.core.settings import Settings, get_settings
from glisk.services.wallet_signature import verify_wallet_signature
from glisk.services.x_oauth import XOAuthService, oauth_state_storage, cleanup_expired_oauth_states

logger = structlog.get_logger()
router = APIRouter(prefix="/api/authors/x", tags=["x-auth"])


# Request/Response Models

class XAuthStartRequest(BaseModel):
    """Request to initiate X OAuth flow."""

    wallet_address: str = Field(..., min_length=42, max_length=42)
    message: str = Field(..., min_length=1, max_length=500)
    signature: str = Field(..., min_length=1)


class XAuthStartResponse(BaseModel):
    """Response with OAuth authorization URL."""

    authorization_url: str = Field(..., min_length=1)


# API Endpoints

@router.post("/auth/start", response_model=XAuthStartResponse)
async def start_x_oauth(
    request: XAuthStartRequest,
    settings: Settings = Depends(get_settings),
    uow_factory=Depends(get_uow_factory),
) -> XAuthStartResponse:
    """Initiate X OAuth flow with wallet signature verification."""
    # Step 1: Verify wallet signature
    is_valid = verify_wallet_signature(
        wallet_address=request.wallet_address,
        message=request.message,
        signature=request.signature,
    )
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Signature verification failed",
        )

    # Step 2: Check if author already has X account linked
    async with await uow_factory() as uow:
        author = await uow.authors.get_by_wallet(request.wallet_address)
        if author and author.twitter_handle:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="X account already linked. Cannot re-link in MVP.",
            )

    # Step 3: Generate OAuth authorization URL
    oauth_service = XOAuthService(
        client_id=settings.X_CLIENT_ID,
        redirect_uri=settings.X_REDIRECT_URI,
    )
    authorization_url, _, _ = oauth_service.build_authorization_url(
        wallet_address=request.wallet_address
    )

    return XAuthStartResponse(authorization_url=authorization_url)


@router.get("/callback")
async def x_oauth_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    settings: Settings = Depends(get_settings),
    uow_factory=Depends(get_uow_factory),
) -> RedirectResponse:
    """Handle OAuth callback from X."""
    # Cleanup expired states
    cleanup_expired_oauth_states()

    # Handle user denial
    if error:
        logger.warning("x_oauth_denied", error=error)
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/profile/settings?x_linked=false&error=user_denied"
        )

    # Validate required parameters
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state")

    # Retrieve OAuth state (CSRF protection)
    oauth_state = oauth_state_storage.get(state)
    if not oauth_state:
        logger.error("x_oauth_state_not_found", state=state[:8])
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/profile/settings?x_linked=false&error=state_mismatch"
        )

    # Check TTL
    import time
    if time.time() > oauth_state.expires_at:
        del oauth_state_storage[state]
        logger.warning("x_oauth_state_expired", state=state[:8])
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/profile/settings?x_linked=false&error=expired"
        )

    try:
        # Exchange code for access token
        oauth_service = XOAuthService(
            client_id=settings.X_CLIENT_ID,
            redirect_uri=settings.X_REDIRECT_URI,
        )
        access_token = await oauth_service.exchange_code_for_token(
            code=code,
            code_verifier=oauth_state.code_verifier,
        )

        # Fetch username from X API
        username = await oauth_service.fetch_username(access_token)

        # Update author record
        async with await uow_factory() as uow:
            author = await uow.authors.upsert_x_handle(
                wallet_address=oauth_state.wallet_address,
                twitter_handle=username,
            )

        # Cleanup state
        del oauth_state_storage[state]

        logger.info(
            "x_account_linked",
            wallet_address=oauth_state.wallet_address,
            twitter_handle=username,
        )

        # Redirect to success page
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/profile/settings?x_linked=true&username={username}"
        )

    except Exception as e:
        logger.error("x_oauth_callback_error", error=str(e))
        # Cleanup state on error
        if state in oauth_state_storage:
            del oauth_state_storage[state]
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/profile/settings?x_linked=false&error=token_exchange_failed"
        )
```

### Phase 3: Update Author Repository

**File**: `backend/src/glisk/repositories/author.py` (add method)

```python
# Add to AuthorRepository class:

async def upsert_x_handle(
    self,
    wallet_address: str,
    twitter_handle: str,
) -> Author:
    """Update or create author with X handle.

    Args:
        wallet_address: Ethereum wallet address
        twitter_handle: X username (without @ symbol)

    Returns:
        Updated Author entity
    """
    # Try to get existing author
    author = await self.get_by_wallet(wallet_address)

    if author:
        # Update existing author
        author.twitter_handle = twitter_handle
        self.session.add(author)
    else:
        # Create new author (with default prompt if needed)
        author = Author(
            wallet_address=wallet_address,
            twitter_handle=twitter_handle,
            prompt_text="",  # Empty prompt (user must set later)
        )
        self.session.add(author)

    await self.session.flush()
    await self.session.refresh(author)
    return author
```

### Phase 4: Update IPFS Metadata Generation

**File**: `backend/src/glisk/workers/ipfs_upload_worker.py` (modify function)

```python
# Update build_metadata function (around line 27):

def build_metadata(token: Token, image_cid: str, twitter_handle: Optional[str] = None) -> dict:
    """Build ERC721 metadata JSON for token.

    Args:
        token: Token model instance
        image_cid: IPFS CID of uploaded image
        twitter_handle: Optional X handle from author profile

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
    if twitter_handle:
        metadata["creator"] = {
            "twitter": twitter_handle
        }

    return metadata


# Update process_single_token function to fetch author and pass twitter_handle:
async def process_single_token(...):
    # ... existing code ...

    # Fetch author to get twitter_handle
    author = await session.scalar(
        select(Author).where(Author.wallet_address == attached_token.author_wallet)
    )

    # ... upload image ...

    # Build metadata with twitter handle
    metadata = build_metadata(
        attached_token,
        image_cid,
        twitter_handle=author.twitter_handle if author else None
    )

    # ... rest of function ...
```

### Phase 5: Update Settings

**File**: `backend/src/glisk/core/settings.py` (add fields)

```python
# Add to Settings class:

X_CLIENT_ID: str = Field(..., description="X OAuth 2.0 Client ID")
X_REDIRECT_URI: str = Field(..., description="X OAuth callback URL")
FRONTEND_URL: str = Field(default="http://localhost:5173", description="Frontend base URL")
```

### Phase 6: Register Routes

**File**: `backend/src/glisk/main.py` (add import and registration)

```python
from glisk.api.routes import x_auth

# ... existing code ...

# Register routers
app.include_router(x_auth.router)  # Add this line
```

### Phase 7: Frontend Integration

**File**: `frontend/src/pages/ProfileSettings.tsx` (add X linking UI)

```typescript
import { useState } from 'react';
import { useAccount, useSignMessage } from 'wagmi';

function ProfileSettings() {
  const { address } = useAccount();
  const { signMessageAsync } = useSignMessage();
  const [twitterHandle, setTwitterHandle] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Fetch author status on mount
  useEffect(() => {
    if (address) {
      fetch(`/api/authors/${address}`)
        .then(res => res.json())
        .then(data => setTwitterHandle(data.twitter_handle));
    }
  }, [address]);

  // Check for OAuth callback params
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('x_linked') === 'true') {
      const username = params.get('username');
      setTwitterHandle(username);
      alert(`X account @${username} linked successfully!`);
      // Clear query params
      window.history.replaceState({}, '', window.location.pathname);
    } else if (params.get('x_linked') === 'false') {
      alert(`Failed to link X account: ${params.get('error')}`);
    }
  }, []);

  async function linkXAccount() {
    if (!address) return;

    setLoading(true);
    try {
      // Sign message
      const message = `Link X account for wallet: ${address}`;
      const signature = await signMessageAsync({ message });

      // Call backend
      const response = await fetch('/api/authors/x/auth/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          wallet_address: address,
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

      // Redirect to X
      window.location.href = authorization_url;
    } catch (error) {
      console.error('Failed to initiate X linking:', error);
      alert('Failed to initiate X linking');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h2>Profile Settings</h2>

      {/* X Account Section */}
      <div>
        <h3>X (Twitter) Account</h3>
        {twitterHandle ? (
          <p>Linked: @{twitterHandle}</p>
        ) : (
          <button onClick={linkXAccount} disabled={loading}>
            {loading ? 'Redirecting...' : 'Link X Account'}
          </button>
        )}
      </div>
    </div>
  );
}
```

## Testing (1 hour)

### Manual Test 1: Complete OAuth Flow

1. **Start backend**: `cd backend && uv run uvicorn glisk.main:app --reload`
2. **Start frontend**: `cd frontend && npm run dev`
3. **Connect wallet**: Open http://localhost:5173, connect MetaMask
4. **Navigate to settings**: `/profile/settings`
5. **Click "Link X Account"**: Should prompt for wallet signature
6. **Sign message**: Approve in MetaMask
7. **Redirected to X**: Should see X authorization page
8. **Approve on X**: Click "Authorize app"
9. **Redirected back**: Should see "X account @username linked successfully!"
10. **Verify database**:
    ```bash
    docker exec backend-postgres-1 psql -U glisk -d glisk -c "SELECT wallet_address, twitter_handle FROM authors;"
    ```
11. **Verify UI**: "Link X Account" button should be hidden, showing `@username` instead

### Manual Test 2: User Denies Authorization

1. Follow steps 1-6 from Test 1
2. **Click "Cancel" on X authorization page**
3. **Verify**: Redirected back with error message
4. **Verify database**: `twitter_handle` should still be NULL
5. **Verify UI**: "Link X Account" button should still be visible

### Manual Test 3: Re-link Prevention (MVP Constraint)

1. Complete Test 1 (link X account)
2. **Click "Link X Account" again** (if button somehow visible)
3. **Verify**: Should return 409 Conflict error: "X account already linked"
4. **Verify UI**: Button should be hidden (not clickable)

### Manual Test 4: NFT Metadata Includes X Handle

1. Complete Test 1 (link X account)
2. **Mint NFT** (use existing mint flow)
3. **Wait for IPFS upload** (check logs)
4. **Fetch metadata from IPFS**:
    ```bash
    # Get metadata CID from database
    docker exec backend-postgres-1 psql -U glisk -d glisk -c "SELECT metadata_cid FROM tokens_s0 ORDER BY mint_timestamp DESC LIMIT 1;"

    # Fetch from IPFS gateway
    curl https://gateway.pinata.cloud/ipfs/<metadata_cid>
    ```
5. **Verify JSON**:
    ```json
    {
      "name": "GLISK S0 #123",
      "description": "GLISK Season 0. https://x.com/getglisk",
      "image": "ipfs://...",
      "attributes": [],
      "creator": {
        "twitter": "your_username"  // ✅ Should exist
      }
    }
    ```

## Troubleshooting

### Issue: "Callback URL mismatch" error from X

**Solution**: Verify X app settings:
- Redirect URI must **exactly** match `X_REDIRECT_URI` in `.env`
- Include protocol (`http://` or `https://`)
- No trailing slashes
- Port must match (e.g., `:8000`)

### Issue: "State mismatch" error in callback

**Possible causes**:
1. OAuth state expired (>5 minutes) → Retry OAuth
2. Backend restarted (in-memory state lost) → Retry OAuth
3. CSRF attack → Check request logs

**Solution**: Clear browser cache and retry

### Issue: "401 Unauthorized" when fetching username

**Possible causes**:
1. Invalid `X_CLIENT_ID` in `.env`
2. X app not configured for OAuth 2.0
3. Access token expired

**Solution**:
- Verify Client ID in X Developer Portal
- Check X app permissions (should be "Read")
- Check backend logs for token exchange errors

### Issue: "twitter_handle not showing in metadata"

**Solution**:
1. Verify author record in database: `SELECT * FROM authors WHERE wallet_address = '0x...';`
2. Verify `build_metadata()` function receives `twitter_handle` parameter
3. Check IPFS upload worker logs for errors
4. Re-trigger IPFS upload (reset token status to `generating`)

## Production Deployment

### Environment Variables (Production)

```bash
# Production .env (backend)
X_CLIENT_ID=your_production_client_id
X_REDIRECT_URI=https://api.glisk.com/api/authors/x/callback
FRONTEND_URL=https://glisk.com
```

### X App Configuration (Production)

1. Add production callback URL in X Developer Portal:
   - `https://api.glisk.com/api/authors/x/callback`
2. Verify app is in "Production" environment (not "Development")
3. Test with production URLs before public launch

### Security Checklist

- [ ] HTTPS enabled for all production URLs
- [ ] X app Client ID is not exposed in frontend code
- [ ] Wallet signature verification enabled on `/auth/start`
- [ ] CSRF protection via state parameter
- [ ] Access tokens discarded immediately after use
- [ ] OAuth state TTL set to 5 minutes
- [ ] Structured logging enabled for security events

## Next Steps

After MVP launch, consider:
1. **Add unlink endpoint** (allow authors to remove X link)
2. **Add re-link endpoint** (allow authors to change X account)
3. **Redis for state storage** (distributed in-memory storage for multi-instance backend)
4. **Rate limiting** (prevent abuse)
5. **Audit log table** (track linking events)
6. **Fetch additional X profile data** (follower count, profile image, bio)

## Support

For issues or questions:
- **Backend logs**: `docker-compose logs -f backend`
- **Database queries**: `docker exec -it backend-postgres-1 psql -U glisk -d glisk`
- **X API Status**: https://api.x.com/status
- **Developer Docs**: https://docs.x.com/

---

**Estimated Implementation Time**: 3-5 hours (including testing)
