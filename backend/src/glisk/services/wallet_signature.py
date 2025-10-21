"""Wallet signature verification service for EIP-191 message signing.

This module provides secure wallet ownership verification using Ethereum's
EIP-191 personal message signing standard. Used for authenticating wallet
owners when updating their author profiles without requiring on-chain transactions.
"""

import structlog
from eth_account import Account
from eth_account.messages import encode_defunct
from eth_utils.address import to_checksum_address

logger = structlog.get_logger()


def verify_wallet_signature(wallet_address: str, message: str, signature: str) -> bool:
    """Verify EIP-191 signature matches the claimed wallet address.

    This function implements secure wallet ownership verification by recovering
    the signer's address from the message and signature, then comparing it with
    the claimed wallet address using checksummed address format (EIP-55).

    Args:
        wallet_address: The Ethereum address claiming to have signed the message.
                       Format: 0x followed by 40 hex characters.
        message: The plain text message that was signed by the wallet.
                This should match exactly what was presented to the user for signing.
        signature: The EIP-191 signature produced by the wallet (hex string).
                  Produced by eth_sign or personal_sign RPC methods.

    Returns:
        bool: True if the signature was created by the claimed wallet address,
             False if the signature is invalid or was created by a different wallet.

    Raises:
        ValueError: If the signature format is invalid (not a hex string) or
                   if signature recovery fails (malformed signature).

    Example:
        >>> message = "Update GLISK prompt for wallet: 0x742d35Cc..."
        >>> signature = "0x1234567890abcdef..."  # From wallet signature
        >>> verify_wallet_signature("0x742d35Cc...", message, signature)
        True

    Security Notes:
        - Uses checksummed address comparison (EIP-55)
        - Comparison is constant-time for equal-length strings
        - Does not validate message content or timestamp - caller must validate
        - Does not prevent signature replay - caller should implement nonce/timestamp checks
    """
    # Log verification attempt
    logger.debug(
        "wallet_signature_verification_attempt",
        wallet_address=wallet_address,
        message_preview=message[:50] if len(message) > 50 else message,
        signature_prefix=signature[:10] if len(signature) > 10 else signature,
    )

    try:
        # Encode message using EIP-191 personal message format
        # This prepends "\x19Ethereum Signed Message:\n{len(message)}" to the message
        message_hash = encode_defunct(text=message)

        # Recover the signer's address from the message hash and signature
        # This performs ECDSA signature recovery and returns checksummed address
        recovered_address = Account.recover_message(message_hash, signature=signature)

        # Normalize input address to checksummed format for comparison
        checksummed_input = to_checksum_address(wallet_address)

        # Compare checksummed addresses (constant-time for equal-length strings)
        is_valid = recovered_address == checksummed_input

        # Log verification result
        if is_valid:
            logger.info(
                "wallet_signature_verification_success",
                wallet_address=checksummed_input,
                recovered_address=recovered_address,
            )
        else:
            logger.warning(
                "wallet_signature_verification_failed",
                wallet_address=checksummed_input,
                recovered_address=recovered_address,
                reason="address_mismatch",
            )

        return is_valid

    except Exception as e:
        # Signature recovery can fail for invalid signatures or malformed data
        logger.error(
            "wallet_signature_verification_error",
            wallet_address=wallet_address,
            error=str(e),
            error_type=type(e).__name__,
        )
        # Convert any exception to ValueError with clear error message
        raise ValueError(f"Invalid signature format or signature recovery failed: {str(e)}")
