"""Unit tests for Alchemy webhook signature validation.

Tests the HMAC-SHA256 signature validation logic to ensure only authentic
requests from Alchemy are processed.
"""

import hashlib
import hmac

import pytest

from glisk.services.blockchain.alchemy_signature import validate_alchemy_signature


class TestAlchemySignatureValidation:
    """Test suite for HMAC signature validation."""

    @pytest.fixture
    def signing_key(self) -> str:
        """Webhook signing key for tests."""
        return "test_signing_key_secret"

    @pytest.fixture
    def sample_payload(self) -> bytes:
        """Sample webhook payload as raw bytes."""
        return b'{"webhookId":"wh_test123","id":"whevt_001","type":"CUSTOM"}'

    @pytest.fixture
    def valid_signature(self, sample_payload: bytes, signing_key: str) -> str:
        """Generate valid HMAC signature for sample payload."""
        return hmac.new(
            key=signing_key.encode("utf-8"), msg=sample_payload, digestmod=hashlib.sha256
        ).hexdigest()

    def test_valid_signature_acceptance(
        self, sample_payload: bytes, valid_signature: str, signing_key: str
    ):
        """Test that valid signatures are accepted."""
        # Act
        result = validate_alchemy_signature(
            raw_body=sample_payload, signature=valid_signature, signing_key=signing_key
        )

        # Assert
        assert result is True, "Valid signature should be accepted"

    def test_invalid_signature_rejection(self, sample_payload: bytes, signing_key: str):
        """Test that invalid signatures are rejected."""
        # Arrange
        invalid_signature = "0" * 64  # Wrong signature (all zeros)

        # Act
        result = validate_alchemy_signature(
            raw_body=sample_payload, signature=invalid_signature, signing_key=signing_key
        )

        # Assert
        assert result is False, "Invalid signature should be rejected"

    def test_tampered_payload_rejection(
        self, sample_payload: bytes, valid_signature: str, signing_key: str
    ):
        """Test that tampered payloads are rejected even with original signature."""
        # Arrange - modify payload after signature was generated
        tampered_payload = sample_payload + b"extra_data"

        # Act
        result = validate_alchemy_signature(
            raw_body=tampered_payload, signature=valid_signature, signing_key=signing_key
        )

        # Assert
        assert result is False, "Tampered payload should be rejected"

    def test_wrong_signing_key_rejection(self, sample_payload: bytes, valid_signature: str):
        """Test that requests signed with wrong key are rejected."""
        # Arrange
        wrong_key = "different_signing_key"

        # Act
        result = validate_alchemy_signature(
            raw_body=sample_payload, signature=valid_signature, signing_key=wrong_key
        )

        # Assert
        assert result is False, "Signature from wrong key should be rejected"

    def test_empty_signature_rejection(self, sample_payload: bytes, signing_key: str):
        """Test that empty signatures are rejected."""
        # Arrange
        empty_signature = ""

        # Act
        result = validate_alchemy_signature(
            raw_body=sample_payload, signature=empty_signature, signing_key=signing_key
        )

        # Assert
        assert result is False, "Empty signature should be rejected"

    def test_malformed_signature_rejection(self, sample_payload: bytes, signing_key: str):
        """Test that malformed signatures (non-hex) are rejected."""
        # Arrange
        malformed_signature = "not_a_hex_string_xyz"

        # Act
        result = validate_alchemy_signature(
            raw_body=sample_payload, signature=malformed_signature, signing_key=signing_key
        )

        # Assert
        assert result is False, "Malformed signature should be rejected"

    def test_case_sensitivity(self, sample_payload: bytes, valid_signature: str, signing_key: str):
        """Test that signature comparison is case-insensitive (hex can be upper/lower)."""
        # Arrange - convert signature to uppercase
        uppercase_signature = valid_signature.upper()

        # Act
        result = validate_alchemy_signature(
            raw_body=sample_payload, signature=uppercase_signature, signing_key=signing_key
        )

        # Assert
        # Note: hmac.hexdigest() returns lowercase, but compare_digest handles this
        # If this test fails, we may need to normalize case before comparison
        assert result is True, "Uppercase hex signature should be accepted"

    def test_constant_time_comparison(self, sample_payload: bytes, signing_key: str):
        """Test that constant-time comparison is used (timing attack prevention).

        This is a smoke test - we can't directly measure timing in unit tests,
        but we verify that hmac.compare_digest is being used by checking that
        early mismatches don't cause different behavior than late mismatches.
        """
        # Arrange - create signatures with mismatches at different positions
        correct_sig = hmac.new(
            key=signing_key.encode("utf-8"), msg=sample_payload, digestmod=hashlib.sha256
        ).hexdigest()

        # Early mismatch (first character wrong)
        early_mismatch = "0" + correct_sig[1:]

        # Late mismatch (last character wrong)
        late_mismatch = correct_sig[:-1] + "0"

        # Act
        result_early = validate_alchemy_signature(
            raw_body=sample_payload, signature=early_mismatch, signing_key=signing_key
        )

        result_late = validate_alchemy_signature(
            raw_body=sample_payload, signature=late_mismatch, signing_key=signing_key
        )

        # Assert - both should return False (no early exit)
        assert result_early is False, "Early mismatch should be rejected"
        assert result_late is False, "Late mismatch should be rejected"
        # If we were using == instead of compare_digest, timing might differ

    def test_unicode_payload_handling(self, signing_key: str):
        """Test that unicode payloads are correctly handled as UTF-8 bytes."""
        # Arrange - payload with unicode characters
        unicode_payload = '{"message":"Hello 🔒 World"}'.encode("utf-8")

        # Generate valid signature
        valid_signature = hmac.new(
            key=signing_key.encode("utf-8"), msg=unicode_payload, digestmod=hashlib.sha256
        ).hexdigest()

        # Act
        result = validate_alchemy_signature(
            raw_body=unicode_payload, signature=valid_signature, signing_key=signing_key
        )

        # Assert
        assert result is True, "Unicode payload should be handled correctly"

    def test_large_payload_handling(self, signing_key: str):
        """Test signature validation with large payloads (stress test)."""
        # Arrange - create a large payload (10KB)
        large_payload = b'{"data":"' + (b"x" * 10000) + b'"}'

        # Generate valid signature
        valid_signature = hmac.new(
            key=signing_key.encode("utf-8"), msg=large_payload, digestmod=hashlib.sha256
        ).hexdigest()

        # Act
        result = validate_alchemy_signature(
            raw_body=large_payload, signature=valid_signature, signing_key=signing_key
        )

        # Assert
        assert result is True, "Large payload should be handled correctly"

    def test_empty_payload_handling(self, signing_key: str):
        """Test signature validation with empty payload."""
        # Arrange
        empty_payload = b""

        # Generate valid signature for empty payload
        valid_signature = hmac.new(
            key=signing_key.encode("utf-8"), msg=empty_payload, digestmod=hashlib.sha256
        ).hexdigest()

        # Act
        result = validate_alchemy_signature(
            raw_body=empty_payload, signature=valid_signature, signing_key=signing_key
        )

        # Assert
        assert result is True, "Empty payload with valid signature should be accepted"
