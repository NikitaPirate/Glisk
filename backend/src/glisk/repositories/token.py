"""Token repository for GLISK backend.

Provides data access methods for Token entities with worker coordination via FOR UPDATE SKIP LOCKED.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from glisk.models.token import Token, TokenStatus


class TokenRepository:
    """Repository for Token entities.

    Methods include worker coordination queries using FOR UPDATE SKIP LOCKED
    to ensure non-overlapping token distribution across concurrent workers.
    """

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session for database operations
        """
        self.session = session

    async def get_by_id(self, token_id: UUID) -> Token | None:
        """Retrieve token by internal UUID.

        Args:
            token_id: Token's unique identifier

        Returns:
            Token if found, None otherwise
        """
        result = await self.session.execute(select(Token).where(Token.id == token_id))  # type: ignore[arg-type]
        return result.scalar_one_or_none()

    async def get_by_token_id(self, token_id: int) -> Token | None:
        """Retrieve token by on-chain token ID.

        Args:
            token_id: On-chain token ID (unique)

        Returns:
            Token if found, None otherwise
        """
        result = await self.session.execute(select(Token).where(Token.token_id == token_id))  # type: ignore[arg-type]
        return result.scalar_one_or_none()

    async def add(self, token: Token) -> Token:
        """Persist new token to database.

        Args:
            token: Token entity to persist

        Returns:
            Persisted token with generated ID
        """
        self.session.add(token)
        await self.session.flush()
        return token

    async def get_pending_for_generation(self, limit: int = 10) -> list[Token]:
        """Retrieve tokens pending image generation with row-level locking.

        Uses FOR UPDATE SKIP LOCKED to ensure concurrent workers receive
        non-overlapping sets of tokens. Orders by mint_timestamp ASC to
        process oldest tokens first (FIFO).

        Query explanation:
        - WHERE status = 'detected': Only unprocessed tokens
        - WHERE generation_attempts < 3: Only tokens with retry budget remaining
        - ORDER BY mint_timestamp ASC: Process oldest first
        - LIMIT: Batch size for worker
        - FOR UPDATE SKIP LOCKED: Lock rows, skip already locked ones

        Args:
            limit: Maximum number of tokens to retrieve (default: 10)

        Returns:
            List of tokens locked for this worker
        """
        # FOR UPDATE SKIP LOCKED ensures worker coordination
        result = await self.session.execute(
            select(Token)
            .where(Token.status == TokenStatus.DETECTED)  # type: ignore[arg-type]
            .where(Token.generation_attempts < 3)  # type: ignore[attr-defined]
            .order_by(Token.mint_timestamp.asc())  # type: ignore[attr-defined]
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return list(result.scalars().all())

    async def update_image_url(self, token: Token, image_url: str) -> None:
        """Update token with generated image URL and mark as ready for upload.

        Args:
            token: Token entity to update
            image_url: Generated image URL from Replicate CDN

        Raises:
            ValueError: If image_url is empty
        """
        if not image_url:
            raise ValueError("image_url cannot be empty")

        token.image_url = image_url
        token.status = TokenStatus.UPLOADING
        self.session.add(token)
        await self.session.flush()
        await self.session.refresh(token)

    async def get_pending_for_upload(self, limit: int = 10) -> list[Token]:
        """Retrieve tokens pending IPFS upload with row-level locking.

        Uses FOR UPDATE SKIP LOCKED for worker coordination.

        Query explanation:
        - WHERE status = 'uploading': Tokens ready for IPFS upload
        - ORDER BY mint_timestamp ASC: Process oldest first
        - LIMIT: Batch size for worker
        - FOR UPDATE SKIP LOCKED: Lock rows, skip already locked ones

        Args:
            limit: Maximum number of tokens to retrieve (default: 10)

        Returns:
            List of tokens locked for this worker
        """
        # FOR UPDATE SKIP LOCKED ensures worker coordination
        result = await self.session.execute(
            select(Token)
            .where(Token.status == TokenStatus.UPLOADING)  # type: ignore[arg-type]
            .order_by(Token.mint_timestamp.asc())  # type: ignore[attr-defined]
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return list(result.scalars().all())

    async def get_ready_for_reveal(self, limit: int = 50) -> list[Token]:
        """Retrieve tokens ready for batch reveal with row-level locking.

        Uses FOR UPDATE SKIP LOCKED for worker coordination.
        Larger batch size (50) for gas-efficient batch reveals.

        Query explanation:
        - WHERE status = 'ready': Tokens with metadata uploaded
        - ORDER BY mint_timestamp ASC: Process oldest first
        - LIMIT: Batch size for reveal transaction
        - FOR UPDATE SKIP LOCKED: Lock rows, skip already locked ones

        Args:
            limit: Maximum number of tokens to retrieve (default: 50)

        Returns:
            List of tokens locked for this worker
        """
        # FOR UPDATE SKIP LOCKED ensures worker coordination
        result = await self.session.execute(
            select(Token)
            .where(Token.status == TokenStatus.READY)  # type: ignore[arg-type]
            .order_by(Token.mint_timestamp.asc())  # type: ignore[attr-defined]
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return list(result.scalars().all())

    async def get_by_author(
        self, author_id: UUID, limit: int = 100, offset: int = 0
    ) -> list[Token]:
        """Retrieve tokens by author with pagination.

        Args:
            author_id: Author's unique identifier
            limit: Maximum number of tokens to return (default: 100)
            offset: Number of tokens to skip (default: 0)

        Returns:
            List of tokens ordered by mint timestamp (newest first)
        """
        result = await self.session.execute(
            select(Token)
            .where(Token.author_id == author_id)  # type: ignore[arg-type]
            .order_by(Token.mint_timestamp.desc())  # type: ignore[attr-defined]
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_by_status(
        self, status: TokenStatus, limit: int = 100, offset: int = 0
    ) -> list[Token]:
        """Retrieve tokens by status with pagination.

        Args:
            status: Token status to filter by
            limit: Maximum number of tokens to return (default: 100)
            offset: Number of tokens to skip (default: 0)

        Returns:
            List of tokens ordered by mint timestamp (oldest first)
        """
        result = await self.session.execute(
            select(Token)
            .where(Token.status == status)  # type: ignore[arg-type]
            .order_by(Token.mint_timestamp.asc())  # type: ignore[attr-defined]
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def mark_failed(self, token: Token, error_message: str) -> None:
        """Mark token as permanently failed with error message.

        Args:
            token: Token entity to update
            error_message: Error description (truncated to 1000 characters)
        """
        token.status = TokenStatus.FAILED
        token.generation_error = error_message[:1000]  # Truncate to 1000 chars
        self.session.add(token)
        await self.session.flush()
        await self.session.refresh(token)

    async def increment_attempts(self, token: Token, error_message: str) -> None:
        """Increment retry counter and reset status for transient failure.

        Args:
            token: Token entity to update
            error_message: Error description (truncated to 1000 characters)
        """
        token.generation_attempts += 1
        token.status = TokenStatus.DETECTED  # Reset to detected for retry
        token.generation_error = error_message[:1000]  # Truncate to 1000 chars
        self.session.add(token)
        await self.session.flush()
        await self.session.refresh(token)
