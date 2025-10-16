"""add_author_wallet_and_recipient_to_mint_events

Revision ID: ac0fccec2b6e
Revises: 5c7554583d44
Create Date: 2025-10-17 01:49:14.524760

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ac0fccec2b6e"
down_revision: Union[str, Sequence[str], None] = "5c7554583d44"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add author_wallet and recipient fields to mint_events table."""
    # Add author_wallet column (prompt author's wallet address)
    op.add_column(
        "mint_events",
        sa.Column(
            "author_wallet",
            sa.String(length=42),
            nullable=False,
            server_default="0x0000000000000000000000000000000000000000",
        ),
    )
    # Add recipient column (minter's wallet address)
    op.add_column(
        "mint_events",
        sa.Column(
            "recipient",
            sa.String(length=42),
            nullable=False,
            server_default="0x0000000000000000000000000000000000000000",
        ),
    )

    # Remove server defaults after adding columns (only needed for existing rows)
    op.alter_column("mint_events", "author_wallet", server_default=None)
    op.alter_column("mint_events", "recipient", server_default=None)


def downgrade() -> None:
    """Remove author_wallet and recipient fields from mint_events table."""
    op.drop_column("mint_events", "recipient")
    op.drop_column("mint_events", "author_wallet")
