"""IPFSUploadRecord repository for GLISK backend.

Provides data access methods for IPFSUploadRecord entities.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from glisk.models.ipfs_record import IPFSUploadRecord


class IPFSUploadRecordRepository:
    """Repository for IPFSUploadRecord entities.

    Tracks IPFS upload attempts for images and metadata.
    """

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session for database operations
        """
        self.session = session

    async def add(self, record: IPFSUploadRecord) -> IPFSUploadRecord:
        """Persist new IPFS upload record to database.

        Args:
            record: IPFSUploadRecord entity to persist

        Returns:
            Persisted record with generated ID
        """
        self.session.add(record)
        await self.session.flush()
        return record

    async def get_by_id(self, record_id: UUID) -> IPFSUploadRecord | None:
        """Retrieve IPFS upload record by UUID.

        Args:
            record_id: Record's unique identifier

        Returns:
            IPFSUploadRecord if found, None otherwise
        """
        result = await self.session.execute(
            select(IPFSUploadRecord).where(IPFSUploadRecord.id == record_id)  # type: ignore[arg-type]
        )
        return result.scalar_one_or_none()

    async def get_by_token(
        self, token_id: UUID, record_type: str | None = None
    ) -> list[IPFSUploadRecord]:
        """Retrieve IPFS upload records for a token.

        Returns all upload attempts (including retries and failures) ordered by creation time.
        Optionally filter by record_type (image or metadata).

        Args:
            token_id: Token's unique identifier
            record_type: Optional filter for record type ("image" or "metadata")

        Returns:
            List of records ordered by creation time (oldest first)
        """
        query = select(IPFSUploadRecord).where(IPFSUploadRecord.token_id == token_id)  # type: ignore[arg-type]

        if record_type is not None:
            query = query.where(IPFSUploadRecord.record_type == record_type)  # type: ignore[arg-type]

        query = query.order_by(IPFSUploadRecord.created_at.asc())  # type: ignore[attr-defined]

        result = await self.session.execute(query)
        return list(result.scalars().all())
