"""Token recovery tests for GLISK backend.

Tests cover:
- TokenRepository.get_missing_token_ids() for various gap scenarios
- TokenRecoveryService.get_next_token_id() with mocked Web3
- Full recovery flow integration test with testcontainer PostgreSQL
"""

from unittest.mock import Mock, patch

import pytest
from web3.exceptions import BadFunctionCallOutput

from glisk.models.author import Author
from glisk.models.token import Token, TokenStatus
from glisk.repositories.token import TokenRepository
from glisk.services.blockchain.token_recovery import TokenRecoveryService
from glisk.services.exceptions import BlockchainConnectionError, ContractNotFoundError

# ====================
# T015: Unit tests for TokenRepository.get_missing_token_ids()
# ====================


@pytest.mark.asyncio
async def test_get_missing_token_ids_empty_database(session):
    """Test get_missing_token_ids() with empty database.

    Scenario:
    1. Database has no tokens
    2. max_token_id=11 (tokens 1-10 should exist)
    3. Should return [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    """
    token_repo = TokenRepository(session)

    missing = await token_repo.get_missing_token_ids(max_token_id=11)

    assert missing == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    assert len(missing) == 10


@pytest.mark.asyncio
async def test_get_missing_token_ids_partial_gaps(session):
    """Test get_missing_token_ids() with partial gaps.

    Scenario:
    1. Create tokens [1, 2, 3, 6, 7, 8]
    2. max_token_id=11 (tokens 1-10 should exist)
    3. Should return [4, 5, 9, 10]
    """
    # Create author first (required foreign key)
    author = Author(
        wallet_address="0x1234567890123456789012345678901234567890",
        prompt_text="Test prompt for recovery testing",
    )
    session.add(author)
    await session.commit()

    # Create tokens with gaps
    for token_id in [1, 2, 3, 6, 7, 8]:
        token = Token(
            token_id=token_id,
            author_id=author.id,
            status=TokenStatus.DETECTED,
            generation_attempts=0,
        )
        session.add(token)
    await session.commit()

    token_repo = TokenRepository(session)
    missing = await token_repo.get_missing_token_ids(max_token_id=11)

    assert missing == [4, 5, 9, 10]
    assert len(missing) == 4


@pytest.mark.asyncio
async def test_get_missing_token_ids_no_gaps(session):
    """Test get_missing_token_ids() with no gaps.

    Scenario:
    1. Create tokens [1, 2, 3, 4, 5]
    2. max_token_id=6 (tokens 1-5 should exist)
    3. Should return empty list
    """
    # Create author
    author = Author(
        wallet_address="0x1234567890123456789012345678901234567890",
        prompt_text="Test prompt for recovery testing",
    )
    session.add(author)
    await session.commit()

    # Create all tokens (no gaps)
    for token_id in [1, 2, 3, 4, 5]:
        token = Token(
            token_id=token_id,
            author_id=author.id,
            status=TokenStatus.DETECTED,
            generation_attempts=0,
        )
        session.add(token)
    await session.commit()

    token_repo = TokenRepository(session)
    missing = await token_repo.get_missing_token_ids(max_token_id=6)

    assert missing == []
    assert len(missing) == 0


@pytest.mark.asyncio
async def test_get_missing_token_ids_single_missing(session):
    """Test get_missing_token_ids() with single missing token.

    Scenario:
    1. Create tokens [1, 2, 4, 5]
    2. max_token_id=6 (tokens 1-5 should exist)
    3. Should return [3]
    """
    # Create author
    author = Author(
        wallet_address="0x1234567890123456789012345678901234567890",
        prompt_text="Test prompt for recovery testing",
    )
    session.add(author)
    await session.commit()

    # Create tokens with single gap
    for token_id in [1, 2, 4, 5]:
        token = Token(
            token_id=token_id,
            author_id=author.id,
            status=TokenStatus.DETECTED,
            generation_attempts=0,
        )
        session.add(token)
    await session.commit()

    token_repo = TokenRepository(session)
    missing = await token_repo.get_missing_token_ids(max_token_id=6)

    assert missing == [3]
    assert len(missing) == 1


@pytest.mark.asyncio
async def test_get_missing_token_ids_with_limit(session):
    """Test get_missing_token_ids() with limit parameter.

    Scenario:
    1. Database has no tokens
    2. max_token_id=101 (tokens 1-100 should exist)
    3. limit=10
    4. Should return first 10 missing tokens [1, 2, ..., 10]
    """
    token_repo = TokenRepository(session)

    missing = await token_repo.get_missing_token_ids(max_token_id=101, limit=10)

    assert missing == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    assert len(missing) == 10


