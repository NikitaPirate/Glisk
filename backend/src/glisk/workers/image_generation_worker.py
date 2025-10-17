"""Image generation worker for processing detected mint events.

Polls for tokens with status='detected', generates images via Replicate API,
and updates token status to 'uploading' with image URL.
"""

import asyncio
import time
from typing import Callable

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from glisk.core.config import Settings
from glisk.models.author import Author
from glisk.models.token import Token
from glisk.repositories.token import TokenRepository
from glisk.services.image_generation.prompt_validator import validate_prompt
from glisk.services.image_generation.replicate_client import generate_image

logger = structlog.get_logger(__name__)


async def process_single_token(
    token: Token,
    session: AsyncSession,
    settings: Settings,
) -> None:
    """Process a single token for image generation.

    Workflow:
    1. Update status: detected → generating
    2. Fetch author's prompt text
    3. Validate prompt
    4. Call Replicate API to generate image
    5. Update token with image URL and status: generating → uploading

    Args:
        token: Token entity to process
        session: Database session for queries
        settings: Application settings (API tokens, config)

    Raises:
        Exception: Any error during processing (caller should handle)
    """
    token_repo = TokenRepository(session)
    start_time = time.time()

    # Log start of processing
    logger.info(
        "token.generation.started",
        token_id=token.token_id,
    )

    # Step 1: Mark token as generating
    token.mark_generating()
    session.add(token)
    await session.commit()
    await session.refresh(token)

    try:
        # Step 2: Fetch author's prompt text
        result = await session.execute(select(Author).where(Author.id == token.author_id))  # type: ignore[arg-type]
        author = result.scalar_one_or_none()

        if not author:
            raise ValueError(f"Author not found for token {token.token_id}")

        # Step 3: Validate prompt
        prompt = validate_prompt(author.prompt_text)

        # Step 4: Generate image via Replicate
        image_url = await generate_image(
            prompt=prompt,
            api_token=settings.replicate_api_token,
            model_version=settings.replicate_model_version,
        )

        # Step 5: Update token with image URL and mark as uploading
        await token_repo.update_image_url(token, image_url)
        await session.commit()

        # Log successful completion with duration and image URL
        duration = time.time() - start_time
        logger.info(
            "token.generation.succeeded",
            token_id=token.token_id,
            image_url=image_url,
            duration=duration,
        )

    except Exception:
        # If any error occurs, rollback and re-raise
        await session.rollback()
        raise


async def process_batch(
    session: AsyncSession,
    settings: Settings,
) -> None:
    """Process a batch of tokens concurrently for image generation.

    Workflow:
    1. Lock tokens via get_pending_for_generation() (FOR UPDATE SKIP LOCKED)
    2. Process tokens concurrently with asyncio.gather(return_exceptions=True)
    3. Log successes and failures

    Args:
        session: Database session for queries
        settings: Application settings (batch size, API tokens)
    """
    token_repo = TokenRepository(session)

    # Step 1: Lock tokens for processing
    tokens = await token_repo.get_pending_for_generation(limit=settings.worker_batch_size)

    if not tokens:
        # No tokens to process
        return

    # Step 2: Process tokens concurrently
    tasks = [process_single_token(token, session, settings) for token in tokens]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Step 3: Log errors (successes are logged in process_single_token)
    for token, result in zip(tokens, results):
        if isinstance(result, Exception):
            logger.error(
                "token.generation.failed",
                token_id=token.token_id,
                error=str(result),
                error_type=type(result).__name__,
            )


async def run_image_generation_worker(
    session_factory: Callable,
    settings: Settings,
) -> None:
    """Main worker loop for image generation.

    Polls at POLL_INTERVAL_SECONDS, processes batches, and handles graceful shutdown.

    Workflow:
    1. Poll at configured interval
    2. Call process_batch() with new session
    3. Handle CancelledError for graceful shutdown
    4. Log worker start/stop events

    Args:
        session_factory: Factory function that creates database sessions
        settings: Application settings (poll interval, batch size, API tokens)
    """
    logger.info(
        "worker.started",
        poll_interval=settings.poll_interval_seconds,
        batch_size=settings.worker_batch_size,
    )

    try:
        while True:
            # Create new session for each polling cycle
            async with session_factory() as session:
                await process_batch(session, settings)

            # Wait for next polling interval
            await asyncio.sleep(settings.poll_interval_seconds)

    except asyncio.CancelledError:
        # Graceful shutdown
        logger.info("worker.stopped")
        raise
