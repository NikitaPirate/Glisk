"""HMAC signature validation for Alchemy webhooks.

This module provides cryptographic signature validation for incoming webhook
requests from Alchemy. It uses HMAC-SHA256 with constant-time comparison to
prevent timing attacks.

Security Note:
    The validate_alchemy_signature function MUST be called before processing
    any webhook payload. Return 401 Unauthorized immediately if validation fails.
"""

import hashlib
import hmac


def validate_alchemy_signature(raw_body: bytes, signature: str, signing_key: str) -> bool:
    """Validate Alchemy webhook signature using HMAC-SHA256.

    This function implements cryptographic signature validation to ensure that
    webhook requests are genuinely from Alchemy and haven't been tampered with.

    Args:
        raw_body: Raw request body bytes (NOT parsed JSON). Must be the exact
            bytes received from the request, before any parsing or transformation.
        signature: Signature value from X-Alchemy-Signature header. This is the
            hex-encoded HMAC-SHA256 signature provided by Alchemy.
        signing_key: Webhook signing key from Alchemy dashboard. This is a secret
            key unique to your webhook configuration.

    Returns:
        True if signature is valid (request is authentic), False otherwise.

    Security:
        - Uses hmac.compare_digest() for constant-time comparison to prevent
          timing attacks. Never use == for signature comparison.
        - Prevents attackers from gradually determining the correct signature
          by measuring response times.

    Example:
        >>> raw_body = b'{"webhookId":"wh_123","event":{...}}'
        >>> signature = "a1b2c3d4e5f6..."
        >>> signing_key = "your_webhook_secret"
        >>> is_valid = validate_alchemy_signature(raw_body, signature, signing_key)
        >>> if not is_valid:
        ...     raise HTTPException(status_code=401, detail="Invalid signature")
    """
    # Compute expected HMAC-SHA256 signature
    expected = hmac.new(
        key=signing_key.encode("utf-8"), msg=raw_body, digestmod=hashlib.sha256
    ).hexdigest()

    # Normalize both signatures to lowercase for case-insensitive comparison
    # (hexdigest() returns lowercase, but accept uppercase input for robustness)
    expected_lower = expected.lower()
    signature_lower = signature.lower()

    # Constant-time comparison to prevent timing attacks
    # NEVER use standard == comparison for cryptographic signatures
    return hmac.compare_digest(expected_lower, signature_lower)
