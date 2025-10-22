"""Author profile management API endpoints.

This module implements REST endpoints for author profile management including:
- POST /api/authors/prompt - Create or update author's AI generation prompt with
  signature verification
- GET /api/authors/{wallet_address} - Check if author has configured a prompt
- GET /api/authors/{wallet_address}/tokens - Get paginated list of tokens authored by wallet

All prompt updates require EIP-191 wallet signature verification to prove wallet ownership.
"""

from datetime import datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from web3 import Web3

from glisk.api.dependencies import get_uow_factory, get_w3
from glisk.services.wallet_signature import verify_wallet_signature

logger = structlog.get_logger()
router = APIRouter(prefix="/api/authors", tags=["authors"])


# Request/Response Models


class UpdatePromptRequest(BaseModel):
    """Request model for updating author's prompt with signature verification."""

    wallet_address: str = Field(
        ...,
        description="Ethereum wallet address (0x + 40 hex characters)",
        min_length=42,
        max_length=42,
    )
    prompt_text: str = Field(
        ...,
        description="AI generation prompt text",
        min_length=1,
        max_length=1000,
    )
    message: str = Field(
        ...,
        description="Signed message (should match what was presented to user)",
    )
    signature: str = Field(
        ...,
        description="EIP-191 signature hex string",
    )

    @field_validator("wallet_address")
    @classmethod
    def validate_wallet_address(cls, v: str) -> str:
        """Validate and normalize Ethereum wallet address."""
        if not v.startswith("0x") or len(v) != 42:
            raise ValueError("Wallet address must be 0x followed by 40 hex characters")
        try:
            # Normalize to checksummed address
            return Web3.to_checksum_address(v)
        except ValueError as e:
            raise ValueError(f"Invalid Ethereum address: {e}")


class UpdatePromptResponse(BaseModel):
    """Response model for prompt update operations.

    Note: Does NOT include prompt_text for security (prompts are write-only via API).
    """

    success: bool = Field(
        ...,
        description="True if prompt was saved successfully",
    )
    has_prompt: bool = Field(
        ...,
        description="True if author now has a prompt configured",
    )


class AuthorStatusResponse(BaseModel):
    """Response model for author status queries."""

    has_prompt: bool = Field(
        ...,
        description="True if author has configured a prompt, False otherwise",
    )
    twitter_handle: str | None = Field(
        default=None,
        description="X (Twitter) username if author has linked their account, None otherwise",
    )


class TokenDTO(BaseModel):
    """Data Transfer Object for token information in API responses."""

    token_id: int = Field(
        ...,
        description="On-chain token ID",
    )
    status: str = Field(
        ...,
        description=(
            "Token lifecycle status (detected, generating, uploading, ready, revealed, failed)"
        ),
    )
    image_cid: str | None = Field(
        default=None,
        description="IPFS CID for image (null if not yet uploaded)",
    )
    metadata_cid: str | None = Field(
        default=None,
        description="IPFS CID for metadata JSON (null if not yet uploaded)",
    )
    image_url: str | None = Field(
        default=None,
        description="Replicate URL for generated image (null if not yet generated)",
    )
    generation_attempts: int = Field(
        ...,
        description="Number of image generation attempts",
    )
    generation_error: str | None = Field(
        default=None,
        description="Error message if generation failed (null otherwise)",
    )
    reveal_tx_hash: str | None = Field(
        default=None,
        description="Transaction hash for reveal (null if not yet revealed)",
    )
    created_at: datetime = Field(
        ...,
        description="Timestamp when token record was created (UTC)",
    )


class TokensResponse(BaseModel):
    """Response model for paginated tokens list."""

    tokens: list[TokenDTO] = Field(
        ...,
        description="Array of token objects for current page",
    )
    total: int = Field(
        ...,
        description="Total number of tokens matching query (across all pages)",
    )
    offset: int = Field(
        ...,
        description="Number of tokens skipped (pagination offset)",
    )
    limit: int = Field(
        ...,
        description="Maximum number of tokens per page",
    )


