"""Reveal worker for batch reveal operations.

Polls for tokens with status='ready', accumulates batches, and submits
batch reveal transactions to the blockchain network.
"""

import asyncio
from typing import Callable

import structlog
from web3 import Web3

from glisk.core.config import Settings
from glisk.models.reveal_tx import RevealTransaction
from glisk.models.token import Token, TokenStatus
from glisk.repositories.reveal_tx import RevealTransactionRepository
from glisk.repositories.token import TokenRepository
from glisk.services.blockchain.keeper import KeeperService
from glisk.services.exceptions import PermanentError, TransientError

logger = structlog.get_logger()


async def get_batch(
    token_repo: TokenRepository,
    batch_max_size: int,
    batch_wait_time: int,
) -> list[Token]:
    """Accumulate batch of tokens for reveal using two-query pattern.

    Strategy:
    1. Lock up to batch_max_size tokens immediately
    2. If 0 < count < max, wait batch_wait_time seconds
    3. Poll again for remaining slots
    4. Return combined list

    This maximizes batch efficiency while preventing indefinite waiting.

    Args:
        token_repo: Token repository instance
        batch_max_size: Maximum tokens per batch (default: 50)
        batch_wait_time: Wait time in seconds for batch accumulation (default: 5)

    Returns:
        List of tokens locked for this batch (1-50 tokens)
    """
    # First query: lock up to batch_max_size tokens
    tokens = await token_repo.get_ready_for_reveal(limit=batch_max_size)

    if not tokens:
        return []

    token_count = len(tokens)
    logger.debug(
        "reveal.batch_initial_lock",
        token_count=token_count,
        batch_max_size=batch_max_size,
    )

    # If we have some tokens but not max, wait for more
    if 0 < token_count < batch_max_size:
        logger.debug(
            "reveal.batch_waiting",
            current_count=token_count,
            max_size=batch_max_size,
            wait_seconds=batch_wait_time,
        )
        await asyncio.sleep(batch_wait_time)

        # Second query: try to fill remaining slots
        remaining_slots = batch_max_size - token_count
        additional_tokens = await token_repo.get_ready_for_reveal(limit=remaining_slots)

        if additional_tokens:
            # Filter out duplicates by token_id
            # (important: first query may still return same tokens)
            existing_ids = {t.token_id for t in tokens}
            unique_additional = [t for t in additional_tokens if t.token_id not in existing_ids]

            if unique_additional:
                tokens.extend(unique_additional)
                logger.debug(
                    "reveal.batch_accumulated",
                    initial_count=token_count,
                    additional_count=len(unique_additional),
                    duplicates_filtered=len(additional_tokens) - len(unique_additional),
                    final_count=len(tokens),
                )

    return tokens


async def process_reveal_batch(
    tokens: list[Token],
    token_repo: TokenRepository,
    reveal_tx_repo: RevealTransactionRepository,
    keeper: KeeperService,
) -> None:
    """Process a batch of tokens by submitting reveal transaction.

    Args:
        tokens: List of tokens to reveal (1-50 tokens)
        token_repo: Token repository instance
        reveal_tx_repo: Reveal transaction repository instance
        keeper: Keeper service instance

    Raises:
        TransientError: Gas estimation failed, submission failed, timeout
        PermanentError: Transaction reverted on-chain
    """
    if not tokens:
        return

    # Build batch inputs
    token_ids = [t.token_id for t in tokens]
    metadata_uris = [f"ipfs://{t.metadata_cid}" for t in tokens]

    logger.info(
        "reveal.batch_processing",
        token_count=len(tokens),
        token_ids=token_ids,
    )

    # Submit batch reveal transaction
    tx_hash, block_number, gas_used = await keeper.reveal_batch(token_ids, metadata_uris)

    logger.info(
        "reveal.batch_confirmed",
        tx_hash=tx_hash,
        block_number=block_number,
        gas_used=gas_used,
        token_count=len(tokens),
    )

    # Create reveal transaction audit record
    reveal_tx = RevealTransaction(
        token_ids=[t.id for t in tokens],
        tx_hash=tx_hash,
        block_number=block_number,
        status="confirmed",
    )
    await reveal_tx_repo.add(reveal_tx)

    # Update all tokens in batch to revealed status
    for token in tokens:
        await token_repo.mark_revealed(token, tx_hash)

    logger.info(
        "reveal.batch_complete",
        tx_hash=tx_hash,
        token_count=len(tokens),
        duration_seconds=0,  # Could add timing if needed
    )


