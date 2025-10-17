"""RevealTransaction repository for GLISK backend.

Provides data access methods for RevealTransaction entities.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from glisk.models.reveal_tx import RevealTransaction


class RevealTransactionRepository:
    """Repository for RevealTransaction entities.

    Tracks batch reveal transactions for gas optimization.
    """

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session for database operations
        """
        self.session = session

    async def add(self, reveal_tx: RevealTransaction) -> RevealTransaction:
        """Persist new reveal transaction to database.

        Args:
            reveal_tx: RevealTransaction entity to persist

        Returns:
            Persisted reveal transaction with generated ID
        """
        self.session.add(reveal_tx)
        await self.session.flush()
        return reveal_tx

    async def get_by_id(self, tx_id: UUID) -> RevealTransaction | None:
        """Retrieve reveal transaction by UUID.

        Args:
            tx_id: Transaction's unique identifier

        Returns:
            RevealTransaction if found, None otherwise
        """
        result = await self.session.execute(
            select(RevealTransaction).where(RevealTransaction.id == tx_id)  # type: ignore[arg-type]
        )
        return result.scalar_one_or_none()

    async def get_by_tx_hash(self, tx_hash: str) -> RevealTransaction | None:
        """Retrieve reveal transaction by blockchain transaction hash.

        Args:
            tx_hash: Transaction hash (0x...)

        Returns:
            RevealTransaction if found, None otherwise
        """
        result = await self.session.execute(
            select(RevealTransaction).where(RevealTransaction.tx_hash == tx_hash)  # type: ignore[arg-type]
        )
        return result.scalar_one_or_none()

    async def get_by_status(
        self, status: str, limit: int = 100, offset: int = 0
    ) -> list[RevealTransaction]:
        """Retrieve reveal transactions by status with pagination.

        Args:
            status: Transaction status ("pending", "sent", "confirmed", "failed")
            limit: Maximum number of transactions to return (default: 100)
            offset: Number of transactions to skip (default: 0)

        Returns:
            List of transactions ordered by creation time (oldest first)
        """
        result = await self.session.execute(
            select(RevealTransaction)
            .where(RevealTransaction.status == status)  # type: ignore[arg-type]
            .order_by(RevealTransaction.created_at.asc())  # type: ignore[attr-defined]
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_pending(self, limit: int = 100) -> list[RevealTransaction]:
        """Retrieve pending reveal transactions.

        Convenience method for get_by_status("pending").
        Used by reveal worker to find transactions that need confirmation.

        Args:
            limit: Maximum number of transactions to return (default: 100)

        Returns:
            List of pending transactions ordered by creation time (oldest first)
        """
        return await self.get_by_status("pending", limit=limit)

    async def mark_confirmed(
        self,
        tx_hash: str,
        block_number: int,
        gas_used: int,
    ) -> None:
        """Mark reveal transaction as confirmed.

        Updates transaction status and stores blockchain confirmation details.

        Args:
            tx_hash: Transaction hash (0x...)
            block_number: Block number where transaction was confirmed
            gas_used: Gas used by transaction
        """
        from datetime import datetime

        result = await self.session.execute(
            select(RevealTransaction).where(RevealTransaction.tx_hash == tx_hash)  # type: ignore[arg-type]
        )
        tx_record = result.scalar_one_or_none()

        if tx_record:
            tx_record.status = "confirmed"
            tx_record.block_number = block_number
            tx_record.confirmed_at = datetime.utcnow()
            self.session.add(tx_record)
            await self.session.flush()

    async def mark_failed(
        self,
        tx_hash: str,
        error_message: str,
    ) -> None:
        """Mark reveal transaction as failed.

        Updates transaction status and stores error message.

        Args:
            tx_hash: Transaction hash (0x...)
            error_message: Error message describing failure
        """
        result = await self.session.execute(
            select(RevealTransaction).where(RevealTransaction.tx_hash == tx_hash)  # type: ignore[arg-type]
        )
        tx_record = result.scalar_one_or_none()

        if tx_record:
            tx_record.status = "failed"
            self.session.add(tx_record)
            await self.session.flush()
