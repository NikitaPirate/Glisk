"""SystemState repository for GLISK backend.

Provides data access methods for SystemState key-value store.
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from glisk.models.system_state import SystemState


class SystemStateRepository:
    """Repository for SystemState key-value store.

    Provides UPSERT behavior (INSERT ... ON CONFLICT DO UPDATE) for setting state.
    State values are stored as JSONB and automatically serialized/deserialized.
    """

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session for database operations
        """
        self.session = session

    async def get_state(self, key: str) -> Any | None:
        """Retrieve state value for a key.

        State values are stored as JSONB and automatically deserialized.

        Args:
            key: State key (e.g., "last_processed_block")

        Returns:
            Deserialized state value if found, None otherwise
        """
        result = await self.session.execute(select(SystemState).where(SystemState.key == key))  # type: ignore[arg-type]
        state = result.scalar_one_or_none()
        return state.state_value if state else None

    async def set_state(self, key: str, value: Any) -> None:
        """Set state value for a key (UPSERT).

        Uses INSERT ... ON CONFLICT DO UPDATE to atomically insert or update.
        State values are automatically serialized to JSONB.

        Query explanation:
        - INSERT: Try to insert new row
        - ON CONFLICT (key): If key already exists
        - DO UPDATE: Update existing row with new value and timestamp

        Args:
            key: State key (alphanumeric + underscores only)
            value: State value (must be JSON-serializable)
        """
        # UPSERT using PostgreSQL INSERT ... ON CONFLICT DO UPDATE
        stmt = insert(SystemState).values(
            key=key,
            state_value=value,
            updated_at=datetime.now(timezone.utc),
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["key"],
            set_={
                "state_value": value,
                "updated_at": datetime.now(timezone.utc),
            },
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def delete_state(self, key: str) -> bool:
        """Delete state entry for a key (idempotent).

        Args:
            key: State key to delete

        Returns:
            True if key was deleted, False if key did not exist
        """
        result = await self.session.execute(delete(SystemState).where(SystemState.key == key))  # type: ignore[arg-type]
        await self.session.flush()
        return result.rowcount > 0  # type: ignore[attr-defined]

    async def list_all_keys(self) -> list[str]:
        """Retrieve all state keys.

        Useful for debugging and administrative tasks.

        Returns:
            List of all keys in system state store
        """
        result = await self.session.execute(select(SystemState.key))  # type: ignore[arg-type]
        return list(result.scalars().all())
