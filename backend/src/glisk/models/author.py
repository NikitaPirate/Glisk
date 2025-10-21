"""Author entity - NFT creator with wallet address and AI prompt."""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from eth_utils.address import to_checksum_address
from pydantic import field_validator
from sqlmodel import Field, SQLModel


class Author(SQLModel, table=True):
    """Author represents an NFT creator with wallet address and AI prompt."""

    __tablename__ = "authors"  # type: ignore[assignment]

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    wallet_address: str = Field(max_length=42, unique=True, index=True)
    twitter_handle: Optional[str] = Field(default=None, max_length=255)
    farcaster_handle: Optional[str] = Field(default=None, max_length=255)
    prompt_text: Optional[str] = Field(
        default=None
    )  # TEXT field - None until author sets their prompt
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("wallet_address")
    @classmethod
    def validate_wallet_address(cls, v: str) -> str:
        """Validate and normalize Ethereum wallet address to checksummed format (EIP-55).

        Accepts any valid Ethereum address (case-insensitive) and converts it to
        the checksummed format for consistency across the system.
        """
        if not v.startswith("0x") or len(v) != 42:
            raise ValueError("Wallet address must be in format 0x followed by 40 hex characters")
        try:
            # Verify it's valid hex and normalize to checksummed format
            checksummed = to_checksum_address(v)
            return checksummed
        except ValueError:
            raise ValueError("Wallet address must contain valid hexadecimal characters")

    @field_validator("prompt_text")
    @classmethod
    def validate_prompt_text(cls, v: Optional[str]) -> Optional[str]:
        """Validate AI prompt text length (1-1000 characters) if provided.

        Returns:
            None if v is None, otherwise validated prompt text

        Raises:
            ValueError: If prompt text is not between 1-1000 characters
        """
        if v is None:
            return None
        if len(v) < 1 or len(v) > 1000:
            raise ValueError("Prompt text must be between 1 and 1000 characters")
        return v
