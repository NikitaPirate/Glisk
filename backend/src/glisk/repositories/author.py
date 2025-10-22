"""Author repository for GLISK backend.

Provides data access methods for Author entities with case-insensitive wallet lookup.
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from glisk.models.author import Author
from glisk.models.token import Token


class AuthorRepository:
    """Repository for Author entities.

    Methods:
    - get_by_id: Retrieve author by UUID
    - get_by_wallet: Case-insensitive wallet address lookup
    - add: Persist new author
    - list_all: Paginated list of all authors
    - upsert_author_prompt: Create or update author's prompt text
    - upsert_x_handle: Create or update author's X (Twitter) handle
    - get_author_leaderboard: Top 50 authors ranked by token count
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

    async def upsert_author_prompt(self, wallet_address: str, prompt_text: str) -> Author:
        """Create or update author's prompt text.

        Implements UPSERT logic: creates new author if wallet doesn't exist,
        or updates prompt for existing author. Uses case-insensitive wallet lookup
        to prevent duplicate authors.

        Args:
            wallet_address: Ethereum wallet address (0x + 40 hex chars)
            prompt_text: AI generation prompt (1-1000 characters)

        Returns:
            Author entity (newly created or updated)

        Raises:
            ValueError: If validation fails (invalid wallet format, prompt length, etc.)

        Example:
            >>> author = await repo.upsert_author_prompt(
            ...     "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
            ...     "Surreal neon landscapes with futuristic architecture"
            ... )
        """
        # Check if author already exists (case-insensitive lookup)
        existing_author = await self.get_by_wallet(wallet_address)

        if existing_author:
            # Update existing author's prompt
            existing_author.prompt_text = prompt_text  # Triggers Pydantic validation
            await self.session.flush()
            return existing_author
        else:
            # Create new author with prompt
            new_author = Author(
                wallet_address=wallet_address,  # Triggers wallet validation
                prompt_text=prompt_text,  # Triggers prompt validation
            )
            return await self.add(new_author)

    async def upsert_x_handle(self, wallet_address: str, twitter_handle: str) -> Author:
        """Create or update author's X (Twitter) handle.

        Implements UPSERT logic for X account linking: creates new author if wallet
        doesn't exist, or updates twitter_handle for existing author. Uses case-insensitive
        wallet lookup to prevent duplicate authors.

        This method is called after successful OAuth verification to store the verified
        X username in the author's profile.

        Args:
            wallet_address: Ethereum wallet address (0x + 40 hex chars)
            twitter_handle: Verified X username from OAuth (1-15 chars, alphanumeric + underscores)

        Returns:
            Author entity (newly created or updated)

        Raises:
            ValueError: If validation fails (invalid wallet format, twitter handle format, etc.)

        Example:
            >>> author = await repo.upsert_x_handle(
            ...     "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
            ...     "gliskartist"
            ... )
        """
        # Check if author already exists (case-insensitive lookup)
        existing_author = await self.get_by_wallet(wallet_address)

        if existing_author:
            # Update existing author's twitter handle
            existing_author.twitter_handle = twitter_handle  # Triggers Pydantic validation
            await self.session.flush()
            await self.session.refresh(existing_author)  # Ensure fresh data
            return existing_author
        else:
            # Create new author with twitter handle but no prompt yet
            # Author will need to set prompt before minting NFTs
            new_author = Author(
                wallet_address=wallet_address,  # Triggers wallet validation
                twitter_handle=twitter_handle,  # Triggers twitter handle validation
                prompt_text=None,  # Will be set when author updates their prompt
            )
            return await self.add(new_author)

    async def get_author_leaderboard(self) -> list[tuple[str, int]]:
        """Retrieve top 50 authors ranked by total token count.

        Returns authors sorted by total number of minted tokens (descending),
        with alphabetical tie-breaking by wallet address (ascending).

        Returns:
            List of tuples (wallet_address, total_tokens) for top 50 authors.
            Empty list if no tokens exist.

        Example:
            >>> leaderboard = await repo.get_author_leaderboard()
            >>> # [('0x742d35Cc...', 145), ('0x1234567...', 89), ...]
        """
        # Build aggregation query
        # type: ignore - SQLAlchemy expression types are complex
        stmt = (
            select(
                Author.wallet_address,  # type: ignore[arg-type]
                func.count(Token.id).label("total_tokens"),  # type: ignore[arg-type]
            )
            .select_from(Token)
            .join(Author, Token.author_id == Author.id)  # type: ignore[arg-type]
            .group_by(Author.id, Author.wallet_address)  # type: ignore[arg-type]
            .order_by(
                func.count(Token.id).desc(),  # type: ignore[arg-type]
                Author.wallet_address.asc(),  # type: ignore[attr-defined]
            )
            .limit(50)
        )

        # Execute query
        result = await self.session.execute(stmt)  # type: ignore[arg-type]

        # Return list of tuples (wallet_address, total_tokens)
        return [(row[0], row[1]) for row in result.all()]
