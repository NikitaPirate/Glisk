"""Token recovery service for recovering missing tokens from blockchain state.

This module provides the TokenRecoveryService which:
1. Queries contract.nextTokenId() to determine total tokens minted
2. Identifies missing token IDs in database
3. Creates Token records with status=DETECTED for missing tokens
4. Looks up actual prompt author from contract for accurate attribution
"""

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime

import structlog
from sqlalchemy.exc import IntegrityError
from web3 import Web3
from web3.exceptions import BadFunctionCallOutput, ContractLogicError

from glisk.abi import get_contract_abi
from glisk.core.config import Settings
from glisk.models.token import Token, TokenStatus
from glisk.services.exceptions import (
    BlockchainConnectionError,
    ContractNotFoundError,
    DefaultAuthorNotFoundError,
)
from glisk.uow import UnitOfWork

logger = structlog.get_logger()


@dataclass
class RecoveryResult:
    """Result of a recovery operation."""

    total_on_chain: int  # Value from nextTokenId()
    total_in_db: int  # Count of tokens in database before recovery
    missing_count: int  # Number of gaps identified
    recovered_count: int  # Number of tokens created (may be less if duplicates)
    skipped_duplicate_count: int  # Tokens already created by webhook during recovery
    errors: list[str]  # Any non-fatal errors encountered


