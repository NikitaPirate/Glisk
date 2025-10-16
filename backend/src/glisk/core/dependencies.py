"""FastAPI dependency injection functions."""

from typing import AsyncGenerator

from fastapi import Request

from glisk.uow import UnitOfWork


async def get_uow(request: Request) -> AsyncGenerator[UnitOfWork, None]:
    """FastAPI dependency for Unit of Work injection.

    Retrieves the UoW factory from app.state and yields a UoW instance.
    The UoW is automatically committed on successful request completion
    or rolled back if an exception occurs.

    Args:
        request: FastAPI request object (provides access to app.state)

    Yields:
        UnitOfWork instance for the request scope

    Example:
        @app.get("/tokens/{token_id}")
        async def get_token(
            token_id: int,
            uow: UnitOfWork = Depends(get_uow)
        ):
            token = await uow.tokens.get_by_token_id(token_id)
            return token
    """
    uow_factory = request.app.state.uow_factory
    async with await uow_factory() as uow:
        yield uow
