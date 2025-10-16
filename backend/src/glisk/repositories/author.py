"""Author repository for GLISK backend.

Provides data access methods for Author entities with case-insensitive wallet lookup.
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from glisk.models.author import Author


class AuthorRepository:
    """Repository for Author entities.

    Methods:
    - get_by_id: Retrieve author by UUID
    - get_by_wallet: Case-insensitive wallet address lookup
    - add: Persist new author
    - list_all: Paginated list of all authors
    """

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session for database operations
        """
        self.session = session

    async def get_by_id(self, author_id: UUID) -> Author | None:
        """Retrieve author by UUID.

        Args:
            author_id: Author's unique identifier

        Returns:
            Author if found, None otherwise
        """
        result = await self.session.execute(select(Author).where(Author.id == author_id))  # type: ignore[arg-type]
        return result.scalar_one_or_none()

    async def get_by_wallet(self, wallet_address: str) -> Author | None:
        """Retrieve author by wallet address (case-insensitive).

        Uses LOWER() comparison to prevent duplicate authors due to case differences.
        Ethereum addresses are case-insensitive (checksum is optional).

        Args:
            wallet_address: Ethereum wallet address (0x...)

        Returns:
            Author if found, None otherwise
        """
        result = await self.session.execute(
            select(Author).where(func.lower(Author.wallet_address) == func.lower(wallet_address))
        )
        return result.scalar_one_or_none()

    async def add(self, author: Author) -> Author:
        """Persist new author to database.

        Args:
            author: Author entity to persist

        Returns:
            Persisted author with generated ID
        """
        self.session.add(author)
        await self.session.flush()
        return author

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[Author]:
        """Retrieve paginated list of all authors.

        Args:
            limit: Maximum number of authors to return (default: 100)
            offset: Number of authors to skip (default: 0)

        Returns:
            List of authors ordered by creation date (newest first)
        """
        result = await self.session.execute(
            select(Author).order_by(Author.created_at.desc()).limit(limit).offset(offset)  # type: ignore[attr-defined]
        )
        return list(result.scalars().all())
