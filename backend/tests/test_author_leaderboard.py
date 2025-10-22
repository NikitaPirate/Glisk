"""Integration tests for author leaderboard feature.

Tests author leaderboard endpoint including:
- GET /api/authors/leaderboard - Returns ranked list of authors by token count

Uses TDD approach: tests written first, should FAIL before implementation.
"""

from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from glisk.app import app
from glisk.models.author import Author
from glisk.models.token import Token, TokenStatus
from glisk.repositories.author import AuthorRepository


@pytest_asyncio.fixture
async def test_client(uow_factory):
    """Provide AsyncClient for testing API endpoints with database access."""
    # Inject uow_factory into app.state for dependency injection
    app.state.uow_factory = uow_factory

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def seed_authors_and_tokens(session):
    """Seed test database with authors and tokens for leaderboard tests.

    Creates 3 authors with different token counts:
    - Author A (0x742d...): 5 tokens
    - Author B (0x1234...): 3 tokens
    - Author C (0xAbCd...): 1 token
    """
    # Create authors
    author_a = Author(
        id=uuid4(),
        wallet_address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
        prompt_text="Neon cyberpunk cityscapes",
    )
    author_b = Author(
        id=uuid4(),
        wallet_address="0x1234567890AbcdEF1234567890aBcdef12345678",
        prompt_text="Abstract geometric patterns",
    )
    author_c = Author(
        id=uuid4(),
        wallet_address="0xAbCdEf1234567890aBcDeF1234567890AbCdEf12",
        prompt_text="Surreal dreamscapes",
    )

    session.add(author_a)
    session.add(author_b)
    session.add(author_c)
    await session.commit()

    # Create tokens (Author A: 5, Author B: 3, Author C: 1)
    tokens = [
        # Author A tokens
        Token(id=uuid4(), token_id=1, author_id=author_a.id, status=TokenStatus.REVEALED),
        Token(id=uuid4(), token_id=2, author_id=author_a.id, status=TokenStatus.REVEALED),
        Token(id=uuid4(), token_id=3, author_id=author_a.id, status=TokenStatus.REVEALED),
        Token(id=uuid4(), token_id=4, author_id=author_a.id, status=TokenStatus.REVEALED),
        Token(id=uuid4(), token_id=5, author_id=author_a.id, status=TokenStatus.REVEALED),
        # Author B tokens
        Token(id=uuid4(), token_id=6, author_id=author_b.id, status=TokenStatus.REVEALED),
        Token(id=uuid4(), token_id=7, author_id=author_b.id, status=TokenStatus.REVEALED),
        Token(id=uuid4(), token_id=8, author_id=author_b.id, status=TokenStatus.REVEALED),
        # Author C tokens
        Token(id=uuid4(), token_id=9, author_id=author_c.id, status=TokenStatus.REVEALED),
    ]

    for token in tokens:
        session.add(token)
    await session.commit()

    return {
        "author_a": author_a,
        "author_b": author_b,
        "author_c": author_c,
    }


@pytest.mark.asyncio
async def test_get_leaderboard_basic(session, seed_authors_and_tokens):
    """Test AuthorRepository.get_author_leaderboard returns correct order.

    Scenario:
    1. Seed database with 3 authors (5, 3, 1 tokens)
    2. Call get_author_leaderboard()
    3. Assert returns descending order by total_tokens
    4. Assert correct wallet addresses and counts

    This verifies the aggregation query works correctly.
    """
    # Arrange
    authors = seed_authors_and_tokens
    author_repo = AuthorRepository(session)

    # Act
    leaderboard = await author_repo.get_author_leaderboard()

    # Assert - should return 3 authors in descending order
    assert len(leaderboard) == 3, "Should return 3 authors"

    # First place: Author A with 5 tokens
    assert leaderboard[0][0] == authors["author_a"].wallet_address
    assert leaderboard[0][1] == 5

    # Second place: Author B with 3 tokens
    assert leaderboard[1][0] == authors["author_b"].wallet_address
    assert leaderboard[1][1] == 3

    # Third place: Author C with 1 token
    assert leaderboard[2][0] == authors["author_c"].wallet_address
    assert leaderboard[2][1] == 1


@pytest.mark.asyncio
async def test_get_leaderboard_tie_breaking(session):
    """Test AuthorRepository.get_author_leaderboard alphabetical tie-breaking.

    Scenario:
    1. Create 3 authors with equal token counts (2 each)
    2. Call get_author_leaderboard()
    3. Assert secondary sort is alphabetical by wallet_address

    This verifies deterministic ordering when token counts are equal.
    """
    # Arrange - create 3 authors with wallet addresses in non-alphabetical order
    author_z = Author(
        id=uuid4(),
        # Will be last alphabetically
        wallet_address="0xZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ",
        prompt_text="Test Z",
    )
    author_a = Author(
        id=uuid4(),
        # Will be first alphabetically
        wallet_address="0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
        prompt_text="Test A",
    )
    author_m = Author(
        id=uuid4(),
        # Will be middle alphabetically
        wallet_address="0xMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM",
        prompt_text="Test M",
    )

    session.add(author_z)
    session.add(author_a)
    session.add(author_m)
    await session.commit()

    # Create 2 tokens for each author
    tokens = [
        Token(id=uuid4(), token_id=1, author_id=author_z.id, status=TokenStatus.REVEALED),
        Token(id=uuid4(), token_id=2, author_id=author_z.id, status=TokenStatus.REVEALED),
        Token(id=uuid4(), token_id=3, author_id=author_a.id, status=TokenStatus.REVEALED),
        Token(id=uuid4(), token_id=4, author_id=author_a.id, status=TokenStatus.REVEALED),
        Token(id=uuid4(), token_id=5, author_id=author_m.id, status=TokenStatus.REVEALED),
        Token(id=uuid4(), token_id=6, author_id=author_m.id, status=TokenStatus.REVEALED),
    ]
    for token in tokens:
        session.add(token)
    await session.commit()

    # Act
    author_repo = AuthorRepository(session)
    leaderboard = await author_repo.get_author_leaderboard()

    # Assert - should be alphabetical when counts are equal
    assert len(leaderboard) == 3
    assert leaderboard[0][0] == "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    assert leaderboard[0][1] == 2
    assert leaderboard[1][0] == "0xMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM"
    assert leaderboard[1][1] == 2
    assert leaderboard[2][0] == "0xZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ"
    assert leaderboard[2][1] == 2


