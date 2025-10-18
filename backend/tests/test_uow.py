"""Unit of Work pattern tests.

Tests focus on transaction management:
- Successful commits persist changes
- Exceptions trigger rollback
- Multiple repository operations are atomic
"""

import pytest

from glisk.models.author import Author
from glisk.models.token import Token, TokenStatus
from glisk.uow import create_uow_factory


@pytest.mark.asyncio
async def test_uow_commits_on_successful_exit(session):
    """Test that UoW commits changes when exiting successfully.

    Changes made within the context should persist after the context exits.
    """
    # Create UoW factory from the test session
    from sqlalchemy.ext.asyncio import async_sessionmaker

    session_factory = async_sessionmaker(
        bind=session.bind,
        expire_on_commit=False,
    )
    uow_factory = create_uow_factory(session_factory)

    author_id = None

    # Make changes within UoW context
    async with await uow_factory() as uow:
        author = Author(
            wallet_address="0x1234567890123456789012345678901234567890",
            prompt_text="Test prompt",
            twitter_handle="testuser",
        )
        uow.authors.session.add(author)
        await uow.authors.session.flush()
        author_id = author.id
        # Context exits successfully - should commit

    # Verify changes persisted in a new UoW context
    async with await uow_factory() as uow:
        found_author = await uow.authors.get_by_id(author_id)
        assert found_author is not None
        assert found_author.wallet_address == "0x1234567890123456789012345678901234567890"


@pytest.mark.asyncio
async def test_uow_rollback_on_exception(session):
    """Test that UoW rolls back changes when an exception occurs.

    If an exception is raised within the context:
    1. Changes should be rolled back
    2. Exception should propagate (not be swallowed)
    """
    # Create UoW factory from the test session
    from sqlalchemy.ext.asyncio import async_sessionmaker

    session_factory = async_sessionmaker(
        bind=session.bind,
        expire_on_commit=False,
    )
    uow_factory = create_uow_factory(session_factory)

    author_wallet = "0x1234567890123456789012345678901234567890"

    # Attempt to make changes but raise exception
    # Use pytest.raises to verify exception propagates correctly
    with pytest.raises(ValueError, match="Simulated error"):
        async with await uow_factory() as uow:
            author = Author(
                wallet_address=author_wallet,
                prompt_text="Test prompt",
                twitter_handle="testuser",
            )
            uow.authors.session.add(author)
            await uow.authors.session.flush()

            # Raise exception - should trigger rollback AND propagate
            raise ValueError("Simulated error")

    # Verify author does not exist (rollback occurred)
    async with await uow_factory() as uow:
        found_author = await uow.authors.get_by_wallet(author_wallet)
        assert found_author is None, "Author should not exist after rollback"


@pytest.mark.asyncio
async def test_uow_provides_all_repositories(session):
    """Test that UoW provides access to all 7 repositories.

    Validates that all repository properties are available.
    """
    # Create UoW factory from the test session
    from sqlalchemy.ext.asyncio import async_sessionmaker

    session_factory = async_sessionmaker(
        bind=session.bind,
        expire_on_commit=False,
    )
    uow_factory = create_uow_factory(session_factory)

    async with await uow_factory() as uow:
        # Verify all repositories are accessible
        assert hasattr(uow, "authors")
        assert hasattr(uow, "tokens")
        assert hasattr(uow, "mint_events")
        assert hasattr(uow, "image_jobs")
        assert hasattr(uow, "ipfs_records")
        assert hasattr(uow, "reveal_txs")
        assert hasattr(uow, "system_state")

        # Verify they're actual repository instances
        assert uow.authors is not None
        assert uow.tokens is not None
        assert uow.mint_events is not None
        assert uow.image_jobs is not None
        assert uow.ipfs_records is not None
        assert uow.reveal_txs is not None
        assert uow.system_state is not None


@pytest.mark.asyncio
async def test_uow_atomic_multi_repository_operation(session):
    """Test that operations across multiple repositories are atomic.

    All changes should commit together or roll back together.
    """
    # Create UoW factory from the test session
    from sqlalchemy.ext.asyncio import async_sessionmaker

    session_factory = async_sessionmaker(
        bind=session.bind,
        expire_on_commit=False,
    )
    uow_factory = create_uow_factory(session_factory)

    author_id = None
    token_id = None

    # Create author and token in same transaction
    async with await uow_factory() as uow:
        # Create author
        author = Author(
            wallet_address="0x1234567890123456789012345678901234567890",
            prompt_text="Test prompt",
            twitter_handle="testuser",
        )
        await uow.authors.add(author)
        author_id = author.id

        # Create token referencing author
        token = Token(
            token_id=1000,
            author_id=author.id,
            status=TokenStatus.DETECTED,
        )
        await uow.tokens.add(token)
        token_id = token.id
        # Both should commit together

    # Verify both exist in new context
    async with await uow_factory() as uow:
        found_author = await uow.authors.get_by_id(author_id)
        found_token = await uow.tokens.get_by_id(token_id)

        assert found_author is not None
        assert found_token is not None
        assert found_token.author_id == found_author.id
