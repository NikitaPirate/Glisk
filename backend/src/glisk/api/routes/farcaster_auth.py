"""Farcaster account linking API endpoints.

This module implements Farcaster account linking for author profiles using
Sign In With Farcaster (SIWF). Unlike OAuth-based social auth (X/Twitter),
Farcaster uses a frontend-driven flow with Auth Kit that returns both wallet
and Farcaster signatures for backend verification.

Flow:
1. User provides wallet signature (proves wallet ownership)
2. User completes SIWF flow via Auth Kit (proves Farcaster ownership)
3. Backend verifies both signatures
4. Backend links Farcaster handle to author's wallet address

Endpoints:
- POST /api/authors/farcaster/link - Link Farcaster account with dual signature verification
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from web3 import Web3

from glisk.api.dependencies import get_uow_factory, get_w3
from glisk.core.config import Settings
from glisk.services.farcaster_signature import verify_farcaster_signature
from glisk.services.wallet_signature import verify_wallet_signature

logger = structlog.get_logger()
router = APIRouter(prefix="/api/authors/farcaster", tags=["farcaster-auth"])


# Dependency to get settings
def get_settings() -> Settings:
    """Get application settings."""
    return Settings()  # type: ignore[call-arg]


# Request/Response Models


class FarcasterLinkRequest(BaseModel):
    """Request model for linking Farcaster account with dual signature verification."""

    # Wallet signature (proves wallet ownership)
    wallet_address: str = Field(
        ...,
        description="Ethereum wallet address (0x + 40 hex characters)",
        min_length=42,
        max_length=42,
    )
    wallet_message: str = Field(
        ...,
        description="Message that was signed by the wallet",
        min_length=1,
        max_length=500,
    )
    wallet_signature: str = Field(
        ...,
        description="EIP-191 signature hex string from wallet",
        min_length=1,
    )

    # Farcaster SIWF signature (proves Farcaster ownership)
    farcaster_message: str = Field(
        ...,
        description="SIWF message (EIP-4361 format) from Auth Kit",
        min_length=1,
    )
    farcaster_signature: str = Field(
        ...,
        description="SIWF signature hex string from Farcaster wallet",
        min_length=1,
    )

    # Farcaster profile data
    fid: int = Field(
        ...,
        description="Farcaster ID (numeric identifier)",
        ge=1,
    )
    username: str = Field(
        ...,
        description="Farcaster username (without @ prefix)",
        min_length=1,
        max_length=255,
    )


class FarcasterLinkResponse(BaseModel):
    """Response model for successful Farcaster account linking."""

    success: bool = Field(
        ...,
        description="True if Farcaster account was linked successfully",
    )
    username: str = Field(
        ...,
        description="Farcaster username that was linked",
    )
    fid: int = Field(
        ...,
        description="Farcaster ID that was linked",
    )


# API Endpoints


@router.post("/link", response_model=FarcasterLinkResponse, status_code=status.HTTP_200_OK)
async def link_farcaster_account(
    request: FarcasterLinkRequest,
    settings: Settings = Depends(get_settings),
    uow_factory=Depends(get_uow_factory),
    w3: Web3 | None = Depends(get_w3),
) -> FarcasterLinkResponse:
    """Link Farcaster account to author profile with dual signature verification.

    This endpoint verifies both wallet and Farcaster signatures before linking
    a Farcaster account to the author's wallet address. This dual verification
    ensures that:
    1. The user owns the wallet address (wallet signature)
    2. The user owns the Farcaster account (SIWF signature)

    Security:
    - EIP-191/ERC-1271 wallet signature verification
    - SIWF (EIP-4361) signature verification
    - Domain validation for SIWF message
    - No persistent state storage (signatures verified and discarded)

    Args:
        request: Farcaster link request with wallet and SIWF signatures
        settings: Application settings (injected dependency)
        uow_factory: UnitOfWork factory (injected dependency)
        w3: Web3 instance for smart wallet support (injected dependency)

    Returns:
        FarcasterLinkResponse with success status and linked username

    Raises:
        HTTPException 400: Invalid signature or validation error
        HTTPException 500: Unexpected error

    Example:
        POST /api/authors/farcaster/link
        {
            "wallet_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
            "wallet_message": "Link Farcaster account for wallet: 0x742d35Cc...",
            "wallet_signature": "0x1234567890abcdef...",
            "farcaster_message": "example.com wants you to sign in...",
            "farcaster_signature": "0xabcdef1234567890...",
            "fid": 12345,
            "username": "gliskartist"
        }

        Response 200:
        {
            "success": true,
            "username": "gliskartist",
            "fid": 12345
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
        is_valid_wallet_signature = verify_wallet_signature(
            wallet_address=checksummed_address,
            message=request.wallet_message,
            signature=request.wallet_signature,
            w3=w3,  # For ERC-1271 smart wallet support
        )

        if not is_valid_wallet_signature:
            logger.warning(
                "farcaster_link_wallet_signature_failed",
                wallet_address=checksummed_address,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Wallet signature verification failed. "
                    "Please ensure you're using the correct wallet."
                ),
            )

        logger.info(
            "farcaster_link_wallet_signature_verified",
            wallet_address=checksummed_address,
        )

        # Step 3: Verify Farcaster SIWF signature (proves Farcaster ownership)
        is_valid_farcaster_signature = verify_farcaster_signature(
            message=request.farcaster_message,
            signature=request.farcaster_signature,
            expected_domain=settings.farcaster_domain,
            expected_address=None,  # SIWF address may differ from wallet address
        )

        if not is_valid_farcaster_signature:
            logger.warning(
                "farcaster_link_siwf_signature_failed",
                wallet_address=checksummed_address,
                fid=request.fid,
                username=request.username,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Farcaster signature verification failed. "
                    "Please try linking your Farcaster account again."
                ),
            )

        logger.info(
            "farcaster_link_siwf_signature_verified",
            wallet_address=checksummed_address,
            fid=request.fid,
            username=request.username,
        )

        # Step 4: Link Farcaster handle to author profile
        async with await uow_factory() as uow:
            try:
                author = await uow.authors.upsert_farcaster_handle(
                    wallet_address=checksummed_address,
                    farcaster_handle=request.username,
                )

                logger.info(
                    "farcaster_account_linked",
                    wallet_address=checksummed_address,
                    farcaster_handle=request.username,
                    fid=request.fid,
                    author_id=str(author.id),
                )

            except ValueError as e:
                # Validation error from Author model
                logger.error(
                    "farcaster_handle_validation_error",
                    wallet_address=checksummed_address,
                    username=request.username,
                    error=str(e),
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Validation failed: {e}",
                )

        # Step 5: Return success response
        return FarcasterLinkResponse(
            success=True,
            username=request.username,
            fid=request.fid,
        )

    except HTTPException:
        # Re-raise HTTPExceptions (already have correct status codes)
        raise
    except Exception as e:
        # Unexpected error
        logger.error(
            "unexpected_error_linking_farcaster",
            wallet_address=request.wallet_address,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to link Farcaster account. Please try again later.",
        )
