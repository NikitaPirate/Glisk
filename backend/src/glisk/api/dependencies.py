"""FastAPI dependencies for request validation and common operations.

This module provides reusable FastAPI dependencies for:
- Webhook signature validation
- Authentication and authorization
- Request context and logging
"""

from typing import Annotated, Callable

from fastapi import Depends, Header, HTTPException, Request, status
from web3 import Web3

from glisk.core.config import Settings
from glisk.services.blockchain.alchemy_signature import validate_alchemy_signature
from glisk.uow import UnitOfWork


def get_settings() -> Settings:
    """Get application settings instance.

    Returns:
        Settings instance loaded from environment variables.
    """
    return Settings()  # type: ignore[call-arg]  # Pydantic loads from env vars


async def validate_webhook_signature(
    request: Request,
    x_alchemy_signature: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
) -> bytes:
    """Validate Alchemy webhook signature before processing request.

    This dependency performs cryptographic signature validation to ensure that
    webhook requests are genuinely from Alchemy and haven't been tampered with.
    It MUST be used as a dependency for all webhook endpoints.

    The dependency reads the raw request body and validates the HMAC-SHA256
    signature from the X-Alchemy-Signature header. If validation fails, it
    raises a 401 Unauthorized error before any request processing occurs.

    Args:
        request: FastAPI Request object (contains raw body)
        x_alchemy_signature: Signature from X-Alchemy-Signature header
        settings: Application settings (injected via dependency)

    Returns:
        Raw request body bytes (for further processing by the endpoint)

    Raises:
        HTTPException: 401 Unauthorized if signature is missing or invalid

    Security:
        - Validates signature BEFORE any processing logic
        - Uses constant-time comparison to prevent timing attacks
        - Returns raw body to ensure consistency with signature validation

    Example:
        >>> from fastapi import APIRouter
        >>> router = APIRouter()
        >>>
        >>> @router.post("/webhooks/alchemy")
        >>> async def webhook_endpoint(
        ...     raw_body: bytes = Depends(validate_webhook_signature)
        ... ):
        ...     # Signature is validated - safe to process
        ...     payload = json.loads(raw_body)
        ...     return {"status": "success"}
    """
    # Check if signature header is present
    if not x_alchemy_signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing X-Alchemy-Signature header"
        )

    # Read raw request body (before any JSON parsing)
    # This must be the exact bytes received for signature validation
    raw_body = await request.body()

    # Validate signature using HMAC-SHA256
    is_valid = validate_alchemy_signature(
        raw_body=raw_body,
        signature=x_alchemy_signature,
        signing_key=settings.alchemy_webhook_secret,
    )

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature"
        )

    # Signature is valid - return raw body for processing
    return raw_body


def get_uow_factory(request: Request) -> Callable[[], UnitOfWork]:
    """Get UnitOfWork factory from app state.

    Args:
        request: FastAPI Request object (contains app.state)

    Returns:
        UnitOfWork factory function from app lifespan

    Example:
        >>> @router.post("/endpoint")
        >>> async def endpoint(uow_factory=Depends(get_uow_factory)):
        ...     async with await uow_factory() as uow:
        ...         await uow.authors.get_by_wallet(wallet)
    """
    return request.app.state.uow_factory


def get_w3(request: Request) -> Web3 | None:
    """Get Web3 instance from app state for ERC-1271 signature verification.

    Args:
        request: FastAPI Request object (contains app.state)

    Returns:
        Web3 instance for blockchain RPC calls, or None if not initialized.
        Returns None on unsupported networks or connection failure.

    Example:
        >>> @router.post("/endpoint")
        >>> async def endpoint(w3: Web3 | None = Depends(get_w3)):
        ...     if w3:
        ...         # Can make on-chain calls for ERC-1271
        ...         result = contract.functions.someMethod().call()
    """
    return request.app.state.w3
