"""Token repository for GLISK backend.

Provides data access methods for Token entities with worker coordination via FOR UPDATE SKIP LOCKED.
"""

from uuid import UUID

from sqlalchemy import select, text
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
        non-overlapping sets of tokens. Orders by created_at ASC to
        process oldest tokens first (FIFO).

        Query explanation:
        - WHERE status = 'detected': Only unprocessed tokens
        - ORDER BY created_at ASC: Process oldest first
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
            .order_by(Token.created_at.asc())  # type: ignore[attr-defined]
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
        - ORDER BY created_at ASC: Process oldest first
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
            .order_by(Token.created_at.asc())  # type: ignore[attr-defined]
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
        - ORDER BY created_at ASC: Process oldest first
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
            .order_by(Token.created_at.asc())  # type: ignore[attr-defined]
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
            List of tokens ordered by created_at timestamp (newest first)
        """
        result = await self.session.execute(
            select(Token)
            .where(Token.author_id == author_id)  # type: ignore[arg-type]
            .order_by(Token.created_at.desc())  # type: ignore[attr-defined]
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
            List of tokens ordered by created_at timestamp (oldest first)
        """
        result = await self.session.execute(
            select(Token)
            .where(Token.status == status)  # type: ignore[arg-type]
            .order_by(Token.created_at.asc())  # type: ignore[attr-defined]
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

    async def update_ipfs_cids(self, token: Token, image_cid: str, metadata_cid: str) -> None:
        """Update token with IPFS CIDs and mark as ready for reveal.

        Args:
            token: Token entity to update
            image_cid: IPFS CID of uploaded image
            metadata_cid: IPFS CID of uploaded metadata JSON

        Raises:
            ValueError: If either CID is empty
        """
        if not image_cid or not metadata_cid:
            raise ValueError("Both image_cid and metadata_cid are required")

        token.image_cid = image_cid
        token.metadata_cid = metadata_cid
        token.status = TokenStatus.READY
        self.session.add(token)
        await self.session.flush()
        await self.session.refresh(token)

    async def mark_revealed(self, token: Token, tx_hash: str) -> None:
        """Mark token as revealed with transaction hash.

        Args:
            token: Token entity to update
            tx_hash: Ethereum transaction hash of reveal operation

        Raises:
            ValueError: If tx_hash is empty
        """
        if not tx_hash:
            raise ValueError("tx_hash is required")

        token.reveal_tx_hash = tx_hash
        token.status = TokenStatus.REVEALED
        self.session.add(token)
        await self.session.flush()
        await self.session.refresh(token)

    async def get_missing_token_ids(self, max_token_id: int, limit: int | None = None) -> list[int]:
        """Retrieve token IDs that exist on-chain but not in database.

        Uses generate_series() to create expected range [1, max_token_id-1],
        then LEFT JOIN to find missing IDs. Token IDs start at 1 (not 0).

        Args:
            max_token_id: Upper bound from contract.nextTokenId() (exclusive)
            limit: Optional cap on number of results (for batching large gaps)

        Returns:
            List of missing token IDs in ascending order

        Example:
            If max_token_id=11 (tokens 1-10 should exist) and DB has [1,2,3,6,7,8],
            returns [4,5,9,10]
        """
        # Build query with generate_series and LEFT JOIN
        query_text = """
            SELECT series.token_id
            FROM generate_series(1, :max_token_id - 1) AS series(token_id)
            LEFT JOIN tokens_s0 ON series.token_id = tokens_s0.token_id
            WHERE tokens_s0.token_id IS NULL
            ORDER BY series.token_id ASC
        """

        if limit is not None:
            query_text += " LIMIT :limit"

        # Execute raw SQL query
        params = {"max_token_id": max_token_id}
        if limit is not None:
            params["limit"] = limit

        result = await self.session.execute(text(query_text), params)
        return [row[0] for row in result.fetchall()]
