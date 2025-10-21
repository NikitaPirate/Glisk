"""X (Twitter) OAuth 2.0 service for one-time account verification.

This module provides OAuth 2.0 Authorization Code Flow with PKCE (Proof Key for
Code Exchange) for verifying X account ownership. The service generates PKCE
parameters, builds authorization URLs, exchanges authorization codes for access
tokens, and fetches usernames from the X API.

Key Features:
- PKCE implementation (no client secret needed)
- In-memory state storage with 5-minute TTL
- One-time token use (discard after username fetch)
- CSRF protection via state parameter
- Structured logging for security events

References:
- X OAuth 2.0: https://docs.x.com/fundamentals/authentication/oauth-2-0/authorization-code
- PKCE RFC 7636: https://datatracker.ietf.org/doc/html/rfc7636
"""

import base64
import hashlib
import secrets
import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlencode

import httpx
import structlog

logger = structlog.get_logger()

# X API OAuth 2.0 endpoints
X_AUTHORIZATION_URL = "https://x.com/i/oauth2/authorize"
X_TOKEN_URL = "https://api.x.com/2/oauth2/token"
X_USER_INFO_URL = "https://api.x.com/2/users/me"

# OAuth state TTL (5 minutes in seconds)
OAUTH_STATE_TTL_SECONDS = 300


@dataclass
class OAuthState:
    """Temporary OAuth state for PKCE flow (5-minute TTL).

    Attributes:
        state: Random CSRF token (serves as dict key for lookup)
        code_verifier: PKCE code verifier (43-128 chars, used to verify token exchange)
        wallet_address: Author's wallet address (for updating after OAuth completes)
        created_at: Unix timestamp when state was created
        expires_at: Unix timestamp when state expires (created_at + 300 seconds)
    """

    state: str
    code_verifier: str
    wallet_address: str
    created_at: float
    expires_at: float


# Module-level in-memory storage for OAuth state (no Redis for MVP)
# Key: state parameter (random CSRF token)
# Value: OAuthState dataclass with PKCE verifier and wallet address
# Lifetime: 5 minutes (auto-cleanup on access or manual cleanup)
oauth_state_storage: dict[str, OAuthState] = {}


