"""Integration tests for author API endpoints.

Tests author profile management endpoints including:
- POST /api/authors/prompt - Create/update author prompt with signature verification
- GET /api/authors/{wallet_address} - Check author prompt status

Uses TDD approach: tests written first, should FAIL before implementation.
"""

import pytest
import pytest_asyncio
from eth_account import Account
from eth_account.messages import encode_defunct
from httpx import ASGITransport, AsyncClient

from glisk.app import app
from glisk.models.author import Author
from glisk.repositories.author import AuthorRepository


@pytest_asyncio.fixture
async def test_client(uow_factory):
    """Provide AsyncClient for testing API endpoints with database access."""
    # Inject uow_factory into app.state for dependency injection
    app.state.uow_factory = uow_factory
    # Set w3 to None for tests (EOA signatures don't need Web3)
    app.state.w3 = None

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest.fixture
def test_wallet():
    """Create test wallet for signature generation."""
    private_key = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
    account = Account.from_key(private_key)
    return {
        "address": account.address,
        "private_key": private_key,
        "account": account,
    }


@pytest.fixture
def different_wallet():
    """Create different test wallet for negative tests."""
    private_key = "0xfedcba0987654321fedcba0987654321fedcba0987654321fedcba0987654321"
    account = Account.from_key(private_key)
    return {
        "address": account.address,
        "private_key": private_key,
        "account": account,
    }


def sign_message(account: Account, message: str) -> str:
    """Helper to sign message and return hex signature."""
    message_hash = encode_defunct(text=message)
    signed_message = account.sign_message(message_hash)
    return signed_message.signature.hex()


