"""pytest fixtures for GLISK backend tests.

Provides:
- postgres_container: Session-scoped testcontainer PostgreSQL instance
- utc_timezone: Autouse fixture enforcing UTC timezone
- session: Function-scoped database session with table truncation
- uow_factory: Function-scoped UnitOfWork factory (Phase 5)
"""

import os
import subprocess
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from testcontainers.postgres import PostgresContainer

from glisk.core.database import setup_db_session


@pytest.fixture(scope="session")
def postgres_container():
    """Provide session-scoped PostgreSQL container with migrations applied.

    Container starts once per test session and is reused across all tests.
    Migrations are applied using subprocess to avoid asyncio event loop conflicts.
    """
    with PostgresContainer(
        image="postgres:17",
        username="test",
        password="test",
        dbname="test_glisk",
    ).with_bind_ports(5432, None) as container:
        # Get database URL
        db_url = container.get_connection_url(driver="psycopg")

        # Apply migrations using subprocess (avoids asyncio.run() conflict)
        # Set DATABASE_URL environment variable for alembic env.py
        env = os.environ.copy()
        env["DATABASE_URL"] = db_url

        # Run alembic upgrade from backend directory
        subprocess.run(
            ["uv", "run", "alembic", "upgrade", "head"],
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )

        yield container


@pytest.fixture(scope="session", autouse=True)
def utc_timezone():
    """Enforce UTC timezone for all tests.

    Autouse fixture ensures TZ=UTC is set before any test runs.
    This prevents timezone-dependent behavior and ensures reproducible tests.
    """
    os.environ["TZ"] = "UTC"
    yield
    # No cleanup needed - environment persists for session


@pytest_asyncio.fixture(scope="function")
async def session(postgres_container) -> AsyncGenerator[AsyncSession, None]:
    """Provide function-scoped database session with table truncation.

    Each test gets a fresh session with empty tables (truncated between tests).
    Migrations are applied automatically on first use.
    """
    # Get database URL from container (migrations already applied in postgres_container fixture)
    # Testcontainers returns postgresql+psycopg:// format which is correct for async SQLAlchemy
    db_url = postgres_container.get_connection_url(driver="psycopg")

    # Create session factory
    session_factory = setup_db_session(db_url, pool_size=5)

    async with session_factory() as session:
        yield session

        # Rollback any uncommitted changes from the test
        # This prevents foreign key violations when truncating tables
        await session.rollback()

        # Truncate all tables for test isolation
        # Order matters: delete from dependent tables first
        # Use text() wrapper for raw SQL (SQLAlchemy 2.0 requirement)
        await session.execute(text("DELETE FROM ipfs_upload_records"))
        await session.execute(text("DELETE FROM image_generation_jobs"))
        await session.execute(text("DELETE FROM reveal_transactions"))
        await session.execute(text("DELETE FROM tokens_s0"))
        await session.execute(text("DELETE FROM mint_events"))
        await session.execute(text("DELETE FROM authors"))
        await session.execute(text("DELETE FROM system_state"))
        await session.commit()


@pytest_asyncio.fixture(scope="function")
async def uow_factory(session: AsyncSession):
    """Provide function-scoped UnitOfWork factory.

    Returns a callable that creates UoW instances using the test session.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from glisk.uow import create_uow_factory

    # Create session factory from the test session's engine
    session_factory = async_sessionmaker(
        bind=session.bind,
        expire_on_commit=False,
    )

    # Return UoW factory
    return create_uow_factory(session_factory)