async def recover_orphaned_transactions(
    reveal_tx_repo: RevealTransactionRepository,
    token_repo: TokenRepository,
    w3: Web3,
) -> None:
    """Check for orphaned pending transactions and update their status.

    On worker restart, pending transactions may have already confirmed or failed.
    This function queries blockchain receipts and updates database accordingly.

    Args:
        reveal_tx_repo: Reveal transaction repository instance
        token_repo: Token repository instance
        w3: Web3 instance for blockchain queries
    """
    from sqlalchemy import select

    from glisk.models.reveal_tx import RevealTransaction

    # Find all pending transactions
    pending_txs_result = await reveal_tx_repo.session.execute(
        select(RevealTransaction).where(RevealTransaction.status == "pending")  # type: ignore[arg-type]
    )
    pending_txs = list(pending_txs_result.scalars().all())

    if not pending_txs:
        logger.info("worker.recovery", message="No orphaned transactions to recover")
        return

    logger.info(
        "worker.recovery_started",
        pending_count=len(pending_txs),
        message="Checking pending transactions for confirmation",
    )

    recovered_count = 0
    for tx_record in pending_txs:
        try:
            # Query blockchain for transaction receipt
            if not tx_record.tx_hash:
                continue
            receipt = w3.eth.get_transaction_receipt(tx_record.tx_hash)  # type: ignore[arg-type]

            if receipt["status"] == 1:
                # Transaction confirmed - update record
                await reveal_tx_repo.mark_confirmed(
                    tx_hash=tx_record.tx_hash,
                    block_number=receipt["blockNumber"],
                    gas_used=receipt["gasUsed"],
                )

                # Update all tokens in batch
                for token_id in tx_record.token_ids:
                    token = await token_repo.get_by_id(token_id)
                    if token and token.status == TokenStatus.READY and tx_record.tx_hash:
                        await token_repo.mark_revealed(token, tx_record.tx_hash)

                recovered_count += 1
                logger.info(
                    "worker.recovery_confirmed",
                    tx_hash=tx_record.tx_hash,
                    block_number=receipt["blockNumber"],
                    token_count=len(tx_record.token_ids),
                )
            else:
                # Transaction reverted - mark as failed
                await reveal_tx_repo.mark_failed(
                    tx_hash=tx_record.tx_hash,
                    error_message="Transaction reverted (detected during recovery)",
                )
                logger.warning(
                    "worker.recovery_reverted",
                    tx_hash=tx_record.tx_hash,
                    message="Tokens remain 'ready' for retry",
                )

        except Exception as e:
            # Transaction not found or RPC error - leave as pending
            logger.warning(
                "worker.recovery_failed",
                tx_hash=tx_record.tx_hash,
                error=str(e),
                message="Transaction still pending or not found",
            )

    logger.info(
        "worker.recovery_complete",
        total_pending=len(pending_txs),
        recovered_count=recovered_count,
    )


