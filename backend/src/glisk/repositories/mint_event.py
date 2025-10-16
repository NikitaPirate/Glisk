"""MintEvent repository for GLISK backend.

Provides data access methods for MintEvent entities with duplicate detection.
"""

from uuid import UUID

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from glisk.models.mint_event import MintEvent


class MintEventRepository:
    """Repository for MintEvent entities.

    Provides duplicate detection to prevent processing the same event twice.
    """

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session for database operations
        """
        self.session = session

    async def add(self, mint_event: MintEvent) -> MintEvent:
        """Persist new mint event to database.

        Args:
            mint_event: MintEvent entity to persist

        Returns:
            Persisted mint event with generated ID
        """
        self.session.add(mint_event)
        await self.session.flush()
        return mint_event

    async def exists(self, tx_hash: str, log_index: int) -> bool:
        """Check if mint event already exists (duplicate detection).

        Uses SELECT EXISTS query for efficient existence check.
        The (tx_hash, log_index) pair uniquely identifies a blockchain event.

        Query purpose: Prevent processing duplicate mint events from webhooks
        or recovery processes that may send the same event multiple times.

        Args:
            tx_hash: Transaction hash (0x...)
            log_index: Log index within transaction

        Returns:
            True if event exists, False otherwise
        """
        result = await self.session.execute(
            select(exists().where(MintEvent.tx_hash == tx_hash, MintEvent.log_index == log_index))  # type: ignore[arg-type]
        )
        return result.scalar()  # type: ignore[return-value]

    async def get_by_block_range(self, start_block: int, end_block: int) -> list[MintEvent]:
        """Retrieve mint events within a block range.

        Used for recovery processes that replay events from historical blocks.

        Args:
            start_block: Starting block number (inclusive)
            end_block: Ending block number (inclusive)

        Returns:
            List of mint events ordered by block number and log index
        """
        result = await self.session.execute(
            select(MintEvent)
            .where(
                MintEvent.block_number >= start_block,  # type: ignore[arg-type]
                MintEvent.block_number <= end_block,  # type: ignore[arg-type]
            )
            .order_by(MintEvent.block_number.asc(), MintEvent.log_index.asc())  # type: ignore[attr-defined]
        )
        return list(result.scalars().all())

    async def get_by_id(self, event_id: UUID) -> MintEvent | None:
        """Retrieve mint event by UUID.

        Args:
            event_id: MintEvent's unique identifier

        Returns:
            MintEvent if found, None otherwise
        """
        result = await self.session.execute(select(MintEvent).where(MintEvent.id == event_id))  # type: ignore[arg-type]
        return result.scalar_one_or_none()