class XOAuthService:
    """X (Twitter) OAuth 2.0 service for one-time account verification.

    This service handles the complete OAuth 2.0 Authorization Code Flow with PKCE
    for verifying X account ownership. It generates PKCE parameters, manages
    temporary state storage, exchanges authorization codes for tokens, and fetches
    usernames from the X API.

    Example:
        >>> service = XOAuthService(client_id="abc123", redirect_uri="http://localhost:8000/callback")
        >>> auth_url = service.build_authorization_url("0x742d35Cc...")
        >>> # User authorizes on X, callback receives code and state
        >>> username = await service.fetch_username_from_code(code, state)
        >>> # Update author record with username
    """

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        """Initialize X OAuth service.

        Args:
            client_id: X application client ID from Developer Portal
            client_secret: X application client secret from Developer Portal
            redirect_uri: OAuth callback URI (must match X app configuration exactly)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    def generate_pkce_pair(self) -> tuple[str, str]:
        """Generate PKCE code verifier and code challenge pair.

        PKCE (Proof Key for Code Exchange) prevents authorization code interception
        attacks by requiring the client to prove possession of the original code
        verifier when exchanging the authorization code for an access token.

        Implementation follows RFC 7636:
        - code_verifier: Cryptographically random string (43-128 characters)
        - code_challenge: Base64-URL encoded SHA256 hash of code_verifier

        Returns:
            tuple[str, str]: (code_verifier, code_challenge)
                - code_verifier: Random string to store temporarily (43 chars)
                - code_challenge: SHA256 hash for authorization URL (43 chars)

        Example:
            >>> verifier, challenge = service.generate_pkce_pair()
            >>> len(verifier)  # 43 characters
            43
            >>> len(challenge)  # 43 characters (SHA256 hash, base64-url encoded)
            43
        """
        # Generate cryptographically random code verifier (32 bytes → 43 chars base64)
        # Use secrets module for cryptographically strong randomness
        code_verifier = (
            base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("utf-8").rstrip("=")
        )

        # Generate code challenge (SHA256 hash of verifier)
        # Base64-URL encode with padding removed (per RFC 7636)
        code_challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode("utf-8")).digest())
            .decode("utf-8")
            .rstrip("=")
        )

        logger.debug(
            "pkce_pair_generated",
            verifier_length=len(code_verifier),
            challenge_length=len(code_challenge),
        )

        return code_verifier, code_challenge

    def generate_state(self) -> str:
        """Generate random state parameter for CSRF protection.

        The state parameter is a cryptographically random string that prevents
        Cross-Site Request Forgery (CSRF) attacks. It must be validated in the
        OAuth callback to ensure the authorization response matches the original
        request from this application.

        Returns:
            str: Random state string (43 characters, base64-url encoded)

        Example:
            >>> state = service.generate_state()
            >>> len(state)
            43
        """
        # Generate 32 bytes of cryptographically random data → 43 chars base64
        state = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("utf-8").rstrip("=")

        logger.debug("oauth_state_generated", state_length=len(state))

        return state

    def build_authorization_url(self, wallet_address: str) -> str:
        """Build X authorization URL with PKCE parameters and store state.

        This method generates all required OAuth parameters (PKCE pair, state),
        stores them in in-memory cache with 5-minute TTL, and builds the complete
        authorization URL for redirecting the user to X's authorization page.

        Args:
            wallet_address: Ethereum wallet address of the author (for storing with state)

        Returns:
            str: Complete X authorization URL with all parameters

        Side Effects:
            - Stores OAuthState in oauth_state_storage with 5-minute TTL
            - Cleans up expired OAuth states before creating new one

        Example:
            >>> url = service.build_authorization_url("0x742d35Cc...")
            >>> print(url)
            https://x.com/i/oauth2/authorize?response_type=code&client_id=...
        """
        # Cleanup expired states before creating new one
        cleanup_expired_oauth_states()

        # Generate PKCE parameters
        code_verifier, code_challenge = self.generate_pkce_pair()

        # Generate CSRF state token
        state = self.generate_state()

        # Store OAuth state in memory with 5-minute TTL
        now = time.time()
        oauth_state = OAuthState(
            state=state,
            code_verifier=code_verifier,
            wallet_address=wallet_address,
            created_at=now,
            expires_at=now + OAUTH_STATE_TTL_SECONDS,
        )
        oauth_state_storage[state] = oauth_state

        logger.info(
            "x_oauth_flow_started",
            wallet_address=wallet_address,
            state_count=len(oauth_state_storage),
            state_preview=state[:8] + "...",
        )

        # Build authorization URL with all parameters
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "tweet.read users.read",  # Required scopes for /2/users/me endpoint
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",  # SHA256 hashing
        }

        authorization_url = f"{X_AUTHORIZATION_URL}?{urlencode(params)}"

        logger.debug(
            "authorization_url_built",
            url_preview=authorization_url[:100] + "...",
            params_count=len(params),
        )

        return authorization_url

    async def exchange_code_for_token(self, code: str, code_verifier: str) -> str:
        """Exchange authorization code for access token using PKCE.

        This method calls X's token endpoint to exchange the authorization code
        (received in OAuth callback) for an access token. The code_verifier proves
        that this client initiated the original authorization request (PKCE security).

        Args:
            code: Authorization code from X OAuth callback (valid 30 seconds)
            code_verifier: Original PKCE code verifier (must match challenge)

        Returns:
            str: Bearer access token for X API calls (valid 2 hours)

        Raises:
            ValueError: If token exchange fails (invalid code, network error, etc.)

        Example:
            >>> token = await service.exchange_code_for_token(code, verifier)
            >>> print(token[:20])
            bWF0aXZlIHRva2VuIGZv...
        """
        logger.debug("x_token_exchange_started", code_preview=code[:10] + "...")

        # Build token exchange request
        data = {
            "code": code,
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "code_verifier": code_verifier,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    X_TOKEN_URL,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    auth=(self.client_id, self.client_secret),  # Basic Auth required by X API
                )

                # Check for HTTP errors
                if response.status_code != 200:
                    error_detail = response.text[:200]
                    logger.error(
                        "x_token_exchange_failed",
                        status_code=response.status_code,
                        error=error_detail,
                    )
                    raise ValueError(
                        f"X token exchange failed with status "
                        f"{response.status_code}: {error_detail}"
                    )

                # Parse token response
                token_data = response.json()
                access_token = token_data.get("access_token")

                if not access_token:
                    logger.error(
                        "x_token_exchange_missing_token", response_keys=list(token_data.keys())
                    )
                    raise ValueError("X token response missing access_token field")

                logger.info(
                    "x_token_exchange_success",
                    token_type=token_data.get("token_type"),
                    expires_in=token_data.get("expires_in"),
                )

                return access_token

        except httpx.TimeoutException as e:
            logger.error("x_token_exchange_timeout", error=str(e))
            raise ValueError(f"X API timeout during token exchange: {str(e)}")
        except httpx.RequestError as e:
            logger.error(
                "x_token_exchange_network_error", error=str(e), error_type=type(e).__name__
            )
            raise ValueError(f"Network error during X token exchange: {str(e)}")

    async def fetch_username(self, access_token: str) -> str:
        """Fetch X username from /2/users/me endpoint.

        This method calls X's user info endpoint with the access token to retrieve
        the authenticated user's username. This is the final step in the OAuth flow
        before updating the author record.

        Args:
            access_token: Bearer token from token exchange (valid 2 hours)

        Returns:
            str: X username (handle without @ symbol, e.g., "gliskartist")

        Raises:
            ValueError: If username fetch fails (invalid token, network error, etc.)

        Example:
            >>> username = await service.fetch_username(token)
            >>> print(username)
            gliskartist
        """
        logger.debug("x_username_fetch_started")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    X_USER_INFO_URL,
                    headers={"Authorization": f"Bearer {access_token}"},
                )

                # Check for HTTP errors
                if response.status_code != 200:
                    error_detail = response.text[:200]
                    logger.error(
                        "x_username_fetch_failed",
                        status_code=response.status_code,
                        error=error_detail,
                    )
                    raise ValueError(
                        f"X user info fetch failed with status "
                        f"{response.status_code}: {error_detail}"
                    )

                # Parse user info response
                user_data = response.json()
                username = user_data.get("data", {}).get("username")

                if not username:
                    logger.error(
                        "x_username_fetch_missing_field", response_keys=list(user_data.keys())
                    )
                    raise ValueError("X user info response missing username field")

                logger.info("x_username_fetch_success", username=username)

                return username

        except httpx.TimeoutException as e:
            logger.error("x_username_fetch_timeout", error=str(e))
            raise ValueError(f"X API timeout during username fetch: {str(e)}")
        except httpx.RequestError as e:
            logger.error(
                "x_username_fetch_network_error", error=str(e), error_type=type(e).__name__
            )
            raise ValueError(f"Network error during X username fetch: {str(e)}")


def cleanup_expired_oauth_states() -> int:
    """Remove expired OAuth state entries from in-memory storage.

    This utility function removes all OAuth states that have exceeded their
    5-minute TTL. Called automatically before creating new states and can be
    called manually for periodic cleanup.

    Returns:
        int: Number of expired states removed

    Example:
        >>> expired_count = cleanup_expired_oauth_states()
        >>> print(f"Cleaned up {expired_count} expired states")
        Cleaned up 3 expired states
    """
    now = time.time()

    # Find all expired state keys
    expired_keys = [state for state, data in oauth_state_storage.items() if now > data.expires_at]

    # Remove expired entries
    for key in expired_keys:
        del oauth_state_storage[key]

    if expired_keys:
        logger.info(
            "x_oauth_states_cleaned_up",
            expired_count=len(expired_keys),
            remaining_count=len(oauth_state_storage),
        )

    return len(expired_keys)


def get_oauth_state(state: str) -> Optional[OAuthState]:
    """Retrieve and validate OAuth state from in-memory storage.

    This helper function retrieves OAuth state by the state parameter and
    validates that it hasn't expired. Returns None if state not found or expired.

    Args:
        state: State parameter from OAuth callback

    Returns:
        Optional[OAuthState]: OAuth state if found and valid, None otherwise

    Side Effects:
        - Logs security events for missing or expired states
        - Does NOT remove expired states (caller should handle cleanup)

    Example:
        >>> oauth_state = get_oauth_state(state_from_callback)
        >>> if oauth_state:
        ...     print(f"Found state for wallet: {oauth_state.wallet_address}")
        ... else:
        ...     print("State not found or expired")
    """
    # Check if state exists
    oauth_state = oauth_state_storage.get(state)

    if not oauth_state:
        logger.warning("x_oauth_state_not_found", state_preview=state[:8] + "...")
        return None

    # Check if state has expired
    now = time.time()
    if now > oauth_state.expires_at:
        age_seconds = int(now - oauth_state.created_at)
        logger.warning(
            "x_oauth_state_expired",
            state_preview=state[:8] + "...",
            age_seconds=age_seconds,
            ttl_seconds=OAUTH_STATE_TTL_SECONDS,
        )
        return None

    return oauth_state
