"""MintEvent entity - Blockchain mint events for deduplication."""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import field_validator
from sqlmodel import Field, SQLModel


class MintEvent(SQLModel, table=True):
    """MintEvent tracks blockchain mint events for deduplication and recovery."""

    __tablename__ = "mint_events"  # type: ignore[assignment]

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tx_hash: str = Field(max_length=66, index=True)
    log_index: int = Field(index=True)
    block_number: int = Field(index=True)
    block_timestamp: datetime
    token_id: int
    author_wallet: str = Field(max_length=42)  # Prompt author's wallet (003b)
    recipient: str = Field(max_length=42)  # Minter's wallet (003b)
    detected_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("tx_hash")
    @classmethod
    def validate_tx_hash(cls, v: str) -> str:
        """Validate Ethereum transaction hash format (0x + 64 hex characters)."""
        if not v.startswith("0x") or len(v) != 66:
            raise ValueError("Transaction hash must be in format 0x followed by 64 hex characters")
        try:
            int(v[2:], 16)
        except ValueError:
            raise ValueError("Transaction hash must contain valid hexadecimal characters")
        return v

    @field_validator("log_index")
    @classmethod
    def validate_log_index(cls, v: int) -> int:
        """Validate log index is non-negative."""
        if v < 0:
            raise ValueError("Log index must be non-negative")
        return v

    @field_validator("block_number")
    @classmethod
    def validate_block_number(cls, v: int) -> int:
        """Validate block number is positive."""
        if v <= 0:
            raise ValueError("Block number must be positive")
        return v
