"""IPFSUploadRecord entity - Track IPFS upload attempts."""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class IPFSUploadRecord(SQLModel, table=True):
    """IPFSUploadRecord tracks IPFS upload attempts for images and metadata."""

    __tablename__ = "ipfs_upload_records"  # type: ignore[assignment]

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    token_id: UUID = Field(foreign_key="tokens_s0.id", index=True)
    record_type: str = Field(max_length=50)  # "image" or "metadata"
    cid: Optional[str] = Field(default=None, max_length=255)
    status: str = Field(max_length=50)  # "pending", "uploading", "completed", "failed"
    retry_count: int = Field(default=0)
    error_data: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(default=None)
