"""Wallet signature verification service for EIP-191 and ERC-1271 message signing.

This module provides secure wallet ownership verification using:
- EIP-191 personal message signing standard (EOA wallets)
- ERC-1271 contract signature verification (Smart wallets like Base Account)

Used for authenticating wallet owners when updating their author profiles
without requiring on-chain transactions.
"""

import structlog
from eth_account import Account
from eth_account.messages import _hash_eip191_message, encode_defunct
from eth_utils.address import to_checksum_address
from web3 import Web3

logger = structlog.get_logger()

# ERC-1271 magic value for valid signatures
ERC1271_MAGIC_VALUE = bytes.fromhex("1626ba7e")

# Minimal ABI for ERC-1271 isValidSignature function
ERC1271_ABI = [
    {
        "constant": True,
        "inputs": [
            {"name": "_hash", "type": "bytes32"},
            {"name": "_signature", "type": "bytes"},
        ],
        "name": "isValidSignature",
        "outputs": [{"name": "magicValue", "type": "bytes4"}],
        "type": "function",
    }
]


def verify_wallet_signature(
    wallet_address: str, message: str, signature: str, w3: Web3 | None = None
) -> bool:
    """Verify EIP-191 (EOA) or ERC-1271 (Smart Wallet) signature.

    This function implements secure wallet ownership verification supporting both:
    - EIP-191: ECDSA signatures from EOA wallets (MetaMask, Rainbow, etc.)
    - ERC-1271: Contract signatures from Smart Wallets (Base Account, Safe, etc.)

    The function automatically detects signature type by length:
    - 65-66 bytes: EIP-191 ECDSA (uses signature recovery)
    - >66 bytes: ERC-1271 contract signature (requires on-chain call via w3)

    Args:
        wallet_address: The Ethereum address claiming to have signed the message.
                       Format: 0x followed by 40 hex characters.
        message: The plain text message that was signed by the wallet.
                This should match exactly what was presented to the user for signing.
        signature: The signature produced by the wallet (hex string).
                  - EOA: 65-byte ECDSA signature from eth_sign/personal_sign
                  - Smart Wallet: Variable-length ERC-1271 signature data
        w3: Web3 instance for ERC-1271 on-chain verification (required for smart wallets).
           If None, only EIP-191 signatures will be supported.

    Returns:
        bool: True if the signature was created by the claimed wallet address,
             False if the signature is invalid or was created by a different wallet.

    Raises:
        ValueError: If signature format is invalid, recovery fails, or
                   w3 is required but not provided for ERC-1271 signatures.

    Example:
        >>> # EOA wallet (MetaMask)
        >>> verify_wallet_signature("0x742d35Cc...", message, ecdsa_sig)
        True

        >>> # Smart wallet (Base Account) - requires Web3
        >>> from web3 import Web3
        >>> w3 = Web3(Web3.HTTPProvider("https://..."))
        >>> verify_wallet_signature("0x742d35Cc...", message, erc1271_sig, w3=w3)
        True

    Security Notes:
        - Uses checksummed address comparison (EIP-55)
        - ERC-1271 makes on-chain call to contract.isValidSignature()
        - Does not validate message content or timestamp - caller must validate
        - Does not prevent signature replay - caller should implement nonce/timestamp checks
    """
    # Convert signature to bytes for length detection
    try:
        signature_bytes = bytes.fromhex(signature.removeprefix("0x"))
    except ValueError as e:
        logger.error(
            "wallet_signature_hex_decode_error",
            wallet_address=wallet_address,
            signature_prefix=signature[:10] if len(signature) > 10 else signature,
            error=str(e),
        )
        raise ValueError(f"Invalid signature hex format: {str(e)}")

    # Detect signature type by length
    # EIP-191 ECDSA: 65 bytes (r, s, v) or 64 bytes (r, s with v=0/1)
    # ERC-1271: Variable length (usually >100 bytes with WebAuthn data)
    is_eoa_signature = len(signature_bytes) in (64, 65)

    # Log verification attempt
    logger.debug(
        "wallet_signature_verification_attempt",
        wallet_address=wallet_address,
        message_preview=message[:50] if len(message) > 50 else message,
        signature_prefix=signature[:10] if len(signature) > 10 else signature,
        signature_length=len(signature_bytes),
        signature_type="EIP-191 (EOA)" if is_eoa_signature else "ERC-1271 (Smart Wallet)",
    )

    try:
        # Encode message using EIP-191 personal message format
        # This prepends "\x19Ethereum Signed Message:\n{len(message)}" to the message
        message_hash = encode_defunct(text=message)
        checksummed_input = to_checksum_address(wallet_address)

        if is_eoa_signature:
            # EIP-191: ECDSA signature recovery (EOA wallets like MetaMask)
            recovered_address = Account.recover_message(message_hash, signature=signature)

            # Compare checksummed addresses
            is_valid = recovered_address == checksummed_input

            # Log verification result
            if is_valid:
                logger.info(
                    "eip191_signature_verification_success",
                    wallet_address=checksummed_input,
                    recovered_address=recovered_address,
                )
            else:
                logger.warning(
                    "eip191_signature_verification_failed",
                    wallet_address=checksummed_input,
                    recovered_address=recovered_address,
                    reason="address_mismatch",
                )

            return is_valid

        else:
            # ERC-1271: Contract signature verification (Smart wallets like Base Account)
            if w3 is None:
                logger.error(
                    "erc1271_verification_missing_web3",
                    wallet_address=checksummed_input,
                    signature_length=len(signature_bytes),
                )
                raise ValueError(
                    "Smart wallet signature detected (ERC-1271) but Web3 instance not provided. "
                    "Pass w3 parameter for smart wallet support."
                )

            # Check if contract is deployed (smart wallets are deployed lazily)
            try:
                contract_code = w3.eth.get_code(checksummed_input)
                if len(contract_code) == 0:
                    logger.warning(
                        "erc1271_contract_not_deployed",
                        wallet_address=checksummed_input,
                        signature_length=len(signature_bytes),
                    )
                    raise ValueError(
                        "Smart wallet not deployed on this network yet. "
                        "Please make a transaction first to deploy your smart wallet, "
                        "then try signing again."
                    )
            except Exception as e:
                if "not deployed" in str(e).lower():
                    raise  # Re-raise our custom error
                logger.error(
                    "erc1271_get_code_error",
                    wallet_address=checksummed_input,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                raise ValueError(f"Failed to check if smart wallet is deployed: {str(e)}")

            # Create contract instance for isValidSignature call
            contract = w3.eth.contract(address=checksummed_input, abi=ERC1271_ABI)

            # Get the bytes32 hash for ERC-1271
            # Must use full EIP-191 prefixed hash (same as wallet signed)
            # Format: keccak256("\x19Ethereum Signed Message:\n{len}" + message)
            message_hash_bytes = _hash_eip191_message(message_hash)

            # Call isValidSignature(bytes32 hash, bytes signature)
            try:
                magic_value = contract.functions.isValidSignature(
                    message_hash_bytes, signature_bytes
                ).call()

                # Convert result to bytes if it's hex string
                if isinstance(magic_value, str):
                    magic_value = bytes.fromhex(magic_value.removeprefix("0x"))
                elif isinstance(magic_value, int):
                    magic_value = magic_value.to_bytes(4, byteorder="big")

                is_valid = magic_value == ERC1271_MAGIC_VALUE

                if is_valid:
                    logger.info(
                        "erc1271_signature_verification_success",
                        wallet_address=checksummed_input,
                        magic_value=magic_value.hex(),
                    )
                else:
                    logger.warning(
                        "erc1271_signature_verification_failed",
                        wallet_address=checksummed_input,
                        magic_value=magic_value.hex() if magic_value else None,
                        expected=ERC1271_MAGIC_VALUE.hex(),
                    )

                return is_valid

            except Exception as e:
                logger.error(
                    "erc1271_contract_call_error",
                    wallet_address=checksummed_input,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                raise ValueError(f"ERC-1271 contract call failed: {str(e)}")

    except ValueError:
        # Re-raise ValueError exceptions (already logged above)
        raise
    except Exception as e:
        # Catch any other unexpected errors
        logger.error(
            "wallet_signature_verification_error",
            wallet_address=wallet_address,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise ValueError(f"Signature verification failed: {str(e)}")
