"""State transition tests for Token model.

Tests focus on validating the token lifecycle state machine:
- Valid transitions between states
- Invalid transitions are rejected with clear error messages
- Failed state is reachable from any non-terminal state
"""

import pytest

from glisk.models.author import Author
from glisk.models.token import InvalidStateTransition, Token, TokenStatus


@pytest.mark.asyncio
async def test_valid_state_transitions(session):
    """Test all valid state transitions in the token lifecycle.

    Validates the happy path: detected → generating → uploading → ready → revealed
    """
    # Create test author
    author = Author(
        wallet_address="0x1234567890123456789012345678901234567890",
        prompt_text="Test prompt",
        twitter_handle="testuser",
    )
    session.add(author)
    await session.flush()

    # Create token in detected state
    token = Token(
        token_id=1000,
        author_id=author.id,
        status=TokenStatus.DETECTED,
    )
    session.add(token)
    await session.flush()

    # Transition: detected → generating
    token.mark_generating()
    assert token.status == TokenStatus.GENERATING

    # Transition: generating → uploading
    token.mark_uploading(image_path="/tmp/image.png")
    assert token.status == TokenStatus.UPLOADING

    # Transition: uploading → ready
    metadata_cid = "QmTest123"
    token.mark_ready(metadata_cid=metadata_cid)
    assert token.status == TokenStatus.READY
    assert token.metadata_cid == metadata_cid

    # Transition: ready → revealed
    tx_hash = "0xabcdef1234567890"
    token.mark_revealed(tx_hash=tx_hash)
    assert token.status == TokenStatus.REVEALED


@pytest.mark.asyncio
async def test_invalid_state_transition_raises_exception(session):
    """Test that invalid state transitions raise descriptive exceptions.

    Example: Cannot go directly from detected to revealed without intermediate steps.
    """
    # Create test author
    author = Author(
        wallet_address="0x1234567890123456789012345678901234567890",
        prompt_text="Test prompt",
        twitter_handle="testuser",
    )
    session.add(author)
    await session.flush()

    # Create token in detected state
    token = Token(
        token_id=1000,
        author_id=author.id,
        status=TokenStatus.DETECTED,
    )
    session.add(token)
    await session.flush()

    # Attempt invalid transition: detected → revealed
    with pytest.raises(InvalidStateTransition) as exc_info:
        token.mark_revealed(tx_hash="0xabc")

    # Verify error message is descriptive
    error_message = str(exc_info.value)
    assert "detected" in error_message.lower()
    assert "ready" in error_message.lower()
    assert "revealed" in error_message.lower()


@pytest.mark.asyncio
async def test_mark_failed_from_any_non_terminal_state(session):
    """Test that tokens can transition to failed from any non-terminal state.

    This is important for error handling - failures can occur at any stage.
    """
    # Create test author
    author = Author(
        wallet_address="0x1234567890123456789012345678901234567890",
        prompt_text="Test prompt",
        twitter_handle="testuser",
    )
    session.add(author)
    await session.flush()

    error_dict = {"error": "test_error", "details": "Something went wrong"}

    # Test from each non-terminal state
    token_id_counter = 1000
    for initial_status in [
        TokenStatus.DETECTED,
        TokenStatus.GENERATING,
        TokenStatus.UPLOADING,
        TokenStatus.READY,
    ]:
        token = Token(
            token_id=token_id_counter,
            author_id=author.id,
            status=initial_status,
        )
        session.add(token)
        await session.flush()

        # Should be able to mark as failed
        token.mark_failed(error_dict=error_dict)
        assert token.status == TokenStatus.FAILED
        assert token.error_data == error_dict

        token_id_counter += 1

    # Commit all tokens at once
    await session.commit()


@pytest.mark.asyncio
async def test_cannot_transition_from_terminal_states(session):
    """Test that terminal states (revealed, failed) cannot transition.

    Once a token reaches a terminal state, it should stay there.
    """
    # Create test author
    author = Author(
        wallet_address="0x1234567890123456789012345678901234567890",
        prompt_text="Test prompt",
        twitter_handle="testuser",
    )
    session.add(author)
    await session.flush()

    # Test revealed state (terminal)
    token_revealed = Token(
        token_id=1000,
        author_id=author.id,
        status=TokenStatus.REVEALED,
    )
    session.add(token_revealed)

    # Cannot mark failed from revealed
    with pytest.raises(InvalidStateTransition):
        token_revealed.mark_failed(error_dict={"error": "test"})

    # Test failed state (terminal)
    token_failed = Token(
        token_id=1001,
        author_id=author.id,
        status=TokenStatus.FAILED,
    )
    session.add(token_failed)

    # Cannot mark generating from failed
    with pytest.raises(InvalidStateTransition):
        token_failed.mark_generating()
