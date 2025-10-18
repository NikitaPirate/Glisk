"""CLI command for recovering missing tokens from blockchain state.

Usage:
    python -m glisk.cli.recover_tokens [OPTIONS]

Examples:
    # Recover all missing tokens
    python -m glisk.cli.recover_tokens

    # Limit recovery to 100 tokens
    python -m glisk.cli.recover_tokens --limit 100

    # Dry run (no database writes)
    python -m glisk.cli.recover_tokens --dry-run

    # Verbose logging
    python -m glisk.cli.recover_tokens -v
"""

import asyncio
import sys
from argparse import ArgumentParser, Namespace

import structlog
from web3 import Web3

from glisk.core import timezone  # noqa: F401
from glisk.core.config import Settings, configure_logging
from glisk.core.database import setup_db_session
from glisk.services.blockchain.token_recovery import TokenRecoveryService
from glisk.services.exceptions import RecoveryError
from glisk.uow import create_uow_factory

logger = structlog.get_logger()


def parse_args() -> Namespace:
    """Parse command-line arguments."""
    parser = ArgumentParser(
        description="Recover missing tokens from blockchain state",
        epilog="Uses contract.nextTokenId() to identify and recover missing tokens",
    )

    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of tokens to recover (default: unlimited)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Identify missing tokens without database writes",
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

    # Configure logging level
    if args.verbose:
        settings.log_level = "DEBUG"

    configure_logging(settings)

    logger.info(
        "cli.started",
        limit=args.limit,
        dry_run=args.dry_run,
        contract_address=settings.glisk_nft_contract_address,
        network=settings.network,
    )

    # Initialize Web3 connection
    network_url_mapping = {
        "BASE_SEPOLIA": f"https://base-sepolia.g.alchemy.com/v2/{settings.alchemy_api_key}",
        "BASE_MAINNET": f"https://base-mainnet.g.alchemy.com/v2/{settings.alchemy_api_key}",
    }

    if settings.network not in network_url_mapping:
        logger.error("cli.unsupported_network", network=settings.network)
        print(f"Error: Unsupported network {settings.network}", file=sys.stderr)
        return 1

    alchemy_url = network_url_mapping[settings.network]
    w3 = Web3(Web3.HTTPProvider(alchemy_url))

    if not w3.is_connected():
        logger.error("cli.connection_failed", alchemy_url=alchemy_url)
        print(f"Error: Failed to connect to {alchemy_url}", file=sys.stderr)
        return 1

    logger.info("cli.web3_connected", network=settings.network)

    # Initialize database session factory
    session_factory = setup_db_session(settings.database_url, settings.db_pool_size)
    uow_factory = create_uow_factory(session_factory)

    # Initialize recovery service
    recovery_service = TokenRecoveryService(
        w3=w3,
        contract_address=settings.glisk_nft_contract_address,
    )

    try:
        # Execute recovery
        async with await uow_factory() as uow:
            result = await recovery_service.recover_missing_tokens(
                uow=uow,
                limit=args.limit,
                dry_run=args.dry_run,
            )

        # Print summary
        print("\n" + "=" * 60)
        print("Token Recovery Summary")
        print("=" * 60)
        print(f"Total tokens on-chain: {result.total_on_chain}")
        print(f"Total tokens in database: {result.total_in_db}")
        print(f"Missing tokens detected: {result.missing_count}")
        print(f"Tokens recovered: {result.recovered_count}")
        print(f"Duplicates skipped: {result.skipped_duplicate_count}")

        if result.errors:
            print(f"\nErrors encountered: {len(result.errors)}")
            for error in result.errors[:5]:  # Show first 5 errors
                print(f"  - {error}")
            if len(result.errors) > 5:
                print(f"  ... and {len(result.errors) - 5} more errors")

        if args.dry_run:
            print("\n[DRY RUN] No changes were persisted to database")

        print("=" * 60 + "\n")

        # Determine exit code
        if result.recovered_count == 0 and result.missing_count == 0:
            logger.info("cli.success_no_gaps")
            return 0  # Success - no missing tokens
        elif result.recovered_count == result.missing_count:
            logger.info("cli.success_all_recovered")
            return 0  # Success - all tokens recovered
        elif result.recovered_count > 0:
            logger.warning("cli.partial_success")
            return 2  # Partial success - some errors
        else:
            logger.error("cli.failure")
            return 1  # Failure - no tokens recovered

    except RecoveryError as e:
        logger.error(
            "cli.recovery_error",
            error=str(e),
            error_type=type(e).__name__,
        )
        print(f"\nError: {e}", file=sys.stderr)
        return 1

    except KeyboardInterrupt:
        logger.info("cli.interrupted")
        print("\nRecovery interrupted by user", file=sys.stderr)
        return 130  # Standard exit code for SIGINT

    except Exception as e:
        logger.error(
            "cli.unexpected_error",
            error=str(e),
            error_type=type(e).__name__,
        )
        print(f"\nUnexpected error: {e}", file=sys.stderr)
        return 1


def main() -> None:
    """Synchronous entry point for CLI."""
    sys.exit(asyncio.run(async_main()))


if __name__ == "__main__":
    main()
