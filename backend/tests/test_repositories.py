"""Repository layer tests for GLISK backend.

Tests focus on complex logic per constitution:
- Case-insensitive wallet lookup
- Mint event duplicate detection
- System state UPSERT behavior

Simple CRUD operations are not tested (trust SQLAlchemy/PostgreSQL).

Note: FOR UPDATE SKIP LOCKED worker coordination is validated in production
via real concurrent workers. Testing this properly requires actual concurrent
database connections (threads/processes), which is beyond pytest-asyncio scope.
"""

from datetime import datetime, timezone

import pytest

from glisk.models.author import Author
from glisk.models.mint_event import MintEvent
from glisk.repositories.author import AuthorRepository
from glisk.repositories.mint_event import MintEventRepository
from glisk.repositories.system_state import SystemStateRepository


@pytest.mark.asyncio
async def test_case_insensitive_wallet_lookup(session):
    """Test AuthorRepository.get_by_wallet is case-insensitive.

    Scenario:
    1. Create author with wallet "0xABC..." (mixed case)
    2. Query with "0xabc..." (lowercase)
    3. Assert author is found (LOWER() comparison)

    This prevents duplicate authors due to case differences.
    """
    # Create author with mixed-case wallet
    author = Author(
        wallet_address="0xABCdef1234567890123456789012345678901234",
        prompt_text="Test prompt",
        twitter_handle="testuser",
    )
    session.add(author)
    await session.commit()

    # Query with lowercase wallet
    author_repo = AuthorRepository(session)
    found = await author_repo.get_by_wallet("0xabcdef1234567890123456789012345678901234")

    # Assertions
    assert found is not None, "Author should be found with case-insensitive search"
    assert found.id == author.id
    assert found.wallet_address == author.wallet_address


@pytest.mark.asyncio
async def test_mint_event_duplicate_detection(session):
    """Test MintEventRepository.exists detects duplicate events.

    Scenario:
    1. Create mint event with (tx_hash, log_index)
    2. Call exists(tx_hash, log_index)
    3. Assert returns True (duplicate detected)
    4. Call exists with different log_index
    5. Assert returns False (not a duplicate)

    This prevents processing the same event twice.
    """
    # Create mint event
    event = MintEvent(
        tx_hash="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        log_index=42,
        block_number=12345,
        block_timestamp=datetime.now(timezone.utc),
        token_id=100,
        author_wallet="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
        recipient="0x1234567890123456789012345678901234567890",
        detected_at=datetime.now(timezone.utc),
    )
    session.add(event)
    await session.commit()

    # Check duplicate detection
    mint_repo = MintEventRepository(session)

    # Same tx_hash + log_index should exist
    exists = await mint_repo.exists(
        tx_hash="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        log_index=42,
    )
    assert exists is True, "Duplicate event should be detected"

    # Different log_index should not exist
    exists_different = await mint_repo.exists(
        tx_hash="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        log_index=99,
    )
    assert exists_different is False, "Non-duplicate event should return False"


@pytest.mark.asyncio
async def test_system_state_upsert(session):
    """Test SystemStateRepository.set_state UPSERT behavior.

    Scenario:
    1. Call set_state("key", "value1")
    2. Call set_state("key", "value2")
    3. Call get_state("key")
    4. Assert returns "value2" (INSERT ON CONFLICT DO UPDATE worked)

    This validates the key-value store implementation.
    """
    state_repo = SystemStateRepository(session)

    # First insert
    await state_repo.set_state("test_key", {"count": 1, "status": "active"})
    await session.commit()

    # Verify first value
    value1 = await state_repo.get_state("test_key")
    assert value1 == {"count": 1, "status": "active"}

    # Update (UPSERT)
    await state_repo.set_state("test_key", {"count": 2, "status": "updated"})
    await session.commit()

    # Verify updated value
    value2 = await state_repo.get_state("test_key")
    assert value2 == {"count": 2, "status": "updated"}

    # Verify only one row exists
    all_keys = await state_repo.list_all_keys()
    assert "test_key" in all_keys
    assert len([k for k in all_keys if k == "test_key"]) == 1
