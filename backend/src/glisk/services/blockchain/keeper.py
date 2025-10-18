"""Keeper service for batch reveal operations on blockchain."""

from typing import Tuple

import structlog
from eth_account import Account
from web3 import Web3
from web3.exceptions import TimeExhausted

from glisk.abi import get_contract_abi
from glisk.services.exceptions import (
    GasEstimationError,
    TransactionRevertError,
    TransactionSubmissionError,
    TransactionTimeoutError,
    TransientError,
)

logger = structlog.get_logger()


class KeeperService:
    """Blockchain keeper service for batch reveal operations."""

    def __init__(
        self,
        w3: Web3,
        contract_address: str,
        keeper_private_key: str,
        gas_buffer_percentage: float = 0.20,
        transaction_timeout: int = 180,
    ):
        """
        Initialize keeper service.

        Args:
            w3: Web3 instance (connected to Base L2)
            contract_address: GliskNFT contract address
            keeper_private_key: Private key for keeper wallet (0x-prefixed hex)
            gas_buffer_percentage: Safety buffer for gas estimation (default: 0.20 = 20%)
            transaction_timeout: Max wait time for confirmation in seconds (default: 180)
        """
        self.w3 = w3
        self.contract_address = Web3.to_checksum_address(contract_address)
        self.keeper_private_key = keeper_private_key
        self.gas_buffer = 1.0 + gas_buffer_percentage
        self.transaction_timeout = transaction_timeout

        # Load contract ABI from package resources
        self.contract_abi = get_contract_abi()

        # Initialize contract
        self.contract = self.w3.eth.contract(address=self.contract_address, abi=self.contract_abi)

        # Derive keeper account
        self.keeper_account = Account.from_key(keeper_private_key)
        self.keeper_address = self.keeper_account.address

        logger.info(
            "keeper.initialized",
            keeper_address=self.keeper_address,
            contract_address=self.contract_address,
            gas_buffer=self.gas_buffer,
            timeout=transaction_timeout,
        )

    def get_keeper_address(self) -> str:
        """
        Get keeper wallet address.

        Returns:
            Ethereum address (checksummed, 0x-prefixed)
        """
        return self.keeper_address

    async def estimate_gas(
        self,
        token_ids: list[int],
        metadata_uris: list[str],
    ) -> Tuple[int, int, int]:
        """
        Estimate gas parameters for batch reveal transaction.

        Args:
            token_ids: Array of token IDs to reveal
            metadata_uris: Array of metadata URIs

        Returns:
            Tuple of (gas_limit, max_fee_per_gas, max_priority_fee_per_gas)
            - gas_limit: Estimated gas limit with buffer applied (wei)
            - max_fee_per_gas: EIP-1559 max fee per gas with buffer (wei)
            - max_priority_fee_per_gas: EIP-1559 priority fee with buffer (wei)

        Raises:
            TransientError: RPC error, network timeout, estimation failure
        """
        try:
            # Estimate gas for the transaction
            estimated_gas = self.contract.functions.revealTokens(
                token_ids, metadata_uris
            ).estimate_gas({"from": self.keeper_address})

            # Apply gas buffer
            gas_limit = int(estimated_gas * self.gas_buffer)

            # Get EIP-1559 fee parameters
            max_priority_fee = self.w3.eth.max_priority_fee
            latest_block = self.w3.eth.get_block("latest")
            base_fee = latest_block.get("baseFeePerGas", 0)  # type: ignore[arg-type]

            # Apply buffer to fee parameters
            max_priority_fee_buffered = int(max_priority_fee * self.gas_buffer)
            max_fee_per_gas = int((base_fee * 2) + max_priority_fee_buffered)

            logger.debug(
                "keeper.gas_estimated",
                token_count=len(token_ids),
                estimated_gas=estimated_gas,
                gas_limit=gas_limit,
                base_fee=base_fee,
                max_priority_fee=max_priority_fee,
                max_priority_fee_buffered=max_priority_fee_buffered,
                max_fee_per_gas=max_fee_per_gas,
            )

            return gas_limit, max_fee_per_gas, max_priority_fee_buffered

        except Exception as e:
            error_msg = str(e)
            logger.error(
                "keeper.gas_estimation_failed",
                error=error_msg,
                token_count=len(token_ids),
            )

            # Add actionable context based on error type
            if "insufficient funds" in error_msg.lower():
                context = (
                    "Keeper wallet has insufficient balance for gas. "
                    f"Check balance at {self.keeper_address}. "
                    "Fund wallet or adjust REVEAL_GAS_BUFFER setting."
                )
            elif "execution reverted" in error_msg.lower():
                context = (
                    "Transaction simulation reverted. "
                    "Verify token IDs are valid and not already revealed. "
                    "Check contract state at https://sepolia.basescan.org/"
                )
            else:
                context = f"Gas estimation failed: {error_msg}"

            raise GasEstimationError(context) from e

    async def reveal_batch(
        self,
        token_ids: list[int],
        metadata_uris: list[str],
    ) -> Tuple[str, int, int]:
        """
        Submit batch reveal transaction to blockchain and wait for confirmation.

        Args:
            token_ids: Array of token IDs to reveal (length 1-50)
            metadata_uris: Array of metadata URIs (ipfs://<CID> format, same length as token_ids)

        Returns:
            Tuple of (tx_hash, block_number, gas_used)
            - tx_hash: Transaction hash (0x-prefixed hex string)
            - block_number: Block number where transaction confirmed
            - gas_used: Actual gas used by transaction

        Raises:
            TransientError: Gas estimation failed, submission failed, confirmation timeout
            PermanentError: Transaction reverted on-chain, invalid parameters
        """
        try:
            # Estimate gas
            gas_limit, max_fee_per_gas, max_priority_fee_per_gas = await self.estimate_gas(
                token_ids, metadata_uris
            )

            # Get nonce
            nonce = self.w3.eth.get_transaction_count(self.keeper_address, "pending")

            # Build transaction
            transaction = self.contract.functions.revealTokens(
                token_ids, metadata_uris
            ).build_transaction(
                {
                    "from": self.keeper_address,
                    "nonce": nonce,
                    "gas": gas_limit,
                    "maxFeePerGas": max_fee_per_gas,
                    "maxPriorityFeePerGas": max_priority_fee_per_gas,
                    "chainId": self.w3.eth.chain_id,
                }  # type: ignore[arg-type]
            )

            # Sign transaction
            signed_txn = self.w3.eth.account.sign_transaction(
                transaction, private_key=self.keeper_private_key
            )

            # Send transaction
            try:
                tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
                tx_hash_hex = tx_hash.hex()
                logger.info(
                    "keeper.transaction_submitted",
                    tx_hash=tx_hash_hex,
                    token_count=len(token_ids),
                    nonce=nonce,
                    gas_limit=gas_limit,
                )
            except Exception as e:
                logger.error(
                    "keeper.transaction_submission_failed",
                    error=str(e),
                    token_count=len(token_ids),
                )
                raise TransactionSubmissionError(f"Transaction submission failed: {str(e)}") from e

            # Wait for transaction receipt
            try:
                receipt = self.w3.eth.wait_for_transaction_receipt(
                    tx_hash, timeout=self.transaction_timeout
                )
            except TimeExhausted as e:
                logger.warning(
                    "keeper.transaction_timeout",
                    tx_hash=tx_hash_hex,
                    timeout=self.transaction_timeout,
                )
                raise TransactionTimeoutError(
                    f"Transaction confirmation timeout: {tx_hash_hex}"
                ) from e

            # Check if transaction reverted
            if receipt["status"] == 0:
                logger.error(
                    "keeper.transaction_reverted",
                    tx_hash=tx_hash_hex,
                    block_number=receipt["blockNumber"],
                    gas_used=receipt["gasUsed"],
                )

                # Add actionable context for reverts
                revert_msg = (
                    f"Transaction reverted: {tx_hash_hex}. "
                    "Verify token IDs are valid and metadata URIs match format 'ipfs://<CID>'. "
                    "Check transaction details at https://sepolia.basescan.org/tx/{tx_hash_hex}. "
                    "Tokens remain in 'ready' state for manual investigation."
                )
                raise TransactionRevertError(revert_msg)

            # Success
            block_number = receipt["blockNumber"]
            gas_used = receipt["gasUsed"]

            logger.info(
                "keeper.transaction_confirmed",
                tx_hash=tx_hash_hex,
                block_number=block_number,
                gas_used=gas_used,
                gas_limit=gas_limit,
                gas_saved=gas_limit - gas_used,
                token_count=len(token_ids),
            )

            return tx_hash_hex, block_number, gas_used

        except (
            GasEstimationError,
            TransactionSubmissionError,
            TransactionTimeoutError,
            TransactionRevertError,
        ):
            # Re-raise known errors
            raise
        except Exception as e:
            logger.error(
                "keeper.unexpected_error",
                error=str(e),
                token_count=len(token_ids),
            )
            raise TransientError(f"Unexpected error: {str(e)}") from e
