"""SystemState entity - Singleton key-value store for operational state."""

from datetime import datetime

from pydantic import field_validator
from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class SystemState(SQLModel, table=True):
    """SystemState is a singleton key-value store for operational state."""

    __tablename__ = "system_state"  # type: ignore[assignment]

    key: str = Field(primary_key=True, max_length=255)
    state_value: dict = Field(sa_column=Column(JSON))
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("key")
    @classmethod
    def validate_key(cls, v: str) -> str:
        """Validate key is alphanumeric + underscores only."""
        if not v.replace("_", "").isalnum():
            raise ValueError("Key must be alphanumeric with underscores only")
        return v
