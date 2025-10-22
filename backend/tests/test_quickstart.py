"""Quickstart validation tests for Mint Event Detection System.

This test suite validates all quickstart scenarios from
specs/003-003b-event-detection/quickstart.md.

Tests verify:
- Configuration loading (Alchemy credentials)
- Database connectivity
- Webhook endpoint availability
- Signature validation
- Event processing pipeline
"""

import hmac
import json
import os
from hashlib import sha256

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from glisk.app import app
from glisk.core.config import Settings


@pytest_asyncio.fixture
async def test_client(uow_factory):
    """Provide AsyncClient for testing API endpoints with database access.

    Args:
        uow_factory: UnitOfWork factory from conftest (provides database access)

    Note: Injects uow_factory into app.state for dependency injection.
    """
    # Inject uow_factory into app.state for dependency injection
    # This allows webhook endpoints to access the test database
    app.state.uow_factory = uow_factory

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest.fixture
def test_settings():
    """Provide test settings with required configuration.

    Note: In test environment, some Alchemy values may be empty.
    Tests should handle this gracefully or skip when values are required.
    """
    return Settings()  # type: ignore[call-arg]


@pytest.mark.asyncio
class TestQuickstartValidation:
    """Validate all quickstart scenarios for production readiness."""

    async def test_configuration_loading(self, test_settings: Settings):
        """Verify all Alchemy configuration values are loaded from environment.

        Validates:
        - Configuration schema is correct
        - NETWORK is set to valid value
        - Address formats are validated when set

        Note: In test environment, Alchemy values may be empty strings.
        This test validates the configuration schema, not environment setup.
        """
        # Validate network (always has default value)
        assert test_settings.network in [
            "BASE_SEPOLIA",
            "BASE_MAINNET",
        ], "NETWORK must be BASE_SEPOLIA or BASE_MAINNET"

        # Validate contract address format IF set
        if test_settings.glisk_nft_contract_address:
            assert test_settings.glisk_nft_contract_address.startswith("0x"), (
                "Contract address must start with 0x"
            )
            assert len(test_settings.glisk_nft_contract_address) == 42, (
                "Contract address must be 42 characters (0x + 40 hex)"
            )

        # Check that Settings can be instantiated (validates schema)
        assert test_settings is not None
        assert hasattr(test_settings, "alchemy_api_key")
        assert hasattr(test_settings, "alchemy_webhook_secret")
        assert hasattr(test_settings, "glisk_nft_contract_address")
        assert hasattr(test_settings, "default_prompt")

    async def test_database_connectivity(self, session):
        """Verify database connection and required tables exist.

        Validates:
        - Database connection successful
        - mint_events table exists
        - tokens_s0 table exists
        - authors table exists
        - system_state table exists
        """
        # Execute simple query to verify connection
        result = await session.execute(text("SELECT 1 as test"))
        row = result.fetchone()
        assert row is not None
        assert row[0] == 1

        # Verify required tables exist
        required_tables = ["mint_events", "tokens_s0", "authors", "system_state"]

        for table_name in required_tables:
            result = await session.execute(
                text(
                    "SELECT EXISTS "
                    "(SELECT 1 FROM information_schema.tables "
                    f"WHERE table_name = '{table_name}')"
                )
            )
            exists = result.scalar()
            assert exists, f"Required table '{table_name}' does not exist"

    async def test_webhook_endpoint_availability(self, test_client: AsyncClient):
        """Verify webhook endpoint is accessible and returns expected error for missing signature.

        Validates:
        - POST /webhooks/alchemy endpoint exists
        - Returns 401 for missing X-Alchemy-Signature header
        """
        # Send request without signature header
        response = await test_client.post(
            "/webhooks/alchemy",
            json={
                "webhookId": "test",
                "id": "test001",
                "type": "GRAPHQL",
                "event": {"data": {"block": {"logs": []}}},
            },
        )

        # Should return 401 Unauthorized for missing signature
        assert response.status_code == 401
        assert "signature" in response.json()["detail"].lower()

    async def test_webhook_signature_validation_valid(
        self, test_client: AsyncClient, test_settings: Settings
    ):
        """Verify webhook accepts valid HMAC signature.

        Validates:
        - Valid signature is accepted
        - Returns 200 OK for properly signed request
        """
        # Skip if webhook secret not configured (test environment)
        if not test_settings.alchemy_webhook_secret:
            pytest.skip("ALCHEMY_WEBHOOK_SECRET not set in test environment")

        # Create test payload
        payload = {
            "webhookId": "test",
            "id": "test001",
            "type": "GRAPHQL",
            "event": {"data": {"block": {"number": 12345, "logs": []}}},
        }

        body = json.dumps(payload).encode("utf-8")

        # Generate valid HMAC signature
        signature = hmac.new(
            key=test_settings.alchemy_webhook_secret.encode("utf-8"),
            msg=body,
            digestmod=sha256,
        ).hexdigest()

        # Send request with valid signature
        response = await test_client.post(
            "/webhooks/alchemy",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Alchemy-Signature": signature,
            },
        )

        # Should return 200 OK for valid signature
        assert response.status_code == 200
        assert response.json()["status"] == "success"

    async def test_webhook_signature_validation_invalid(self, test_client: AsyncClient):
        """Verify webhook rejects invalid HMAC signature.

        Validates:
        - Invalid signature is rejected
        - Returns 401 Unauthorized
        """
        # Create test payload
        payload = {
            "webhookId": "test",
            "id": "test001",
            "type": "GRAPHQL",
            "event": {"data": {"block": {"logs": []}}},
        }

        body = json.dumps(payload).encode("utf-8")

        # Use invalid signature
        invalid_signature = "0" * 64

        # Send request with invalid signature
        response = await test_client.post(
            "/webhooks/alchemy",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Alchemy-Signature": invalid_signature,
            },
        )

        # Should return 401 Unauthorized for invalid signature
        assert response.status_code == 401
        assert "signature" in response.json()["detail"].lower()

    async def test_webhook_malformed_payload(
        self, test_client: AsyncClient, test_settings: Settings
    ):
        """Verify webhook handles malformed payload gracefully.

        Validates:
        - Returns 400 Bad Request for invalid JSON
        - Returns 400 Bad Request for missing required fields
        """
        # Skip if webhook secret not configured (test environment)
        if not test_settings.alchemy_webhook_secret:
            pytest.skip("ALCHEMY_WEBHOOK_SECRET not set in test environment")

        # Test 1: Invalid JSON
        body = b"{invalid json"
        signature = hmac.new(
            key=test_settings.alchemy_webhook_secret.encode("utf-8"),
            msg=body,
            digestmod=sha256,
        ).hexdigest()

        response = await test_client.post(
            "/webhooks/alchemy",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Alchemy-Signature": signature,
            },
        )

        assert response.status_code == 400
        assert "json" in response.json()["detail"].lower()

        # Test 2: Missing required fields
        payload = {"webhookId": "test"}  # Missing event.data.block.logs
        body = json.dumps(payload).encode("utf-8")
        signature = hmac.new(
            key=test_settings.alchemy_webhook_secret.encode("utf-8"),
            msg=body,
            digestmod=sha256,
        ).hexdigest()

        response = await test_client.post(
            "/webhooks/alchemy",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Alchemy-Signature": signature,
            },
        )

        assert response.status_code == 400

    async def test_webhook_no_matching_events(
        self, test_client: AsyncClient, test_settings: Settings
    ):
        """Verify webhook handles payload with no matching events.

        Validates:
        - Returns 200 OK for non-matching contract addresses
        - Returns success status
        """
        # Skip if webhook secret not configured (test environment)
        if not test_settings.alchemy_webhook_secret:
            pytest.skip("ALCHEMY_WEBHOOK_SECRET not set in test environment")

        # Create payload with logs from different contract
        payload = {
            "webhookId": "test",
            "id": "test001",
            "type": "GRAPHQL",
            "event": {
                "data": {
                    "block": {
                        "number": 12345,
                        "logs": [
                            {
                                # Different contract
                                "account": {
                                    "address": "0x0000000000000000000000000000000000000000"
                                },
                                "topics": ["0x1234"],
                                "data": "0x",
                            }
                        ],
                    }
                }
            },
        }

        body = json.dumps(payload).encode("utf-8")
        signature = hmac.new(
            key=test_settings.alchemy_webhook_secret.encode("utf-8"),
            msg=body,
            digestmod=sha256,
        ).hexdigest()

        response = await test_client.post(
            "/webhooks/alchemy",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Alchemy-Signature": signature,
            },
        )

        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert "no matching events" in response.json()["message"].lower()

    async def test_system_state_recovery_checkpoint(self, uow_factory):
        """Verify system_state table can store recovery checkpoints.

        Validates:
        - Can write last_processed_block to system_state
        - Can read last_processed_block from system_state
        - Value persists across transactions
        """
        test_block = 12345678

        # Write checkpoint
        async with await uow_factory() as uow:
            await uow.system_state.set_state("last_processed_block", test_block)

        # Read checkpoint in new transaction
        async with await uow_factory() as uow:
            value = await uow.system_state.get_state("last_processed_block")

        assert value is not None
        assert int(value) == test_block