@pytest.mark.asyncio
async def test_get_missing_token_ids_large_gap(session):
    """Test get_missing_token_ids() with large gap (1000+ tokens).

    Scenario:
    1. Database has no tokens
    2. max_token_id=1001 (tokens 1-1000 should exist)
    3. Should return all 1000 missing tokens
    4. Performance: Should complete in <1 second
    """
    import time

    token_repo = TokenRepository(session)

    start = time.time()
    missing = await token_repo.get_missing_token_ids(max_token_id=1001)
    duration = time.time() - start

    assert len(missing) == 1000
    assert missing[0] == 1
    assert missing[-1] == 1000
    assert duration < 1.0, f"Query took {duration:.2f}s, should be <1s"


# ====================
# T016: Unit tests for TokenRecoveryService.get_next_token_id()
# ====================


@pytest.mark.asyncio
async def test_get_next_token_id_success():
    """Test get_next_token_id() with successful RPC call.

    Scenario:
    1. Mock contract.functions.nextTokenId().call() to return 11
    2. Should return 11 without retries
    """
    # Mock Web3 and contract
    mock_w3 = Mock()
    mock_w3.is_connected.return_value = True

    mock_contract = Mock()
    mock_contract.functions.nextTokenId.return_value.call.return_value = 11

    # Patch contract initialization
    with patch("glisk.services.blockchain.token_recovery.Web3") as MockWeb3:
        MockWeb3.to_checksum_address.return_value = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"

        service = TokenRecoveryService(
            w3=mock_w3,
            contract_address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
        )
        service.contract = mock_contract  # Override with mock

        result = await service.get_next_token_id()

        assert result == 11
        mock_contract.functions.nextTokenId.return_value.call.assert_called_once()


@pytest.mark.asyncio
async def test_get_next_token_id_contract_not_found():
    """Test get_next_token_id() with contract not found error.

    Scenario:
    1. Mock contract call to raise BadFunctionCallOutput
    2. Should raise ContractNotFoundError immediately (no retries)
    """
    mock_w3 = Mock()
    mock_w3.is_connected.return_value = True

    mock_contract = Mock()
    mock_contract.functions.nextTokenId.return_value.call.side_effect = BadFunctionCallOutput(
        "Contract not found"
    )

    with patch("glisk.services.blockchain.token_recovery.Web3") as MockWeb3:
        MockWeb3.to_checksum_address.return_value = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"

        service = TokenRecoveryService(
            w3=mock_w3,
            contract_address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
        )
        service.contract = mock_contract

        with pytest.raises(ContractNotFoundError):
            await service.get_next_token_id()

        # Should not retry for contract errors
        assert mock_contract.functions.nextTokenId.return_value.call.call_count == 1


@pytest.mark.asyncio
async def test_get_next_token_id_retry_logic():
    """Test get_next_token_id() retry logic with transient errors.

    Scenario:
    1. First 2 calls raise ConnectionError (transient)
    2. Third call succeeds and returns 11
    3. Should retry and eventually succeed
    """
    mock_w3 = Mock()
    mock_w3.is_connected.return_value = True

    mock_contract = Mock()
    mock_contract.functions.nextTokenId.return_value.call.side_effect = [
        ConnectionError("Network timeout"),
        ConnectionError("Network timeout"),
        11,  # Success on 3rd attempt
    ]

    with patch("glisk.services.blockchain.token_recovery.Web3") as MockWeb3:
        MockWeb3.to_checksum_address.return_value = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"

        service = TokenRecoveryService(
            w3=mock_w3,
            contract_address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
        )
        service.contract = mock_contract

        result = await service.get_next_token_id()

        assert result == 11
        assert mock_contract.functions.nextTokenId.return_value.call.call_count == 3


@pytest.mark.asyncio
async def test_get_next_token_id_retry_exhausted():
    """Test get_next_token_id() when all retries exhausted.

    Scenario:
    1. All 3 attempts raise ConnectionError
    2. Should raise BlockchainConnectionError after 3 attempts
    """
    mock_w3 = Mock()
    mock_w3.is_connected.return_value = True

    mock_contract = Mock()
    mock_contract.functions.nextTokenId.return_value.call.side_effect = ConnectionError(
        "Network timeout"
    )

    with patch("glisk.services.blockchain.token_recovery.Web3") as MockWeb3:
        MockWeb3.to_checksum_address.return_value = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"

        service = TokenRecoveryService(
            w3=mock_w3,
            contract_address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
        )
        service.contract = mock_contract

        with pytest.raises(BlockchainConnectionError):
            await service.get_next_token_id()

        assert mock_contract.functions.nextTokenId.return_value.call.call_count == 3


# ====================
# T017: Integration test for full recovery flow
# ====================


