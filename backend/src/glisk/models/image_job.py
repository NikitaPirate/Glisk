"""ImageGenerationJob entity - Track image generation attempts."""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class ImageGenerationJob(SQLModel, table=True):
    """ImageGenerationJob tracks image generation attempts for retry and debugging."""

    __tablename__ = "image_generation_jobs"  # type: ignore[assignment]

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    token_id: UUID = Field(foreign_key="tokens_s0.id", index=True)
    service: str = Field(max_length=50)  # "replicate" or "selfhosted"
    status: str = Field(max_length=50)  # "pending", "running", "completed", "failed"
    external_job_id: Optional[str] = Field(default=None, max_length=255)
    retry_count: int = Field(default=0)
    error_data: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(default=None)