class AuthorLeaderboardEntry(BaseModel):
    """Response model for a single leaderboard entry."""

    author_address: str = Field(
        ...,
        description="Checksummed Ethereum wallet address",
        min_length=42,
        max_length=42,
    )
    total_tokens: int = Field(
        ...,
        description="Total number of tokens minted by author",
        ge=1,
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "author_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
                "total_tokens": 145,
            }
        }
    }


# API Endpoints


@router.post("/prompt", response_model=UpdatePromptResponse, status_code=status.HTTP_200_OK)
async def update_author_prompt(
    request: UpdatePromptRequest,
    uow_factory=Depends(get_uow_factory),
    w3: Web3 | None = Depends(get_w3),
) -> UpdatePromptResponse:
    """Create or update author's AI generation prompt with signature verification.

    This endpoint allows creators to set or update their AI generation prompt by
    providing a valid EIP-191 wallet signature. The signature proves wallet ownership
    without requiring an on-chain transaction.

    Security:
    - Signature verification required (EIP-191)
    - Prompt text is never returned via API (write-only)
    - Case-insensitive wallet lookup prevents duplicates

    Args:
        request: Prompt update request with wallet address, prompt, and signature
        uow_factory: UnitOfWork factory (injected dependency)

    Returns:
        UpdatePromptResponse with success=True and has_prompt=True

    Raises:
        HTTPException 400: Invalid signature or validation error
        HTTPException 500: Database error

    Example:
        POST /api/authors/prompt
        {
            "wallet_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
            "prompt_text": "Surreal neon landscapes with futuristic architecture",
            "message": "Update GLISK prompt for wallet: 0x742d35Cc...",
            "signature": "0x1234567890abcdef..."
        }

        Response 200:
        {
            "success": true,
            "has_prompt": true
        }
    """
    try:
        # Step 1: Verify wallet signature (proves wallet ownership)
        is_valid_signature = verify_wallet_signature(
            wallet_address=request.wallet_address,
            message=request.message,
            signature=request.signature,
            w3=w3,  # For ERC-1271 smart wallet support
        )

        if not is_valid_signature:
            logger.warning(
                "signature_verification_failed",
                wallet_address=request.wallet_address,
                message_preview=request.message[:50],
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Signature verification failed. Please ensure you're using the correct wallet."
                ),
            )

        # Log successful signature verification
        logger.info(
            "signature_verification_success",
            wallet_address=request.wallet_address,
        )

        # Step 2: Update or create author with prompt (UoW handles transaction)
        async with await uow_factory() as uow:
            try:
                # Upsert author prompt (creates new or updates existing)
                author = await uow.authors.upsert_author_prompt(
                    wallet_address=request.wallet_address,
                    prompt_text=request.prompt_text,
                )

                # Transaction will commit automatically on context exit
                # Log successful update
                logger.info(
                    "author_prompt_updated",
                    wallet_address=request.wallet_address,
                    author_id=str(author.id),
                    prompt_length=len(request.prompt_text),
                )

                return UpdatePromptResponse(
                    success=True,
                    has_prompt=True,
                )

            except ValueError as e:
                # Validation error from Author model (prompt length, wallet format, etc.)
                logger.warning(
                    "author_validation_error",
                    wallet_address=request.wallet_address,
                    error=str(e),
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e),
                )

    except HTTPException:
        # Re-raise HTTPExceptions (already have correct status codes)
        raise
    except Exception as e:
        # Unexpected error (database connection, etc.)
        logger.error(
            "unexpected_error_updating_prompt",
            wallet_address=request.wallet_address,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update author prompt. Please try again later.",
        )


