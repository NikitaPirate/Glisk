"""CLI command for recovering missed mint events from blockchain history.

Usage:
    python -m glisk.cli.recover_events [OPTIONS]

Examples:
    # First-time recovery from contract deployment block
    python -m glisk.cli.recover_events --from-block 12345000

    # Resume from last checkpoint
    python -m glisk.cli.recover_events

    # Specific block range
    python -m glisk.cli.recover_events --from-block 12345000 --to-block 12346000

    # Dry run (no database writes)
    python -m glisk.cli.recover_events --from-block 12345000 --dry-run

    # Verbose logging
    python -m glisk.cli.recover_events --from-block 12345000 -v
"""

import asyncio
import sys
import time
from argparse import ArgumentParser, Namespace

import structlog

from glisk.core import timezone  # noqa: F401
from glisk.core.config import Settings, configure_logging
from glisk.core.database import setup_db_session
from glisk.services.blockchain.event_recovery import (
    fetch_mint_events,
    get_last_processed_block,
    store_recovered_events,
    update_last_processed_block,
)
from glisk.uow import create_uow_factory

logger = structlog.get_logger()


def parse_args() -> Namespace:
    """Parse command-line arguments."""
    parser = ArgumentParser(
        description="Recover missed NFT mint events from blockchain history",
        epilog="See contracts/cli-interface.md for detailed usage examples",
    )

    parser.add_argument(
        "--from-block",
        type=int,
        help="Starting block number (uses last_processed_block if not provided)",
    )

    parser.add_argument(
        "--to-block",
        default="latest",
        help='Ending block number or "latest" (default: latest)',
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Number of blocks per eth_getLogs request (default: 1000)",
    )

    parser.add_argument(
        "--network",
        type=str,
        help="Override network setting (BASE_SEPOLIA or BASE_MAINNET)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and parse events without database writes",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging (DEBUG level)",
    )

    return parser.parse_args()


async def async_main() -> int:
    """Main CLI entry point (async).

    Returns:
        Exit code: 0 (success), 1 (error), 2 (partial success)
    """
    args = parse_args()

    # Initialize settings and logging
    settings = Settings()  # type: ignore[call-arg]

    # Override network if specified
    if args.network:
        settings.network = args.network

    # Configure logging level
    if args.verbose:
        settings.log_level = "DEBUG"

    configure_logging(settings)

    logger.info(
        "recover_events.start",
        network=settings.network,
        contract=settings.glisk_nft_contract_address,
        dry_run=args.dry_run,
    )

    if args.dry_run:
        logger.info("recover_events.dry_run", message="DRY RUN MODE - No database modifications")

    try:
        # Determine starting block
        from_block = args.from_block

        if from_block is None:
            # Load from system_state
            session_factory = setup_db_session(settings.database_url, settings.db_pool_size)
            uow_factory = create_uow_factory(session_factory)

            async with await uow_factory() as uow:
                last_block = await get_last_processed_block(uow)
                if last_block is None:
                    logger.error(
                        "recover_events.error",
                        message=(
                            "Cannot determine starting block. "
                            "Provide --from-block or ensure "
                            "last_processed_block exists in system_state."
                        ),
                    )
                    return 1
                from_block = last_block + 1
                logger.info(
                    "recover_events.resume", last_processed_block=last_block, from_block=from_block
                )

        # Parse to_block
        to_block: int | str
        if args.to_block == "latest":
            to_block = "latest"
        else:
            try:
                to_block = int(args.to_block)
            except ValueError:
                logger.error(
                    "recover_events.error", message=f"Invalid --to-block value: {args.to_block}"
                )
                return 1

        logger.info(
            "recover_events.range",
            from_block=from_block,
            to_block=to_block,
            batch_size=args.batch_size,
        )

        # Fetch events with retry logic
        events = []
        attempt = 0
        max_attempts = 3

        while attempt < max_attempts:
            try:
                events = fetch_mint_events(
                    settings=settings,
                    from_block=from_block,
                    to_block=to_block,
                    batch_size=args.batch_size,
                )
                break  # Success, exit retry loop

            except Exception as e:
                attempt += 1
                error_msg = str(e)

                # Check for rate limit errors
                if "rate limit" in error_msg.lower() or "429" in error_msg:
                    if attempt < max_attempts:
                        backoff_seconds = 5 * (2 ** (attempt - 1))  # Exponential backoff: 5, 10, 20
                        logger.warning(
                            "recover_events.rate_limit",
                            message=(
                                f"Rate limit exceeded, retrying in {backoff_seconds} seconds "
                                f"(attempt {attempt}/{max_attempts})"
                            ),
                        )
                        time.sleep(backoff_seconds)
                    else:
                        logger.error(
                            "recover_events.error",
                            message=(
                                f"Rate limit exceeded after {max_attempts} retries. "
                                "Use smaller --batch-size or wait before retrying."
                            ),
                        )
                        return 1
                else:
                    # Non-rate-limit error, log and exit
                    logger.error("recover_events.error", error=error_msg)
                    return 1

        logger.info("recover_events.fetched", event_count=len(events))

        # Dry run: print events and exit
        if args.dry_run:
            if events:
                logger.info(
                    "recover_events.dry_run_results",
                    message=f"Found {len(events)} events (would be stored):",
                )
                for event in events[:10]:  # Show first 10 events
                    logger.info(
                        "recover_events.dry_run_event",
                        tx_hash=event["tx_hash"],
                        log_index=event["log_index"],
                        token_id=event["start_token_id"],
                        quantity=event["quantity"],
                    )
                if len(events) > 10:
                    logger.info(
                        "recover_events.dry_run_truncated",
                        message=f"... and {len(events) - 10} more events",
                    )
            else:
                logger.info("recover_events.dry_run_results", message="No events found in range")

            logger.info(
                "recover_events.dry_run_complete", message="DRY RUN COMPLETE - No changes made"
            )
            return 0

        # Store events in database
        if events:
            session_factory = setup_db_session(settings.database_url, settings.db_pool_size)
            uow_factory = create_uow_factory(session_factory)

            async with await uow_factory() as uow:
                stored, skipped = await store_recovered_events(events, uow, settings)
                logger.info(
                    "recover_events.stored",
                    stored=stored,
                    skipped=skipped,
                    total=len(events),
                )

                # Update last processed block
                # Determine the highest block number in fetched events
                if isinstance(to_block, int):
                    last_block = to_block
                else:
                    # Use the highest block from events
                    last_block = (
                        max(event["block_number"] for event in events) if events else from_block
                    )

                await update_last_processed_block(last_block, uow)

                logger.info("recover_events.checkpoint", last_processed_block=last_block)
        else:
            logger.info("recover_events.no_events", message="No events found in range")

        logger.info(
            "recover_events.complete",
            message=f"Recovery complete! Total: {len(events)} events processed",
        )
        return 0

    except KeyboardInterrupt:
        logger.warning("recover_events.interrupted", message="Recovery interrupted by user")
        return 2

    except Exception as e:
        logger.error("recover_events.fatal_error", error=str(e), exc_info=True)
        return 1


def main() -> int:
    """Synchronous wrapper for async main."""
    return asyncio.run(async_main())


if __name__ == "__main__":
    sys.exit(main())
