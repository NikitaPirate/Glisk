"""Token entity - NFT with lifecycle status tracking."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class TokenStatus(str, Enum):
    """Token lifecycle status."""

    DETECTED = "detected"
    GENERATING = "generating"
    UPLOADING = "uploading"
    READY = "ready"
    REVEALED = "revealed"
    FAILED = "failed"


class InvalidStateTransition(Exception):
    """Raised when attempting an invalid token state transition."""

    pass


class Token(SQLModel, table=True):
    """Token represents a minted NFT with lifecycle status tracking."""

    __tablename__ = "tokens_s0"  # type: ignore[assignment]

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    token_id: int = Field(unique=True, index=True)
    author_id: UUID = Field(foreign_key="authors.id")
    status: TokenStatus = Field(default=TokenStatus.DETECTED, index=True)
    image_cid: Optional[str] = Field(default=None, max_length=255)
    metadata_cid: Optional[str] = Field(default=None, max_length=255)
    error_data: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Image generation fields (003-003c-image-generation)
    image_url: Optional[str] = Field(default=None)
    generation_attempts: int = Field(default=0, ge=0)
    generation_error: Optional[str] = Field(default=None, max_length=1000)

    # Reveal fields (003-003d-ipfs-reveal)
    reveal_tx_hash: Optional[str] = Field(default=None, max_length=66)

    def mark_generating(self) -> None:
        """Transition from detected to generating.

        Raises:
            InvalidStateTransition: If current status is not detected
        """
        if self.status != TokenStatus.DETECTED:
            raise InvalidStateTransition(
                f"Cannot mark generating from {self.status.value}. Token must be in detected state."
            )
        self.status = TokenStatus.GENERATING

    def mark_uploading(self, image_path: str) -> None:
        """Transition from generating to uploading.

        Args:
            image_path: Path to generated image (stored separately, not on token)

        Raises:
            InvalidStateTransition: If current status is not generating
        """
        if self.status != TokenStatus.GENERATING:
            raise InvalidStateTransition(
                f"Cannot mark uploading from {self.status.value}. "
                "Token must be in generating state."
            )
        # Note: image_path is stored in separate table (ImageGenerationJob)
        self.status = TokenStatus.UPLOADING

    def mark_ready(self, metadata_cid: str) -> None:
        """Transition from uploading to ready.

        Args:
            metadata_cid: IPFS CID of uploaded metadata JSON

        Raises:
            InvalidStateTransition: If current status is not uploading
            ValueError: If metadata_cid is empty
        """
        if self.status != TokenStatus.UPLOADING:
            raise InvalidStateTransition(
                f"Cannot mark ready from {self.status.value}. Token must be in uploading state."
            )
        if not metadata_cid:
            raise ValueError("metadata_cid is required")
        self.metadata_cid = metadata_cid
        self.status = TokenStatus.READY

    def mark_revealed(self, tx_hash: str) -> None:
        """Transition from ready to revealed.

        Args:
            tx_hash: Transaction hash of reveal transaction

        Raises:
            InvalidStateTransition: If current status is not ready
            ValueError: If tx_hash is empty
        """
        if self.status != TokenStatus.READY:
            raise InvalidStateTransition(
                f"Cannot mark revealed from {self.status.value}. Token must be in ready state."
            )
        if not tx_hash:
            raise ValueError("tx_hash is required")
        # Note: tx_hash is stored in reveal_transactions table
        self.status = TokenStatus.REVEALED

    def mark_failed(self, error_dict: dict) -> None:
        """Transition from any non-terminal state to failed.

        Args:
            error_dict: Error details to store in error_data field

        Raises:
            InvalidStateTransition: If current status is already terminal (revealed/failed)
        """
        if self.status in (TokenStatus.REVEALED, TokenStatus.FAILED):
            raise InvalidStateTransition(
                f"Cannot mark failed from terminal state {self.status.value}."
            )
        self.error_data = error_dict
        self.status = TokenStatus.FAILED