@router.get(
    "/leaderboard", response_model=list[AuthorLeaderboardEntry], status_code=status.HTTP_200_OK
)
async def get_author_leaderboard(
    uow_factory=Depends(get_uow_factory),
) -> list[AuthorLeaderboardEntry]:
    """Get ranked list of top 50 authors by token count.

    Returns authors sorted by total number of minted tokens (descending),
    with alphabetical tie-breaking by wallet address (ascending). Designed
    for landing page discovery of popular creators.

    Always returns 200 OK with empty array if no tokens exist.

    Security:
    - No authentication required (public read)
    - Read-only query (no state mutations)
    - Performance optimized with SQL aggregation

    Returns:
        List of AuthorLeaderboardEntry (max 50 authors, ordered by token count DESC)

    Example:
        GET /api/authors/leaderboard

        Response 200 (authors with tokens):
        [
            {
                "author_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
                "total_tokens": 145
            },
            {
                "author_address": "0x1234567890AbcdEF1234567890aBcdef12345678",  # gitleaks:allow
                "total_tokens": 89
            }
        ]

        Response 200 (no tokens):
        []
    """
    try:
        # Log leaderboard request
        logger.debug("leaderboard_request")

        # Query leaderboard data
        async with await uow_factory() as uow:
            # Get top 50 authors by token count
            leaderboard_data = await uow.authors.get_author_leaderboard()

            # Convert tuples to DTOs
            leaderboard_entries = [
                AuthorLeaderboardEntry(
                    author_address=wallet_address,
                    total_tokens=total_tokens,
                )
                for wallet_address, total_tokens in leaderboard_data
            ]

            # Log successful retrieval
            logger.info(
                "leaderboard_retrieved",
                total_authors=len(leaderboard_entries),
            )

            return leaderboard_entries

    except Exception as e:
        # Unexpected error (database connection, etc.)
        logger.error(
            "unexpected_error_getting_leaderboard",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve author leaderboard. Please try again later.",
        )


@router.get(
    "/{wallet_address}", response_model=AuthorStatusResponse, status_code=status.HTTP_200_OK
)
async def get_author_status(
    wallet_address: str,
    uow_factory=Depends(get_uow_factory),
) -> AuthorStatusResponse:
    """Check if author has configured a prompt and X account (read-only status check).

    This endpoint returns whether an author has set up their AI generation prompt
    and if they have linked their X (Twitter) account. It does NOT return the prompt
    text itself (prompts are write-only via API).

    Always returns 200 OK, even if author doesn't exist (returns has_prompt=false).

    Security:
    - No authentication required (public read)
    - Prompt text is never exposed (only boolean status)
    - Case-insensitive wallet lookup

    Args:
        wallet_address: Ethereum wallet address (0x + 40 hex chars, case-insensitive)
        uow_factory: UnitOfWork factory (injected dependency)

    Returns:
        AuthorStatusResponse with has_prompt boolean and twitter_handle (if linked)

    Example:
        GET /api/authors/0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0  # gitleaks:allow

        Response 200 (author exists with X account):
        {
            "has_prompt": true,
            "twitter_handle": "gliskartist"
        }

        Response 200 (author exists without X account):
        {
            "has_prompt": true,
            "twitter_handle": null
        }

        Response 200 (author doesn't exist):
        {
            "has_prompt": false,
            "twitter_handle": null
        }
    """
    try:
        # Normalize wallet address to checksummed format
        try:
            checksummed_address = Web3.to_checksum_address(wallet_address)
        except ValueError:
            # Invalid address format - treat as non-existent author
            logger.warning(
                "invalid_wallet_address_format",
                wallet_address=wallet_address,
            )
            return AuthorStatusResponse(has_prompt=False)

        # Query author by wallet (case-insensitive)
        async with await uow_factory() as uow:
            author = await uow.authors.get_by_wallet(checksummed_address)

            if author is None:
                # Author not found - return has_prompt=false, no twitter_handle (not 404)
                logger.debug(
                    "author_not_found",
                    wallet_address=checksummed_address,
                )
                return AuthorStatusResponse(has_prompt=False, twitter_handle=None)
            else:
                # Author exists with prompt - return status and twitter_handle if linked
                logger.debug(
                    "author_status_retrieved",
                    wallet_address=checksummed_address,
                    author_id=str(author.id),
                    twitter_handle=author.twitter_handle,
                )
                return AuthorStatusResponse(
                    has_prompt=True,
                    twitter_handle=author.twitter_handle,
                )

    except Exception as e:
        # Unexpected error (database connection, etc.)
        logger.error(
            "unexpected_error_getting_author_status",
            wallet_address=wallet_address,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve author status. Please try again later.",
        )