class TokenRecoveryService:
    """Service for recovering missing tokens from blockchain state."""

    def __init__(
        self,
        w3: Web3,
        contract_address: str,
        settings: Settings,
    ):
        """Initialize recovery service with blockchain connection.

        Args:
            w3: Web3 instance for RPC calls
            contract_address: GliskNFT contract address (checksummed)
            settings: Application settings (for default_author_wallet)
        """
        self.w3 = w3
        self.contract_address = Web3.to_checksum_address(contract_address)
        self.settings = settings

        # Load contract ABI from package resources
        self.contract_abi = get_contract_abi()

        # Initialize contract
        self.contract = self.w3.eth.contract(address=self.contract_address, abi=self.contract_abi)

        logger.info(
            "recovery_service.initialized",
            contract_address=self.contract_address,
            connected=self.w3.is_connected(),
        )

    async def get_next_token_id(self) -> int:
        """Query smart contract's nextTokenId counter with retry logic.

        Returns:
            Next token ID that will be minted (exclusive upper bound)

        Raises:
            BlockchainConnectionError: If RPC call fails after retries
            ContractNotFoundError: If contract address is invalid

        Example:
            If 10 tokens have been minted (IDs 1-10), returns 11
        """
        max_retries = 3
        retry_delays = [1, 2, 4]  # Exponential backoff

        for attempt in range(max_retries):
            try:
                # Call nextTokenId() view function
                next_token_id = self.contract.functions.nextTokenId().call()
                logger.info(
                    "recovery.next_token_id_queried",
                    next_token_id=next_token_id,
                    attempt=attempt + 1,
                )
                return next_token_id

            except (BadFunctionCallOutput, ContractLogicError) as e:
                # Contract not found or function doesn't exist
                logger.error(
                    "recovery.contract_error",
                    error=str(e),
                    error_type=type(e).__name__,
                    contract_address=self.contract_address,
                )
                raise ContractNotFoundError(
                    f"Contract not found at {self.contract_address} "
                    "or nextTokenId() function missing"
                ) from e

            except Exception as e:
                # Network/RPC error - retry
                if attempt < max_retries - 1:
                    delay = retry_delays[attempt]
                    logger.warning(
                        "recovery.rpc_error_retry",
                        error=str(e),
                        error_type=type(e).__name__,
                        attempt=attempt + 1,
                        retry_in_seconds=delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "recovery.rpc_error_exhausted",
                        error=str(e),
                        error_type=type(e).__name__,
                        attempts=max_retries,
                    )
                    raise BlockchainConnectionError(
                        f"Failed to connect to blockchain RPC after {max_retries} attempts: {e}"
                    ) from e

        # Should never reach here due to raise in exception handlers
        raise BlockchainConnectionError("Unexpected error in get_next_token_id")

    async def recover_missing_tokens(
        self,
        uow: UnitOfWork,
        limit: int | None = None,
        dry_run: bool = False,
    ) -> RecoveryResult:
        """Identify and create database records for missing tokens.

        Process:
        1. Query contract.nextTokenId()
        2. Query database for missing token IDs
        3. For each missing token, query tokenPromptAuthor from contract
        4. Lookup/create authors in database by wallet addresses
        5. Create Token records with status=DETECTED
        6. Commit transaction (or rollback if dry_run)

        Args:
            uow: Unit of Work for database transaction
            limit: Optional cap on number of tokens to recover
            dry_run: If True, rollback transaction (don't persist changes)

        Returns:
            RecoveryResult with statistics and details

        Raises:
            BlockchainConnectionError: If contract query fails
            RecoveryError: If recovery process fails
        """
        start_time = datetime.now(UTC)

        # Step 1: Query contract for next token ID
        next_token_id = await self.get_next_token_id()

        logger.info(
            "recovery.started",
            max_token_id=next_token_id,
            limit=limit,
            dry_run=dry_run,
        )

        # Step 2: Query database for missing token IDs
        missing_ids = await uow.tokens.get_missing_token_ids(
            max_token_id=next_token_id, limit=limit
        )

        if not missing_ids:
            logger.info("recovery.no_gaps_detected", max_token_id=next_token_id)
            return RecoveryResult(
                total_on_chain=next_token_id - 1,  # Token IDs start at 1
                total_in_db=next_token_id - 1,
                missing_count=0,
                recovered_count=0,
                skipped_duplicate_count=0,
                errors=[],
            )

        logger.info(
            "recovery.gaps_detected",
            missing_count=len(missing_ids),
            first_missing=missing_ids[0],
            last_missing=missing_ids[-1],
        )

        # Step 3-5: For each missing token, lookup author and create record
        recovered_count = 0
        skipped_duplicate_count = 0
        errors: list[str] = []

        for token_id in missing_ids:
            try:
                # Query tokenPromptAuthor from contract
                author_wallet = self.contract.functions.tokenPromptAuthor(token_id).call()
                author_wallet_checksummed = Web3.to_checksum_address(author_wallet)

                # Lookup author in database (case-insensitive via repository)
                author = await uow.authors.get_by_wallet(author_wallet_checksummed)

                if not author:
                    # Use default author if wallet not found in database
                    # This ensures consistent behavior with webhook processing
                    logger.info(
                        "recovery.author_not_found_using_default",
                        author_wallet=author_wallet_checksummed,
                        default_wallet=self.settings.glisk_default_author_wallet,
                    )
                    author = await uow.authors.get_by_wallet(
                        self.settings.glisk_default_author_wallet
                    )
                    if not author:
                        raise DefaultAuthorNotFoundError(
                            f"Default author not found: "
                            f"{self.settings.glisk_default_author_wallet}. "
                            "Ensure default author exists in database before running recovery."
                        )

                # Check if token is already revealed on-chain
                is_revealed = self.contract.functions.isRevealed(token_id).call()

                # Create token record with appropriate status
                if is_revealed:
                    # Token already revealed - extract metadata URI
                    token_uri = self.contract.functions.tokenURI(token_id).call()
                    metadata_cid = (
                        token_uri.replace("ipfs://", "")
                        if token_uri.startswith("ipfs://")
                        else None
                    )

                    token = Token(
                        token_id=token_id,
                        author_id=author.id,
                        status=TokenStatus.REVEALED,
                        metadata_cid=metadata_cid,
                        generation_attempts=0,
                    )

                    logger.info(
                        "recovery.token_revealed",
                        token_id=token_id,
                        metadata_cid=metadata_cid,
                    )
                else:
                    # Token not revealed - will go through pipeline
                    token = Token(
                        token_id=token_id,
                        author_id=author.id,
                        status=TokenStatus.DETECTED,
                        generation_attempts=0,
                    )

                await uow.tokens.add(token)
                await uow.session.flush()  # Ensure token is persisted

                recovered_count += 1
                logger.info(
                    "recovery.token_created",
                    token_id=token_id,
                    author_id=str(author.id),
                    author_wallet=author_wallet_checksummed,
                    status=token.status.value,
                )

            except IntegrityError:
                # Token already exists (webhook created it concurrently)
                skipped_duplicate_count += 1
                logger.info(
                    "recovery.duplicate_skipped",
                    token_id=token_id,
                    reason="webhook_concurrent_creation",
                )

            except Exception as e:
                # Log error but continue with next token
                error_msg = f"Failed to recover token {token_id}: {e}"
                errors.append(error_msg)
                logger.error(
                    "recovery.token_error",
                    token_id=token_id,
                    error=str(e),
                    error_type=type(e).__name__,
                )

        # Rollback if dry run, otherwise commit handled by UoW context manager
        if dry_run:
            await uow.session.rollback()
            logger.info("recovery.dry_run_rollback")

        duration = (datetime.now(UTC) - start_time).total_seconds()

        result = RecoveryResult(
            total_on_chain=next_token_id - 1,  # Token IDs start at 1
            total_in_db=next_token_id - 1 - len(missing_ids) + recovered_count,
            missing_count=len(missing_ids),
            recovered_count=recovered_count,
            skipped_duplicate_count=skipped_duplicate_count,
            errors=errors,
        )

        logger.info(
            "recovery.completed",
            total_on_chain=result.total_on_chain,
            total_in_db=result.total_in_db,
            recovered_count=result.recovered_count,
            skipped_duplicate_count=result.skipped_duplicate_count,
            error_count=len(errors),
            duration_seconds=duration,
        )

        return result