@pytest.mark.asyncio
class TestAuthorPromptEndpoint:
    """Test POST /api/authors/prompt endpoint with signature verification."""

    async def test_create_new_author_with_valid_signature(self, test_client, test_wallet, session):
        """Test creating new author with valid signature returns success response."""
        # Arrange
        prompt_text = "Surreal neon landscapes with futuristic architecture"
        message = f"Update GLISK prompt for wallet: {test_wallet['address']}"
        signature = sign_message(test_wallet["account"], message)

        # Act
        response = await test_client.post(
            "/api/authors/prompt",
            json={
                "wallet_address": test_wallet["address"],
                "prompt_text": prompt_text,
                "message": message,
                "signature": signature,
            },
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["has_prompt"] is True
        # Verify prompt text is NOT echoed back (security requirement)
        assert "prompt_text" not in data

        # Verify author was created in database
        repo = AuthorRepository(session)
        author = await repo.get_by_wallet(test_wallet["address"])
        assert author is not None
        assert author.prompt_text == prompt_text
        assert author.wallet_address == test_wallet["address"]

    async def test_update_existing_author_with_valid_signature(
        self, test_client, test_wallet, session
    ):
        """Test updating existing author's prompt with valid signature."""
        # Arrange: Create existing author first
        repo = AuthorRepository(session)
        existing_author = Author(
            wallet_address=test_wallet["address"],
            prompt_text="Original prompt text",
        )
        await repo.add(existing_author)
        await session.commit()

        # Create update request
        new_prompt = "Updated surreal landscapes with vibrant colors"
        message = f"Update GLISK prompt for wallet: {test_wallet['address']}"
        signature = sign_message(test_wallet["account"], message)

        # Act
        response = await test_client.post(
            "/api/authors/prompt",
            json={
                "wallet_address": test_wallet["address"],
                "prompt_text": new_prompt,
                "message": message,
                "signature": signature,
            },
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["has_prompt"] is True
        assert "prompt_text" not in data  # No prompt echo

        # Verify author was updated (not duplicated)
        await session.refresh(existing_author)
        assert existing_author.prompt_text == new_prompt

        # Verify no duplicate authors created
        all_authors = await repo.list_all()
        authors_with_wallet = [
            a for a in all_authors if a.wallet_address.lower() == test_wallet["address"].lower()
        ]
        assert len(authors_with_wallet) == 1

    async def test_invalid_signature_returns_400_error(
        self, test_client, test_wallet, different_wallet
    ):
        """Test that invalid signature (from wrong wallet) returns 400 error."""
        # Arrange: Sign with different wallet, claim to be test_wallet
        prompt_text = "Surreal neon landscapes"
        message = f"Update GLISK prompt for wallet: {test_wallet['address']}"
        # Sign with DIFFERENT wallet (should fail verification)
        signature = sign_message(different_wallet["account"], message)

        # Act
        response = await test_client.post(
            "/api/authors/prompt",
            json={
                "wallet_address": test_wallet["address"],  # Claim to be test_wallet
                "prompt_text": prompt_text,
                "message": message,
                "signature": signature,  # But signature is from different_wallet
            },
        )

        # Assert
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "signature" in data["detail"].lower() or "verification" in data["detail"].lower()

    async def test_empty_prompt_returns_422_validation_error(self, test_client, test_wallet):
        """Test that empty prompt text returns 422 Pydantic validation error."""
        # Arrange
        message = f"Update GLISK prompt for wallet: {test_wallet['address']}"
        signature = sign_message(test_wallet["account"], message)

        # Act
        response = await test_client.post(
            "/api/authors/prompt",
            json={
                "wallet_address": test_wallet["address"],
                "prompt_text": "",  # Empty prompt (invalid)
                "message": message,
                "signature": signature,
            },
        )

        # Assert: FastAPI returns 422 for Pydantic validation errors
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    async def test_prompt_too_long_returns_422_error(self, test_client, test_wallet):
        """Test that prompt text exceeding 1000 characters returns 422 Pydantic validation error."""
        # Arrange
        too_long_prompt = "a" * 1001  # 1001 characters (limit is 1000)
        message = f"Update GLISK prompt for wallet: {test_wallet['address']}"
        signature = sign_message(test_wallet["account"], message)

        # Act
        response = await test_client.post(
            "/api/authors/prompt",
            json={
                "wallet_address": test_wallet["address"],
                "prompt_text": too_long_prompt,
                "message": message,
                "signature": signature,
            },
        )

        # Assert: FastAPI returns 422 for Pydantic validation errors
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data


@pytest.mark.asyncio
class TestAuthorStatusEndpoint:
    """Test GET /api/authors/{wallet_address} endpoint."""

    async def test_get_author_status_returns_has_prompt_true(
        self, test_client, test_wallet, session
    ):
        """Test GET returns has_prompt=true for existing author."""
        # Arrange: Create author with prompt
        repo = AuthorRepository(session)
        author = Author(
            wallet_address=test_wallet["address"],
            prompt_text="Surreal neon landscapes",
        )
        await repo.add(author)
        await session.commit()

        # Act
        response = await test_client.get(f"/api/authors/{test_wallet['address']}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["has_prompt"] is True
        # Verify prompt text is NEVER returned (security requirement)
        assert "prompt_text" not in data

    async def test_get_nonexistent_author_returns_has_prompt_false(self, test_client, test_wallet):
        """Test GET returns has_prompt=false for non-existent author (not 404)."""
        # Act: Query for wallet that doesn't exist in database
        response = await test_client.get(f"/api/authors/{test_wallet['address']}")

        # Assert: Should return 200 OK with has_prompt=false (NOT 404)
        assert response.status_code == 200
        data = response.json()
        assert data["has_prompt"] is False

    async def test_get_author_status_case_insensitive(self, test_client, test_wallet, session):
        """Test GET endpoint handles case-insensitive wallet addresses."""
        # Arrange: Create author with checksummed address
        repo = AuthorRepository(session)
        author = Author(
            wallet_address=test_wallet["address"],  # Checksummed
            prompt_text="Surreal neon landscapes",
        )
        await repo.add(author)
        await session.commit()

        # Act: Query with lowercase address
        lowercase_address = test_wallet["address"].lower()
        response = await test_client.get(f"/api/authors/{lowercase_address}")

        # Assert: Should still find the author
        assert response.status_code == 200
        data = response.json()
        assert data["has_prompt"] is True
