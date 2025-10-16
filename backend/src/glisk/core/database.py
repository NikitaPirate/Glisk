"""Database session factory setup."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def setup_db_session(db_url: str, pool_size: int = 200) -> async_sessionmaker[AsyncSession]:
    """Create async database session factory.

    Args:
        db_url: PostgreSQL connection URL (postgresql+psycopg://...)
        pool_size: Maximum number of connections in the pool (default: 200)

    Returns:
        Async session factory for creating database sessions
    """
    engine = create_async_engine(
        db_url,
        pool_size=pool_size,
        max_overflow=0,  # No overflow beyond pool_size
        pool_pre_ping=True,  # Verify connections before using
        echo=False,  # Don't log SQL queries (use structlog instead)
    )

    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,  # Prevent lazy loading issues after commit
    )

    return session_factory
