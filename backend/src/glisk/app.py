"""FastAPI application factory."""

# Import timezone enforcement (sets TZ=UTC)
import asyncio
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from web3 import Web3

from glisk.api.routes import authors, webhooks, x_auth
from glisk.core import timezone  # noqa: F401
from glisk.core.config import Settings, configure_logging
from glisk.core.database import setup_db_session
from glisk.services.blockchain.token_recovery import TokenRecoveryService
from glisk.uow import create_uow_factory
from glisk.workers.image_generation_worker import run_image_generation_worker
from glisk.workers.ipfs_upload_worker import run_ipfs_upload_worker
from glisk.workers.reveal_worker import run_reveal_worker

logger = structlog.get_logger()


def create_resilient_worker(
    coro_func, session_factory, settings, worker_name: str, shutdown_event: asyncio.Event
):
    """Create a worker with automatic restart on failure.

    Args:
        coro_func: Worker coroutine function (e.g., run_image_generation_worker)
        session_factory: Database session factory
        settings: Application settings
        worker_name: Human-readable worker name for logging
        shutdown_event: Event to signal graceful shutdown

    Returns:
        Initial task handle (will be auto-recreated on crash)
    """
    RESTART_DELAY = 1  # Fixed 1 second delay between restarts

    def on_worker_done(task: asyncio.Task):
        # Check if shutdown was requested
        if shutdown_event.is_set():
            logger.info("worker.shutdown_complete", worker=worker_name)
            return

        # Check if task was cancelled (normal shutdown)
        if task.cancelled():
            logger.info("worker.cancelled", worker=worker_name)
            return

        # Check for exceptions
        exc = task.exception()
        if exc:
            logger.error(
                "worker.crashed",
                worker=worker_name,
                error=str(exc),
                error_type=type(exc).__name__,
                retry_in_seconds=RESTART_DELAY,
                exc_info=exc,
            )
            logger.error(
                "=" * 80
                + "\n"
                + f"WORKER CRASH: {worker_name} crashed with {type(exc).__name__}: {exc}\n"
                + f"Restarting in {RESTART_DELAY} second(s)...\n"
                + "=" * 80
            )
        else:
            # Worker stopped cleanly (unexpected for infinite loop workers)
            logger.warning(
                "worker.stopped_unexpectedly",
                worker=worker_name,
                retry_in_seconds=RESTART_DELAY,
            )

        # Schedule restart after fixed delay
        async def restart_worker():
            await asyncio.sleep(RESTART_DELAY)

            # Check again if shutdown was requested during sleep
            if shutdown_event.is_set():
                return

            logger.info("worker.restarting", worker=worker_name)
            new_task = asyncio.create_task(coro_func(session_factory, settings))
            new_task.add_done_callback(on_worker_done)

        # Create restart task
        asyncio.create_task(restart_worker())

    # Create initial task
    task = asyncio.create_task(coro_func(session_factory, settings))
    task.add_done_callback(on_worker_done)
    return task


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager.

    Handles startup and shutdown tasks:
    - Startup: Initialize database session factory, configure logging, start workers
    - Shutdown: Stop workers, close database connections

    Workers automatically restart on failure with exponential backoff.
    """
    # Load settings
    settings = Settings()  # type: ignore[call-arg]

    # Configure logging
    configure_logging(settings)

    # Setup database session factory
    session_factory = setup_db_session(settings.database_url, settings.db_pool_size)

    # Create UoW factory for dependency injection
    uow_factory = create_uow_factory(session_factory)

    # Store in app.state for access in routes
    app.state.session_factory = session_factory
    app.state.uow_factory = uow_factory

    # Run token recovery before starting workers (004-recovery-1-nexttokenid)
    # This ensures database is consistent with on-chain state before workers start processing
    try:
        # Initialize Web3 connection for recovery
        network_url_mapping = {
            "BASE_SEPOLIA": f"https://base-sepolia.g.alchemy.com/v2/{settings.alchemy_api_key}",
            "BASE_MAINNET": f"https://base-mainnet.g.alchemy.com/v2/{settings.alchemy_api_key}",
        }

        if settings.network in network_url_mapping:
            alchemy_url = network_url_mapping[settings.network]
            w3 = Web3(Web3.HTTPProvider(alchemy_url))

            if w3.is_connected():
                # Initialize recovery service
                recovery_service = TokenRecoveryService(
                    w3=w3,
                    contract_address=settings.glisk_nft_contract_address,
                    settings=settings,
                )

                # Run recovery
                async with await uow_factory() as uow:
                    result = await recovery_service.recover_missing_tokens(
                        uow=uow,
                        limit=settings.recovery_batch_size,
                    )

                    if result.recovered_count > 0:
                        logger.info(
                            "startup.recovery_completed",
                            recovered=result.recovered_count,
                            duplicates_skipped=result.skipped_duplicate_count,
                            failed=len(result.errors),
                            total_on_chain=result.total_on_chain,
                        )
                    else:
                        logger.debug(
                            "startup.recovery_no_gaps", total_on_chain=result.total_on_chain
                        )
            else:
                logger.warning("startup.recovery_skipped", reason="web3_connection_failed")
        else:
            logger.warning(
                "startup.recovery_skipped", reason="unsupported_network", network=settings.network
            )
    except Exception as e:
        # Log error but don't prevent startup - workers can still process webhooks
        logger.error(
            "startup.recovery_failed",
            error=str(e),
            error_type=type(e).__name__,
            message="Token recovery failed during startup - workers will still start",
        )

    # Create shutdown event for graceful worker termination
    shutdown_event = asyncio.Event()

    # Start background workers with auto-restart
    image_worker_task = create_resilient_worker(
        run_image_generation_worker, session_factory, settings, "image_generation", shutdown_event
    )
    ipfs_worker_task = create_resilient_worker(
        run_ipfs_upload_worker, session_factory, settings, "ipfs_upload", shutdown_event
    )
    reveal_worker_task = create_resilient_worker(
        run_reveal_worker, session_factory, settings, "reveal", shutdown_event
    )

    logger.info("application.startup", db_url=settings.database_url.split("@")[-1])

    yield

    # Shutdown: Signal workers to stop and close database connections
    logger.info("application.shutdown")
    shutdown_event.set()

    # Cancel all workers
    image_worker_task.cancel()
    ipfs_worker_task.cancel()
    reveal_worker_task.cancel()

    # Wait for cancellation to complete (ignore CancelledError)
    await asyncio.gather(
        image_worker_task,
        ipfs_worker_task,
        reveal_worker_task,
        return_exceptions=True,
    )

    # Close database connection pool
    # Note: async_sessionmaker doesn't have close_all(), engine cleanup happens automatically


def create_app() -> FastAPI:
    """Create and configure FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    settings = Settings()  # type: ignore[call-arg]

    app = FastAPI(
        title="GLISK Backend API",
        description="NFT lifecycle management system",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register API routers
    app.include_router(authors.router)  # Authors router has prefix="/api/authors" in definition
    app.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
    app.include_router(x_auth.router)  # X OAuth router has prefix="/api/authors/x" in definition

    # Health check endpoint with database validation
    @app.get("/health")
    async def health_check(response: Response):
        """Health check endpoint with database connectivity test.

        Returns:
            200: {"status": "healthy"} if database connection succeeds
            503: {"status": "unhealthy", "error": {...}} if database connection fails
        """
        try:
            # Test database connection with simple query
            async with app.state.session_factory() as session:
                result = await session.execute(text("SELECT 1"))
                result.scalar()

            logger.debug("health_check.success")
            return {"status": "healthy"}

        except Exception as e:
            # Log error and return unhealthy status
            logger.error(
                "health_check.failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {
                "status": "unhealthy",
                "error": {
                    "type": type(e).__name__,
                    "message": str(e),
                },
            }

    return app


# Create app instance for uvicorn
app = create_app()
