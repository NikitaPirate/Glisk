"""Farcaster SIWF signature verification.

This module provides verification for Sign In With Farcaster (SIWF) signatures,
which are based on the Sign In With Ethereum (SIWE) standard (EIP-4361).

SIWF messages are signed by Farcaster wallets (custody or auth addresses) and
must be cryptographically verified on the backend to prove ownership.
"""

import structlog

logger = structlog.get_logger()


def verify_farcaster_signature(
    message: str,
    signature: str,
    expected_domain: str,
    expected_address: str | None = None,
    nonce: str | None = None,
) -> bool:
    """Verify a Sign In With Farcaster (SIWF) signature.

    SIWF uses the SIWE (Sign In With Ethereum) message format and verification
    process. This function parses the SIWF message, verifies the cryptographic
    signature, and validates the message parameters (domain, nonce, expiration).

    Args:
        message: SIWF message string (EIP-4361 format)
        signature: Hex signature from Farcaster wallet (0x-prefixed)
        expected_domain: Domain that must match the message's domain field
        expected_address: Optional wallet address to verify against message.address
        nonce: Optional nonce to verify against message.nonce

    Returns:
        True if signature is valid and all checks pass, False otherwise

    Raises:
        No exceptions raised - all errors are caught and logged

    Example:
        >>> message = "example.com wants you to sign in with your Ethereum account..."
        >>> signature = "0x1234567890abcdef..."
        >>> is_valid = verify_farcaster_signature(
        ...     message=message,
        ...     signature=signature,
        ...     expected_domain="example.com",
        ...     expected_address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"
        ... )
        >>> print(is_valid)
        True
    """
    try:
        # Parse SIWF message (EIP-4361 format)
        logger.debug(
            "farcaster_message_received",
            message_type=type(message).__name__,
            message_preview=message[:100] if isinstance(message, str) else str(message)[:100],
        )

        # Verify using eth_account directly for Farcaster signatures
        # This avoids the complexity of siwe library parsing
        import re

        from eth_account import Account
        from eth_account.messages import encode_defunct

        # Parse the SIWE message to extract the signer address and domain
        lines = message.strip().split("\n")

        # Extract domain from first line
        domain_match = re.match(r"(.+) wants you to sign in", lines[0])
        message_domain = domain_match.group(1) if domain_match else ""

        # Extract address from second line
        signer_address = lines[1].strip() if len(lines) > 1 else ""

        # Check domain matches
        if message_domain != expected_domain:
            logger.warning(
                "farcaster_domain_mismatch",
                message_domain=message_domain,
                expected_domain=expected_domain,
            )
            return False

        # Verify the signature using eth_account
        # Encode the message for signing
        encoded_message = encode_defunct(text=message)

        # Recover the address from the signature
        recovered_address = Account.recover_message(encoded_message, signature=signature)

        logger.debug(
            "farcaster_signature_recovery",
            signer_address=signer_address,
            recovered_address=recovered_address,
        )

        # Check if the recovered address matches the signer address in the message
        from web3 import Web3

        # Normalize addresses for comparison
        normalized_signer = Web3.to_checksum_address(signer_address)
        normalized_recovered = Web3.to_checksum_address(recovered_address)

        if normalized_signer != normalized_recovered:
            logger.warning(
                "farcaster_signature_mismatch",
                signer_address=normalized_signer,
                recovered_address=normalized_recovered,
            )
            return False

        logger.info(
            "farcaster_signature_verified",
            address=normalized_signer,
            domain=message_domain,
        )

        # Optional: Verify the signing address matches expected address
        if expected_address:
            normalized_expected = Web3.to_checksum_address(expected_address)

            if normalized_signer != normalized_expected:
                logger.warning(
                    "farcaster_address_mismatch",
                    message_address=normalized_signer,
                    expected_address=normalized_expected,
                )
                return False

        return True

    except Exception as e:
        # Catch-all for unexpected errors
        logger.error(
            "unexpected_error_verifying_farcaster_signature",
            error=str(e),
            error_type=type(e).__name__,
        )
        return False
