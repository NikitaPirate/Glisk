"""Tests for wallet signature verification service.

Tests EIP-191 signature verification using eth-account for wallet ownership validation.
"""

import pytest
from eth_account import Account
from eth_account.messages import encode_defunct

from glisk.services.wallet_signature import verify_wallet_signature


class TestWalletSignatureVerification:
    """Test suite for EIP-191 wallet signature verification."""

    @pytest.fixture
    def test_wallet(self):
        """Create a test wallet with known private key for signature generation."""
        # Generate deterministic test wallet (same wallet across test runs)
        private_key = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        account = Account.from_key(private_key)
        return {
            "address": account.address,  # Checksummed address
            "private_key": private_key,
            "account": account,
        }

    @pytest.fixture
    def different_wallet(self):
        """Create a different test wallet for negative tests."""
        private_key = "0xfedcba0987654321fedcba0987654321fedcba0987654321fedcba0987654321"
        account = Account.from_key(private_key)
        return {
            "address": account.address,
            "private_key": private_key,
            "account": account,
        }

    def test_valid_signature_verification_succeeds(self, test_wallet):
        """Test that valid signature from correct wallet verifies successfully."""
        # Arrange
        message = "Update GLISK prompt for wallet: " + test_wallet["address"]
        message_hash = encode_defunct(text=message)
        signed_message = test_wallet["account"].sign_message(message_hash)

        # Act
        is_valid = verify_wallet_signature(
            wallet_address=test_wallet["address"],
            message=message,
            signature=signed_message.signature.hex(),
        )

        # Assert
        assert is_valid is True

    def test_invalid_signature_wrong_wallet_fails(self, test_wallet, different_wallet):
        """Test that signature from different wallet fails verification."""
        # Arrange: Sign message with different wallet
        message = "Update GLISK prompt for wallet: " + test_wallet["address"]
        message_hash = encode_defunct(text=message)
        signed_message = different_wallet["account"].sign_message(message_hash)

        # Act: Try to verify with test_wallet address (should fail)
        is_valid = verify_wallet_signature(
            wallet_address=test_wallet["address"],
            message=message,
            signature=signed_message.signature.hex(),
        )

        # Assert
        assert is_valid is False

    def test_malformed_signature_raises_value_error(self, test_wallet):
        """Test that malformed signature raises ValueError."""
        # Arrange
        message = "Update GLISK prompt for wallet: " + test_wallet["address"]
        malformed_signature = "0xinvalidsignature"

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid signature hex format"):
            verify_wallet_signature(
                wallet_address=test_wallet["address"],
                message=message,
                signature=malformed_signature,
            )

    def test_checksummed_address_comparison(self, test_wallet):
        """Test that signature verification works with checksummed addresses."""
        # Arrange
        message = "Update GLISK prompt for wallet: " + test_wallet["address"]
        message_hash = encode_defunct(text=message)
        signed_message = test_wallet["account"].sign_message(message_hash)

        # Test with various address formats (checksummed, lowercase, uppercase)
        checksummed_address = test_wallet["address"]  # Already checksummed
        lowercase_address = test_wallet["address"].lower()

        # Act & Assert - checksummed address should work
        assert (
            verify_wallet_signature(
                wallet_address=checksummed_address,
                message=message,
                signature=signed_message.signature.hex(),
            )
            is True
        )

        # Act & Assert - lowercase address should also work (normalized to checksum)
        assert (
            verify_wallet_signature(
                wallet_address=lowercase_address,
                message=message,
                signature=signed_message.signature.hex(),
            )
            is True
        )

    def test_wrong_message_fails_verification(self, test_wallet):
        """Test that signature for different message fails verification."""
        # Arrange: Sign one message
        original_message = "Update GLISK prompt for wallet: " + test_wallet["address"]
        message_hash = encode_defunct(text=original_message)
        signed_message = test_wallet["account"].sign_message(message_hash)

        # Act: Try to verify with different message
        different_message = "Different message content"
        is_valid = verify_wallet_signature(
            wallet_address=test_wallet["address"],
            message=different_message,
            signature=signed_message.signature.hex(),
        )

        # Assert
        assert is_valid is False

    def test_empty_signature_raises_value_error(self, test_wallet):
        """Test that empty signature raises ValueError."""
        # Arrange
        message = "Update GLISK prompt for wallet: " + test_wallet["address"]
        empty_signature = ""

        # Act & Assert
        with pytest.raises(ValueError):
            verify_wallet_signature(
                wallet_address=test_wallet["address"],
                message=message,
                signature=empty_signature,
            )