@router.get(
    "/{wallet_address}/tokens", response_model=TokensResponse, status_code=status.HTTP_200_OK
)
async def get_author_tokens(
    wallet_address: str,
    offset: int = Query(default=0, ge=0, description="Number of tokens to skip (pagination)"),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum tokens per page (1-100)"),
    uow_factory=Depends(get_uow_factory),
) -> TokensResponse:
    """Get paginated list of tokens authored by a wallet address.

    Returns all tokens where the wallet address is the prompt author. Results are
    ordered by creation timestamp (newest first) with pagination support.

    Always returns 200 OK with empty array if author not found or has no tokens.

    Security:
    - No authentication required (public read)
    - Wallet address normalized to checksum format
    - Invalid addresses treated as non-existent (returns empty results)

    Args:
        wallet_address: Ethereum wallet address (0x + 40 hex chars, case-insensitive)
        offset: Number of tokens to skip (default: 0, min: 0)
        limit: Maximum tokens per page (default: 20, min: 1, max: 100)
        uow_factory: UnitOfWork factory (injected dependency)

    Returns:
        TokensResponse with tokens array, total count, offset, and limit

    Example:
        GET /api/authors/0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0/tokens?offset=0&limit=20

        Response 200 (author has tokens):
        {
            "tokens": [
                {
                    "token_id": 123,
                    "status": "revealed",
                    "image_cid": "QmXyz...",
                    "metadata_cid": "QmAbc...",
                    "image_url": "https://replicate.delivery/...",
                    "generation_attempts": 1,
                    "generation_error": null,
                    "reveal_tx_hash": "0x1234...",
                    "created_at": "2025-10-22T12:34:56Z"
                }
            ],
            "total": 45,
            "offset": 0,
            "limit": 20
        }

        Response 200 (author not found or no tokens):
        {
            "tokens": [],
            "total": 0,
            "offset": 0,
            "limit": 20
        }
    """
    try:
        # Step 1: Normalize and validate wallet address
        try:
            checksummed_address = Web3.to_checksum_address(wallet_address)
        except ValueError:
            # Invalid address format - treat as non-existent author (return empty, not 400)
            logger.warning(
                "invalid_wallet_format",
                wallet_address=wallet_address,
                offset=offset,
                limit=limit,
            )
            return TokensResponse(tokens=[], total=0, offset=offset, limit=limit)

        # Step 2: Query author and tokens
        async with await uow_factory() as uow:
            # Get author by wallet address
            author = await uow.authors.get_by_wallet(checksummed_address)

            if author is None:
                # Author not found - return empty results (not 404)
                logger.debug(
                    "author_not_found",
                    wallet_address=checksummed_address,
                    offset=offset,
                    limit=limit,
                )
                return TokensResponse(tokens=[], total=0, offset=offset, limit=limit)

            # Get paginated tokens with total count
            tokens, total = await uow.tokens.get_tokens_by_author_paginated(
                author_id=author.id,
                offset=offset,
                limit=limit,
            )

            # Convert Token entities to TokenDTO
            token_dtos = [
                TokenDTO(
                    token_id=token.token_id,
                    status=token.status.value,
                    image_cid=token.image_cid,
                    metadata_cid=token.metadata_cid,
                    image_url=token.image_url,
                    generation_attempts=token.generation_attempts,
                    generation_error=token.generation_error,
                    reveal_tx_hash=token.reveal_tx_hash,
                    created_at=token.created_at,
                )
                for token in tokens
            ]

            # Log successful retrieval
            logger.info(
                "tokens_retrieved",
                wallet_address=checksummed_address,
                author_id=str(author.id),
                total=total,
                returned=len(token_dtos),
                offset=offset,
                limit=limit,
            )

            return TokensResponse(
                tokens=token_dtos,
                total=total,
                offset=offset,
                limit=limit,
            )

    except HTTPException:
        # Re-raise HTTPExceptions (already have correct status codes)
        raise
    except Exception as e:
        # Unexpected error (database connection, etc.)
        logger.error(
            "unexpected_error_getting_author_tokens",
            wallet_address=wallet_address,
            offset=offset,
            limit=limit,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve author tokens. Please try again later.",
        )