async def run_reveal_worker(
    session_factory: Callable,
    settings: Settings,
) -> None:
    """Main entry point for reveal worker.

    Infinite polling loop that:
    1. Polls for tokens with status='ready'
    2. Accumulates batch (with wait strategy)
    3. Submits batch reveal transaction
    4. Updates tokens and creates audit records

    Worker lifecycle:
    - Starts automatically with FastAPI app (registered in lifespan)
    - Runs until asyncio.CancelledError (app shutdown)
    - Completes in-flight operations before exit
    - Recovers orphaned pending transactions on startup

    Error handling:
    - TransientError: Log warning, tokens remain 'ready', retry next poll
    - PermanentError: Log error, tokens remain 'ready', manual investigation

    Args:
        session_factory: Factory function to create new database sessions
        settings: Application settings (poll interval, batch size, keeper config)
    """
    # Extract settings
    poll_interval = settings.poll_interval_seconds
    batch_max_size = settings.batch_reveal_max_tokens
    batch_wait_time = settings.batch_reveal_wait_seconds

    # Initialize Web3 and keeper service
    alchemy_rpc_url = f"https://base-sepolia.g.alchemy.com/v2/{settings.alchemy_api_key}"
    w3 = Web3(Web3.HTTPProvider(alchemy_rpc_url))

    keeper = KeeperService(
        w3=w3,
        contract_address=settings.glisk_nft_contract_address,
        keeper_private_key=settings.keeper_private_key,
        gas_buffer_percentage=settings.reveal_gas_buffer - 1.0,  # Convert 1.2 -> 0.2
        transaction_timeout=settings.transaction_timeout_seconds,
        max_gas_price_gwei=settings.reveal_max_gas_price_gwei,
    )

    # Startup recovery: check for orphaned pending transactions
    async with session_factory() as session:
        try:
            reveal_tx_repo = RevealTransactionRepository(session)
            token_repo = TokenRepository(session)
            await recover_orphaned_transactions(reveal_tx_repo, token_repo, w3)
            await session.commit()
        except Exception as e:
            logger.error(
                "worker.recovery_error",
                error=str(e),
                message="Recovery failed, continuing with worker startup",
            )
            await session.rollback()

    logger.info(
        "worker.started",
        worker="reveal_worker",
        poll_interval=poll_interval,
        batch_max_size=batch_max_size,
        batch_wait_time=batch_wait_time,
        keeper_address=keeper.get_keeper_address(),
    )

    try:
        while True:
            try:
                async with session_factory() as session:
                    token_repo = TokenRepository(session)
                    reveal_tx_repo = RevealTransactionRepository(session)

                    # Get batch of tokens (with accumulation strategy)
                    tokens = await get_batch(token_repo, batch_max_size, batch_wait_time)

                    if tokens:
                        try:
                            # Process batch reveal
                            await process_reveal_batch(tokens, token_repo, reveal_tx_repo, keeper)
                            await session.commit()

                        except TransientError as e:
                            # Transient error: log warning, rollback, tokens remain 'ready'
                            logger.warning(
                                "reveal.transient_error",
                                error=str(e),
                                token_count=len(tokens),
                                message="Tokens remain in 'ready' state, will retry on next poll",
                            )
                            await session.rollback()

                        except PermanentError as e:
                            # Permanent error: log error, rollback, tokens remain 'ready'
                            logger.error(
                                "reveal.permanent_error",
                                error=str(e),
                                token_count=len(tokens),
                                token_ids=[t.token_id for t in tokens],
                                message="Transaction reverted - manual investigation required",
                            )
                            await session.rollback()

                        except Exception as e:
                            # Unexpected error: log error, rollback
                            logger.error(
                                "reveal.unexpected_error",
                                error=str(e),
                                token_count=len(tokens),
                            )
                            await session.rollback()

            except asyncio.CancelledError:
                # Propagate cancellation for graceful shutdown
                raise

            except Exception as e:
                # Unexpected error in polling loop - log and continue with backoff
                logger.error(
                    "worker.error",
                    worker_type="reveal_worker",
                    error_type=type(e).__name__,
                    error_message=str(e),
                    exc_info=True,
                )
                # Back off 5 seconds before retrying
                await asyncio.sleep(5)

            # Wait before next poll
            await asyncio.sleep(poll_interval)

    except asyncio.CancelledError:
        logger.info(
            "worker.stopped",
            worker="reveal_worker",
            message="Graceful shutdown requested",
        )
        raise  # Re-raise to propagate cancellation
