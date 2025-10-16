"""Unit of Work pattern for GLISK backend.

Provides transaction management with automatic commit/rollback and access to all repositories.
"""

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from glisk.repositories.author import AuthorRepository
from glisk.repositories.image_job import ImageGenerationJobRepository
from glisk.repositories.ipfs_record import IPFSUploadRecordRepository
from glisk.repositories.mint_event import MintEventRepository
from glisk.repositories.reveal_tx import RevealTransactionRepository
from glisk.repositories.system_state import SystemStateRepository
from glisk.repositories.token import TokenRepository

logger = structlog.get_logger()


class UnitOfWork:
    """Unit of Work pattern implementation.

    Manages database transactions and provides access to all repositories.
    Use as async context manager for automatic commit/rollback.

    Example:
        async with uow_factory() as uow:
            author = await uow.authors.get_by_wallet(wallet)
            token = await uow.tokens.get_by_id(token_id)
            token.mark_generating()
            # Automatically commits on successful exit
            # Automatically rolls back on exception
    """

    def __init__(self, session: AsyncSession):
        """Initialize UnitOfWork with database session.

        Args:
            session: SQLAlchemy async session for database operations
        """
        self.session = session

        # Instantiate all repositories with the session
        self.authors = AuthorRepository(session)
        self.tokens = TokenRepository(session)
        self.mint_events = MintEventRepository(session)
        self.image_jobs = ImageGenerationJobRepository(session)
        self.ipfs_records = IPFSUploadRecordRepository(session)
        self.reveal_txs = RevealTransactionRepository(session)
        self.system_state = SystemStateRepository(session)

    async def __aenter__(self):
        """Enter async context manager.

        Returns:
            self: UnitOfWork instance with all repositories available
        """
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager with automatic commit/rollback.

        Args:
            exc_type: Exception type if raised
            exc_val: Exception value if raised
            exc_tb: Exception traceback if raised

        Returns:
            False: Always re-raise exceptions after rollback
        """
        if exc_type is None:
            # No exception - commit changes
            await self.session.commit()
            logger.info("transaction.committed")
        else:
            # Exception occurred - rollback changes
            await self.session.rollback()
            logger.info("transaction.rolled_back", exc_type=exc_type.__name__)

        # Return False to re-raise the exception (if any)
        # This ensures errors are not silently swallowed
        return False


def create_uow_factory(session_factory: async_sessionmaker[AsyncSession]):
    """Create a factory function that produces UnitOfWork instances.

    Args:
        session_factory: SQLAlchemy async session factory

    Returns:
        Callable that creates UnitOfWork instances from new sessions

    Example:
        session_factory = setup_db_session(db_url, pool_size=200)
        uow_factory = create_uow_factory(session_factory)

        async with await uow_factory() as uow:
            await uow.authors.add(author)
    """

    async def _create_uow():
        """Create a new UnitOfWork instance with a new session."""
        session = session_factory()
        return UnitOfWork(session)

    return _create_uow
