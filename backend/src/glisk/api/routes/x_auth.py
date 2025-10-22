"""X (Twitter) OAuth API endpoints for account linking.

This module implements OAuth 2.0 Authorization Code Flow with PKCE for linking
X (Twitter) accounts to author profiles. Includes wallet signature verification
and CSRF protection via state parameters.

Endpoints:
- POST /api/authors/x/auth/start - Initiate OAuth flow with wallet signature
- GET /api/authors/x/callback - Handle OAuth redirect, exchange code for username
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from web3 import Web3

from glisk.api.dependencies import get_uow_factory
from glisk.core.config import Settings
from glisk.services.wallet_signature import verify_wallet_signature
from glisk.services.x_oauth import XOAuthService, get_oauth_state, oauth_state_storage

logger = structlog.get_logger()
router = APIRouter(prefix="/api/authors/x", tags=["x-oauth"])


# Dependency to get settings
def get_settings() -> Settings:
    """Get application settings."""
    return Settings()  # type: ignore[call-arg]


# Request/Response Models


class XAuthStartRequest(BaseModel):
    """Request model for initiating X OAuth flow with wallet signature."""

    wallet_address: str = Field(
        ...,
        description="Ethereum wallet address (0x + 40 hex characters)",
        min_length=42,
        max_length=42,
    )
    message: str = Field(
        ...,
        description="Message that was signed by the wallet",
        min_length=1,
        max_length=500,
    )
    signature: str = Field(
        ...,
        description="EIP-191 signature hex string",
        min_length=1,
    )


class XAuthStartResponse(BaseModel):
    """Response model for OAuth flow initiation."""

    authorization_url: str = Field(
        ...,
        description="Full OAuth authorization URL to redirect user to X",
    )


# API Endpoints


@router.post("/auth/start", response_model=XAuthStartResponse, status_code=status.HTTP_200_OK)
async def start_x_oauth(
    request: XAuthStartRequest,
    settings: Settings = Depends(get_settings),
    uow_factory=Depends(get_uow_factory),
) -> XAuthStartResponse:
    """Initiate X (Twitter) OAuth flow with wallet signature verification.

    This endpoint generates an OAuth authorization URL for the user to link their
    X account. It requires a valid EIP-191 wallet signature to prove ownership
    before initiating the OAuth flow.

    Security:
    - EIP-191 signature verification required
    - CSRF protection via state parameter
    - PKCE implementation (no client secret needed)
    - Prevents re-linking if already linked (409 Conflict)

    Args:
        request: OAuth start request with wallet address, message, and signature
        settings: Application settings (injected dependency)
        uow_factory: UnitOfWork factory (injected dependency)

    Returns:
        XAuthStartResponse with authorization URL for X

    Raises:
        HTTPException 400: Invalid signature or validation error
        HTTPException 409: X account already linked
        HTTPException 500: Unexpected error

    Example:
        POST /api/authors/x/auth/start
        {
            "wallet_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
            "message": "Link X account for wallet: 0x742d35Cc...",
            "signature": "0x1234567890abcdef..."
        }

        Response 200:
        {
            "authorization_url": "https://x.com/i/oauth2/authorize?..."
        }
    """
    try:
        # Step 1: Normalize wallet address
        try:
            checksummed_address = Web3.to_checksum_address(request.wallet_address)
        except ValueError as e:
            logger.warning(
                "invalid_wallet_address",
                wallet_address=request.wallet_address,
                error=str(e),
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid Ethereum address: {e}",
            )

        # Step 2: Verify wallet signature (proves wallet ownership)
        is_valid_signature = verify_wallet_signature(
            wallet_address=checksummed_address,
            message=request.message,
            signature=request.signature,
        )

        if not is_valid_signature:
            logger.warning(
                "x_oauth_signature_verification_failed",
                wallet_address=checksummed_address,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Signature verification failed. Please ensure you're using the correct wallet."
                ),
            )

        logger.info(
            "x_oauth_signature_verified",
            wallet_address=checksummed_address,
        )

        # Step 3: Check if author already has X account linked (prevent re-linking)
        async with await uow_factory() as uow:
            existing_author = await uow.authors.get_by_wallet(checksummed_address)

            if existing_author and existing_author.twitter_handle:
                logger.warning(
                    "x_oauth_already_linked",
                    wallet_address=checksummed_address,
                    twitter_handle=existing_author.twitter_handle,
                )
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"X account already linked "
                        f"(@{existing_author.twitter_handle}). "
                        "Cannot re-link in MVP."
                    ),
                )

        # Step 4: Initialize OAuth service and generate authorization URL
        oauth_service = XOAuthService(
            client_id=settings.x_client_id,
            client_secret=settings.x_client_secret,
            redirect_uri=settings.x_redirect_uri,
        )

        authorization_url = oauth_service.build_authorization_url(
            wallet_address=checksummed_address
        )

        logger.info(
            "x_oauth_url_generated",
            wallet_address=checksummed_address,
            url_preview=authorization_url[:100] + "...",
        )

        return XAuthStartResponse(authorization_url=authorization_url)

    except HTTPException:
        # Re-raise HTTPExceptions (already have correct status codes)
        raise
    except Exception as e:
        # Unexpected error
        logger.error(
            "unexpected_error_starting_x_oauth",
            wallet_address=request.wallet_address,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate X OAuth. Please try again later.",
        )


@router.get("/callback")
async def x_oauth_callback(
    code: str | None = Query(default=None, description="Authorization code from X"),
    state: str | None = Query(default=None, description="CSRF protection token"),
    error: str | None = Query(default=None, description="Error code if user denied authorization"),
    error_description: str | None = Query(
        default=None, alias="error_description", description="Human-readable error description"
    ),
    settings: Settings = Depends(get_settings),
    uow_factory=Depends(get_uow_factory),
) -> RedirectResponse:
    """Handle OAuth callback from X after user authorization.

    This endpoint receives the OAuth redirect from X, validates the state parameter,
    exchanges the authorization code for an access token, fetches the username from
    X API, and updates the author's profile.

    Security:
    - State parameter validation (CSRF protection)
    - 5-minute TTL for OAuth state
    - Access token discarded immediately after use
    - In-memory state cleanup after processing

    Args:
        code: Authorization code from X (valid 30 seconds)
        state: CSRF protection token (must match in-memory storage)
        error: Error code if user denied authorization
        error_description: Human-readable error description
        settings: Application settings (injected dependency)
        uow_factory: UnitOfWork factory (injected dependency)

    Returns:
        RedirectResponse to frontend success or error page

    Example:
        GET /api/authors/x/callback?code=ABC123&state=XYZ789

        Redirects to:
        http://localhost:5173/profile?tab=author&x_linked=true&username=gliskartist
    """
    frontend_base_url = settings.frontend_url

    # Step 1: Handle user denial or OAuth errors
    if error:
        logger.warning(
            "x_oauth_denied",
            error=error,
            error_description=error_description,
        )
        return RedirectResponse(
            url=f"{frontend_base_url}/profile?tab=author&x_linked=false&error={error}",
            status_code=status.HTTP_302_FOUND,
        )

    # Step 2: Validate required parameters
    if not code or not state:
        logger.error(
            "x_oauth_callback_missing_params",
            has_code=bool(code),
            has_state=bool(state),
        )
        return RedirectResponse(
            url=f"{frontend_base_url}/profile?tab=author&x_linked=false&error=missing_params",
            status_code=status.HTTP_302_FOUND,
        )

    try:
        # Step 3: Validate state parameter (CSRF protection)
        oauth_state = get_oauth_state(state)

        if not oauth_state:
            logger.error(
                "x_oauth_state_invalid",
                state_preview=state[:8] + "...",
            )
            return RedirectResponse(
                url=f"{frontend_base_url}/profile?tab=author&x_linked=false&error=state_mismatch",
                status_code=status.HTTP_302_FOUND,
            )

        logger.info(
            "x_oauth_state_validated",
            wallet_address=oauth_state.wallet_address,
            state_preview=state[:8] + "...",
        )

        # Step 4: Initialize OAuth service and exchange code for token
        oauth_service = XOAuthService(
            client_id=settings.x_client_id,
            client_secret=settings.x_client_secret,
            redirect_uri=settings.x_redirect_uri,
        )

        try:
            # Exchange authorization code for access token
            access_token = await oauth_service.exchange_code_for_token(
                code=code,
                code_verifier=oauth_state.code_verifier,
            )

            # Fetch username from X API
            username = await oauth_service.fetch_username(access_token)

            logger.info(
                "x_username_fetched",
                wallet_address=oauth_state.wallet_address,
                username=username,
            )

        except ValueError as e:
            # Token exchange or username fetch failed
            logger.error(
                "x_oauth_token_exchange_failed",
                wallet_address=oauth_state.wallet_address,
                error=str(e),
            )
            # Cleanup state before redirecting to error
            del oauth_state_storage[state]
            return RedirectResponse(
                url=f"{frontend_base_url}/profile?tab=author&x_linked=false&error=token_exchange_failed",
                status_code=status.HTTP_302_FOUND,
            )

        # Step 5: Update author with X handle
        async with await uow_factory() as uow:
            try:
                author = await uow.authors.upsert_x_handle(
                    wallet_address=oauth_state.wallet_address,
                    twitter_handle=username,
                )

                logger.info(
                    "x_account_linked",
                    wallet_address=oauth_state.wallet_address,
                    twitter_handle=username,
                    author_id=str(author.id),
                )

            except ValueError as e:
                # Validation error from Author model
                logger.error(
                    "x_handle_validation_error",
                    wallet_address=oauth_state.wallet_address,
                    username=username,
                    error=str(e),
                )
                # Cleanup state before redirecting to error
                del oauth_state_storage[state]
                return RedirectResponse(
                    url=f"{frontend_base_url}/profile?tab=author&x_linked=false&error=validation_failed",
                    status_code=status.HTTP_302_FOUND,
                )

        # Step 6: Cleanup OAuth state (one-time use)
        del oauth_state_storage[state]

        logger.info(
            "x_oauth_state_cleaned_up",
            state_preview=state[:8] + "...",
            remaining_states=len(oauth_state_storage),
        )

        # Step 7: Redirect to frontend success page
        return RedirectResponse(
            url=f"{frontend_base_url}/profile?tab=author&x_linked=true&username={username}",
            status_code=status.HTTP_302_FOUND,
        )

    except Exception as e:
        # Unexpected error
        logger.error(
            "unexpected_error_in_x_callback",
            error=str(e),
            error_type=type(e).__name__,
            state_preview=state[:8] + "..." if state else "None",
        )
        # Cleanup state if exists
        if state and state in oauth_state_storage:
            del oauth_state_storage[state]

        return RedirectResponse(
            url=f"{frontend_base_url}/profile?tab=author&x_linked=false&error=unexpected_error",
            status_code=status.HTTP_302_FOUND,
        )
