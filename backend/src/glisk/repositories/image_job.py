"""ImageGenerationJob repository for GLISK backend.

Provides data access methods for ImageGenerationJob entities.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from glisk.models.image_job import ImageGenerationJob


class ImageGenerationJobRepository:
    """Repository for ImageGenerationJob entities.

    Tracks image generation attempts for retry and debugging.
    """

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session for database operations
        """
        self.session = session

    async def add(self, job: ImageGenerationJob) -> ImageGenerationJob:
        """Persist new image generation job to database.

        Args:
            job: ImageGenerationJob entity to persist

        Returns:
            Persisted job with generated ID
        """
        self.session.add(job)
        await self.session.flush()
        return job

    async def get_by_id(self, job_id: UUID) -> ImageGenerationJob | None:
        """Retrieve image generation job by UUID.

        Args:
            job_id: Job's unique identifier

        Returns:
            ImageGenerationJob if found, None otherwise
        """
        result = await self.session.execute(
            select(ImageGenerationJob).where(ImageGenerationJob.id == job_id)  # type: ignore[arg-type]
        )
        return result.scalar_one_or_none()

    async def get_by_token(self, token_id: UUID) -> list[ImageGenerationJob]:
        """Retrieve all image generation jobs for a token.

        Returns all attempts (including retries and failures) ordered by creation time.

        Args:
            token_id: Token's unique identifier

        Returns:
            List of jobs ordered by creation time (oldest first)
        """
        result = await self.session.execute(
            select(ImageGenerationJob)
            .where(ImageGenerationJob.token_id == token_id)  # type: ignore[arg-type]
            .order_by(ImageGenerationJob.created_at.asc())  # type: ignore[attr-defined]
        )
        return list(result.scalars().all())

    async def get_latest_by_token(self, token_id: UUID) -> ImageGenerationJob | None:
        """Retrieve the most recent image generation job for a token.

        Useful for checking current generation status without loading all retry attempts.

        Args:
            token_id: Token's unique identifier

        Returns:
            Latest ImageGenerationJob if found, None otherwise
        """
        result = await self.session.execute(
            select(ImageGenerationJob)
            .where(ImageGenerationJob.token_id == token_id)  # type: ignore[arg-type]
            .order_by(ImageGenerationJob.created_at.desc())  # type: ignore[attr-defined]
            .limit(1)
        )
        return result.scalar_one_or_none()
