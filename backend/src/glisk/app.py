"""FastAPI application factory."""

# Import timezone enforcement (sets TZ=UTC)
import asyncio
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from glisk.api.routes import webhooks
from glisk.core import timezone  # noqa: F401
from glisk.core.config import Settings, configure_logging
from glisk.core.database import setup_db_session
from glisk.uow import create_uow_factory
from glisk.workers.image_generation_worker import run_image_generation_worker
from glisk.workers.ipfs_upload_worker import run_ipfs_upload_worker
from glisk.workers.reveal_worker import run_reveal_worker

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager.

    Handles startup and shutdown tasks:
    - Startup: Initialize database session factory, configure logging, start worker
    - Shutdown: Stop worker, close database connections
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

    # Start background workers
    image_worker_task = asyncio.create_task(run_image_generation_worker(session_factory, settings))
    ipfs_worker_task = asyncio.create_task(run_ipfs_upload_worker(session_factory, settings))
    reveal_worker_task = asyncio.create_task(run_reveal_worker(session_factory, settings))

    logger.info("application.startup", db_url=settings.database_url.split("@")[-1])

    yield

    # Shutdown: Cancel workers and close database connections
    logger.info("application.shutdown")
    image_worker_task.cancel()
    ipfs_worker_task.cancel()
    reveal_worker_task.cancel()
    try:
        await image_worker_task
    except asyncio.CancelledError:
        pass
    try:
        await ipfs_worker_task
    except asyncio.CancelledError:
        pass
    try:
        await reveal_worker_task
    except asyncio.CancelledError:
        pass

    await session_factory.close_all()  # type: ignore[attr-defined]


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
    app.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])

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