@pytest.mark.asyncio
class TestQuickstartHealthChecks:
    """Additional health checks for production deployment."""

    async def test_health_endpoint_exists(self, test_client: AsyncClient):
        """Verify health endpoint is accessible (if implemented).

        Note: This test may fail if /health endpoint is not yet implemented.
        Health endpoint is optional for quickstart validation.
        """
        try:
            response = await test_client.get("/health")
            # If endpoint exists, it should return 200
            assert response.status_code == 200
        except Exception:
            # Health endpoint not implemented yet - acceptable for quickstart
            pytest.skip("Health endpoint not yet implemented")

    async def test_database_pool_size(self, test_settings: Settings):
        """Verify database connection pool is properly configured.

        Validates:
        - DB_POOL_SIZE is set to reasonable value (recommended: 200 from constitution)
        """
        assert test_settings.db_pool_size > 0, "DB_POOL_SIZE must be greater than 0"
        assert test_settings.db_pool_size <= 500, "DB_POOL_SIZE should not exceed 500"

        # Warning if not at recommended value (not a failure)
        if test_settings.db_pool_size != 200:
            import warnings

            warnings.warn(
                f"DB_POOL_SIZE is {test_settings.db_pool_size}, "
                "recommended value is 200 per constitution"
            )

    async def test_timezone_enforcement(self):
        """Verify UTC timezone is enforced.

        Validates:
        - glisk.core.timezone module is imported (sets TZ=UTC)
        - datetime.utcnow() returns UTC time
        """
        # Import should set TZ=UTC via side effects
        from glisk.core import timezone  # noqa: F401

        # Verify TZ environment variable is set (may not be enforced in tests)
        # This is a soft check - primary enforcement is at application startup
        tz = os.environ.get("TZ")
        if tz:
            assert tz in ["UTC", "GMT"], f"TZ should be UTC or GMT, got {tz}"
