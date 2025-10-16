"""RevealTransaction entity - Track batch reveal transactions."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from pydantic import field_validator
from sqlalchemy import ARRAY, Column
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlmodel import Field, SQLModel


class RevealTransaction(SQLModel, table=True):
    """RevealTransaction tracks batch reveal transactions for gas optimization."""

    __tablename__ = "reveal_transactions"  # type: ignore[assignment]

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    token_ids: list[UUID] = Field(sa_column=Column(ARRAY(PGUUID(as_uuid=True))))
    tx_hash: Optional[str] = Field(default=None, max_length=66, index=True)
    block_number: Optional[int] = Field(default=None)
    gas_price_gwei: Optional[Decimal] = Field(default=None, max_digits=20, decimal_places=9)
    status: str = Field(max_length=50, index=True)  # "pending", "sent", "confirmed", "failed"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    confirmed_at: Optional[datetime] = Field(default=None)

    @field_validator("token_ids")
    @classmethod
    def validate_token_ids(cls, v: list[UUID]) -> list[UUID]:
        """Validate token_ids array has 1-50 elements (batch size limits)."""
        if not v or len(v) < 1:
            raise ValueError("token_ids must contain at least 1 token")
        if len(v) > 50:
            raise ValueError("token_ids cannot exceed 50 tokens per batch")
        return v

    @field_validator("tx_hash")
    @classmethod
    def validate_tx_hash(cls, v: Optional[str]) -> Optional[str]:
        """Validate Ethereum transaction hash format if present."""
        if v is None:
            return v
        if not v.startswith("0x") or len(v) != 66:
            raise ValueError("Transaction hash must be in format 0x followed by 64 hex characters")
        try:
            int(v[2:], 16)
        except ValueError:
            raise ValueError("Transaction hash must contain valid hexadecimal characters")
        return v