@pytest.mark.asyncio
async def test_full_recovery_flow_integration(uow_factory):
    """Integration test for full token recovery flow.

    Scenario:
    1. Seed database with tokens [1, 2, 3, 6, 7, 8] and default author
    2. Mock contract.nextTokenId() to return 11 (tokens 1-10 should exist)
    3. Mock contract.tokenPromptAuthor() to return author addresses
    4. Run recovery
    5. Verify tokens [4, 5, 9, 10] created with status=DETECTED
    6. Verify all tokens have correct author_id from contract
    """
    # Create authors
    async with await uow_factory() as uow:
        author1 = Author(
            wallet_address="0x1111111111111111111111111111111111111111",
            prompt_text="Test prompt for author 1",
        )
        author2 = Author(
            wallet_address="0x2222222222222222222222222222222222222222",
            prompt_text="Test prompt for author 2",
        )
        await uow.authors.add(author1)
        await uow.authors.add(author2)
        await uow.session.flush()

        # Create existing tokens (gaps at 4, 5, 9, 10)
        for token_id in [1, 2, 3, 6, 7, 8]:
            token = Token(
                token_id=token_id,
                author_id=author1.id,
                status=TokenStatus.DETECTED,
                generation_attempts=0,
            )
            await uow.tokens.add(token)

    # Mock Web3 and contract
    mock_w3 = Mock()
    mock_w3.is_connected.return_value = True

    mock_contract = Mock()
    # Mock nextTokenId() to return 11 (tokens 1-10 should exist)
    mock_contract.functions.nextTokenId.return_value.call.return_value = 11

    # Mock tokenPromptAuthor() to return different authors for missing tokens
    def mock_token_prompt_author(token_id):
        mock_call = Mock()
        if token_id in [4, 5]:
            mock_call.call.return_value = "0x1111111111111111111111111111111111111111"
        else:  # tokens 9, 10
            mock_call.call.return_value = "0x2222222222222222222222222222222222222222"
        return mock_call

    mock_contract.functions.tokenPromptAuthor.side_effect = mock_token_prompt_author

    # Initialize recovery service with mocked contract
    with patch("glisk.services.blockchain.token_recovery.Web3") as MockWeb3:
        MockWeb3.to_checksum_address.return_value = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"

        service = TokenRecoveryService(
            w3=mock_w3,
            contract_address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
        )
        service.contract = mock_contract

        # Run recovery
        async with await uow_factory() as uow:
            result = await service.recover_missing_tokens(uow=uow)

        # Verify result
        assert result.total_on_chain == 10
        assert result.missing_count == 4
        assert result.recovered_count == 4
        assert result.skipped_duplicate_count == 0
        assert len(result.errors) == 0

        # Verify tokens were created
        async with await uow_factory() as uow:
            token4 = await uow.tokens.get_by_token_id(4)
            token5 = await uow.tokens.get_by_token_id(5)
            token9 = await uow.tokens.get_by_token_id(9)
            token10 = await uow.tokens.get_by_token_id(10)

            assert token4 is not None
            assert token5 is not None
            assert token9 is not None
            assert token10 is not None

            # Verify status
            assert token4.status == TokenStatus.DETECTED
            assert token5.status == TokenStatus.DETECTED
            assert token9.status == TokenStatus.DETECTED
            assert token10.status == TokenStatus.DETECTED

            # Verify author IDs match mocked contract responses
            assert token4.author_id == author1.id
            assert token5.author_id == author1.id
            assert token9.author_id == author2.id
            assert token10.author_id == author2.id


@pytest.mark.asyncio
async def test_recovery_with_no_gaps(uow_factory):
    """Test recovery when no tokens are missing.

    Scenario:
    1. Seed database with tokens [1, 2, 3, 4]
    2. Mock contract.nextTokenId() to return 5 (tokens 1-4 should exist)
    3. Run recovery
    4. Verify no tokens recovered (no gaps detected)
    """
    # Create author
    async with await uow_factory() as uow:
        author = Author(
            wallet_address="0x1111111111111111111111111111111111111111",
            prompt_text="Test prompt for no gaps test",
        )
        await uow.authors.add(author)
        await uow.session.flush()

        # Create all tokens (no gaps)
        for token_id in [1, 2, 3, 4]:
            token = Token(
                token_id=token_id,
                author_id=author.id,
                status=TokenStatus.DETECTED,
                generation_attempts=0,
            )
            await uow.tokens.add(token)

    # Mock Web3 and contract
    mock_w3 = Mock()
    mock_w3.is_connected.return_value = True

    mock_contract = Mock()
    mock_contract.functions.nextTokenId.return_value.call.return_value = 5
    mock_contract.functions.tokenPromptAuthor.return_value.call.return_value = (
        "0x1111111111111111111111111111111111111111"
    )

    with patch("glisk.services.blockchain.token_recovery.Web3") as MockWeb3:
        MockWeb3.to_checksum_address.return_value = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"

        service = TokenRecoveryService(
            w3=mock_w3,
            contract_address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
        )
        service.contract = mock_contract

        # Run recovery - should detect no gaps
        async with await uow_factory() as uow:
            result = await service.recover_missing_tokens(uow=uow)

        # Verify result shows no missing tokens
        assert result.missing_count == 0
        assert result.recovered_count == 0
        assert result.skipped_duplicate_count == 0
        assert result.total_on_chain == 4
        assert result.total_in_db == 4