@pytest.mark.asyncio
async def test_get_leaderboard_limit(session):
    """Test AuthorRepository.get_author_leaderboard enforces 50 author limit.

    Scenario:
    1. Create 60 authors with 1 token each
    2. Call get_author_leaderboard()
    3. Assert returns exactly 50 authors (not 60)

    This verifies the LIMIT 50 clause works.
    """
    # Arrange - create 60 authors with 1 token each
    for i in range(60):
        # Create author with unique wallet address (valid checksummed format)
        # Use a base address and modify the last 2 characters
        base = "0x" + "A" * 38  # 0xAA...AA (38 A's)
        wallet = base + f"{i:02X}"  # Append 2-digit hex (00-3B for 0-59)
        author = Author(
            id=uuid4(),
            wallet_address=wallet,
            prompt_text=f"Test author {i}",
        )
        session.add(author)
        await session.flush()

        # Create 1 token for this author
        token = Token(
            id=uuid4(),
            token_id=i + 1,
            author_id=author.id,
            status=TokenStatus.REVEALED,
        )
        session.add(token)

    await session.commit()

    # Act
    author_repo = AuthorRepository(session)
    leaderboard = await author_repo.get_author_leaderboard()

    # Assert - should return exactly 50 authors
    assert len(leaderboard) == 50, "Should enforce limit of 50 authors"

    # All returned authors should have 1 token
    for wallet_address, total_tokens in leaderboard:
        assert total_tokens == 1


@pytest.mark.asyncio
async def test_get_leaderboard_empty(session):
    """Test AuthorRepository.get_author_leaderboard handles empty database.

    Scenario:
    1. Start with empty database (no authors, no tokens)
    2. Call get_author_leaderboard()
    3. Assert returns empty list

    This verifies graceful handling of edge case.
    """
    # Arrange - empty database (conftest.py truncates tables between tests)
    author_repo = AuthorRepository(session)

    # Act
    leaderboard = await author_repo.get_author_leaderboard()

    # Assert - should return empty list
    assert leaderboard == [], "Should return empty list for empty database"


@pytest.mark.asyncio
async def test_api_leaderboard_endpoint(test_client, seed_authors_and_tokens):
    """Test GET /api/authors/leaderboard endpoint returns correct JSON.

    Scenario:
    1. Seed database with 3 authors
    2. Call GET /api/authors/leaderboard
    3. Assert 200 OK status
    4. Assert correct JSON schema (array of objects with author_address, total_tokens)
    5. Assert descending order by total_tokens

    This verifies the API endpoint works end-to-end.
    """
    # Arrange
    authors = seed_authors_and_tokens

    # Act
    response = await test_client.get("/api/authors/leaderboard")

    # Assert - status code
    assert response.status_code == 200, "Should return 200 OK"

    # Assert - JSON structure
    data = response.json()
    assert isinstance(data, list), "Should return array"
    assert len(data) == 3, "Should return 3 authors"

    # Assert - first entry schema
    first_entry = data[0]
    assert "author_address" in first_entry, "Should have author_address field"
    assert "total_tokens" in first_entry, "Should have total_tokens field"
    assert isinstance(first_entry["author_address"], str), "author_address should be string"
    assert isinstance(first_entry["total_tokens"], int), "total_tokens should be integer"

    # Assert - correct ordering
    assert data[0]["author_address"] == authors["author_a"].wallet_address
    assert data[0]["total_tokens"] == 5
    assert data[1]["author_address"] == authors["author_b"].wallet_address
    assert data[1]["total_tokens"] == 3
    assert data[2]["author_address"] == authors["author_c"].wallet_address
    assert data[2]["total_tokens"] == 1


@pytest.mark.asyncio
async def test_api_leaderboard_empty(test_client, session):
    """Test GET /api/authors/leaderboard handles empty database.

    Scenario:
    1. Start with empty database
    2. Call GET /api/authors/leaderboard
    3. Assert 200 OK with empty array

    This verifies graceful empty state handling.
    """
    # Arrange - empty database

    # Act
    response = await test_client.get("/api/authors/leaderboard")

    # Assert
    assert response.status_code == 200, "Should return 200 OK even for empty database"
    data = response.json()
    assert data == [], "Should return empty array"
