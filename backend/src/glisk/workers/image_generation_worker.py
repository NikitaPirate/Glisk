"""Image generation worker for processing detected mint events.

Polls for tokens with status='detected', generates images via Replicate API,
and updates token status to 'uploading' with image URL.

## Why This Worker Does NOT Use Unit of Work (UoW) Pattern

This worker intentionally bypasses the UoW pattern and uses direct session management.

**Justification:**

The UoW pattern assumes: one context = one transaction = automatic commit/rollback at exit.

This worker requires: one context = multiple decision points with conditional commits.

**Specific requirements that conflict with UoW:**

1. **Retry logic requires partial commits**: When a transient error occurs, we must:
   - Rollback the current transaction
   - Increment the attempt counter
   - Commit that increment (so it persists across retries)
   - Sleep for backoff period
   - Return without re-raising the exception

   UoW would auto-commit on exit, which doesn't match these semantics.

2. **Multiple error paths with different transaction outcomes**:
   - TransientError: rollback → increment attempts → commit → continue
   - ContentPolicyError: rollback → retry with fallback → commit → continue
   - PermanentError: rollback → mark failed → commit → continue

   Each path needs explicit transaction control.

3. **Batch processing isolation**: Each token in a batch must succeed/fail independently.
   One token's failure should NOT rollback other tokens' changes.

**Pattern used instead:**

- Each token gets its own database session (created in process_batch)
- Explicit session.commit() and session.rollback() calls at decision points
- TokenRepository used for data access, but without UoW wrapper

**Alternative considered and rejected:**

A "WorkerUoW" variant that doesn't auto-commit could work, but adds complexity
without clear benefit. Direct session management is more explicit and readable
for this multi-path transaction scenario.
"""

import asyncio
import time
from typing import Callable

import structlog
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from glisk.core.config import Settings
from glisk.models.token import Token, TokenStatus
from glisk.repositories.author import AuthorRepository
from glisk.repositories.token import TokenRepository
from glisk.services.image_generation.prompt_validator import validate_prompt
from glisk.services.image_generation.replicate_client import (
    ContentPolicyError,
    PermanentError,
    TransientError,
    generate_image,
)

logger = structlog.get_logger(__name__)


async def process_single_token(
    token: Token,
    session_factory: Callable,
    settings: Settings,
) -> None:
    """Process a single token for image generation with retry logic.

    Creates its own database session to ensure transaction isolation from
    concurrent token processing. This prevents one token's failure from
    affecting other tokens in the batch.

    Workflow:
    1. Create dedicated session for this token
    2. Fetch token by ID (with fresh session)
    3. Update status: detected → generating
    4. Fetch author's prompt text
    5. Validate prompt
    6. Call Replicate API to generate image
    7. Handle errors:
       - TransientError: Increment attempts, reset to detected for retry
       - ContentPolicyError: Retry with fallback prompt
       - PermanentError: Mark as failed
       - Max retries (3): Mark as failed
    8. Update token with image URL and status: generating → uploading

    Args:
        token: Token entity to process (detached from session)
        session_factory: Factory function to create new database sessions
        settings: Application settings (API tokens, config)

    Raises:
        Exception: Any error during processing (caller should handle)
    """
    start_time = time.time()

    # Create dedicated session for this token's processing
    async with session_factory() as session:
        token_repo = TokenRepository(session)
        author_repo = AuthorRepository(session)

        # Step 1: Fetch token by ID (attach to this session)
        token_id_to_fetch = token.token_id
        attached_token = await token_repo.get_by_token_id(token_id_to_fetch)
        if not attached_token:
            raise ValueError(f"Token {token_id_to_fetch} not found")

        attempt_number = attached_token.generation_attempts + 1

        # Log start of processing
        logger.info(
            "token.generation.started",
            token_id=attached_token.token_id,
            attempt_number=attempt_number,
        )

        # Step 2: Mark token as generating
        attached_token.mark_generating()
        session.add(attached_token)
        await session.commit()
        await session.refresh(attached_token)

        try:
            # Step 3: Fetch author's prompt text
            author = await author_repo.get_by_id(attached_token.author_id)

            # Use author's prompt if found and set, otherwise use default author's prompt
            if not author or not author.prompt_text:
                if not author:
                    logger.warning(
                        "author_not_found_using_default",
                        author_id=str(attached_token.author_id),
                        token_id=attached_token.token_id,
                        default_wallet=settings.glisk_default_author_wallet,
                    )
                else:
                    logger.info(
                        "author_prompt_not_set_using_default",
                        author_wallet=author.wallet_address,
                        token_id=attached_token.token_id,
                        default_wallet=settings.glisk_default_author_wallet,
                    )

                # Fetch default author's prompt
                default_author = await author_repo.get_by_wallet(
                    settings.glisk_default_author_wallet
                )
                if not default_author:
                    raise ValueError(
                        f"Default author not found: {settings.glisk_default_author_wallet}. "
                        "Create default author in database."
                    )
                if not default_author.prompt_text:
                    raise ValueError(
                        f"Default author {settings.glisk_default_author_wallet} has no prompt. "
                        "Update default author with a valid prompt."
                    )
                prompt_text = default_author.prompt_text
            else:
                prompt_text = author.prompt_text

            # Step 4: Validate prompt
            prompt = validate_prompt(prompt_text)

            # Step 5: Generate image via Replicate
            image_url = await generate_image(
                prompt=prompt,
                api_token=settings.replicate_api_token,
                model_version=settings.replicate_model_version,
            )

            # Step 6: Update token with image URL and mark as uploading
            await token_repo.update_image_url(attached_token, image_url)
            await session.commit()

            # Log successful completion with duration and image URL
            duration = time.time() - start_time
            logger.info(
                "token.generation.succeeded",
                token_id=attached_token.token_id,
                image_url=image_url,
                duration_seconds=duration,
                attempt_number=attempt_number,
            )

        except TransientError as e:
            # Transient error (network timeout, rate limit, service unavailable)
            # Retry infinitely via natural poll loop - no retry limits
            await session.rollback()

            # Increment attempts (monitoring only, not used for business logic)
            await token_repo.increment_attempts(attached_token, str(e))
            await session.commit()

            logger.warning(
                "token.generation.retry",
                token_id=attached_token.token_id,
                error_type="TransientError",
                error_message=str(e),
                attempt_number=attempt_number,
            )
            # Return immediately - next poll will retry

        except ContentPolicyError as e:
            # Content policy violation - retry with fallback prompt
            await session.rollback()

            # Log censorship event
            logger.warning(
                "token.censored",
                token_id=attached_token.token_id,
                original_prompt="[redacted]",
                reason="content_policy_violation",
            )

            # Retry with fallback prompt
            try:
                image_url = await generate_image(
                    prompt=settings.fallback_censored_prompt,
                    api_token=settings.replicate_api_token,
                    model_version=settings.replicate_model_version,
                )

                # Update token with fallback image
                await token_repo.update_image_url(attached_token, image_url)
                # Increment attempts to track censorship
                attached_token.generation_attempts += 1
                session.add(attached_token)
                await session.commit()

                duration = time.time() - start_time
                logger.info(
                    "token.generation.succeeded",
                    token_id=attached_token.token_id,
                    image_url=image_url,
                    duration_seconds=duration,
                    attempt_number=attempt_number,
                    fallback_used=True,
                )
            except Exception as fallback_error:
                # Fallback also failed
                await session.rollback()
                await token_repo.mark_failed(
                    attached_token, f"Fallback prompt failed: {str(fallback_error)}"
                )
                await session.commit()
                logger.error(
                    "token.generation.failed",
                    token_id=attached_token.token_id,
                    error_type="ContentPolicyError",
                    error_message=f"Original: {str(e)}, Fallback: {str(fallback_error)}",
                    attempt_number=attempt_number,
                )

        except PermanentError as e:
            # Permanent error (invalid API token, validation error)
            await session.rollback()
            await token_repo.mark_failed(attached_token, str(e))
            await session.commit()
            logger.error(
                "token.generation.failed",
                token_id=attached_token.token_id,
                error_type="PermanentError",
                error_message=str(e),
                attempt_number=attempt_number,
            )

        except ValueError as e:
            # Prompt validation error - treat as permanent
            await session.rollback()
            await token_repo.mark_failed(attached_token, f"Prompt validation failed: {str(e)}")
            await session.commit()
            logger.error(
                "token.generation.failed",
                token_id=attached_token.token_id,
                error_type="ValueError",
                error_message=f"Prompt validation failed: {str(e)}",
                attempt_number=attempt_number,
            )

        except Exception as e:
            # Unexpected error - rollback and re-raise for batch error handling
            await session.rollback()
            logger.error(
                "token.generation.failed",
                token_id=attached_token.token_id,
                error_type=type(e).__name__,
                error_message=str(e),
                attempt_number=attempt_number,
            )
            raise


async def process_batch(
    session_factory: Callable,
    settings: Settings,
) -> None:
    """Process a batch of tokens concurrently for image generation.

    Uses a temporary session to lock tokens via FOR UPDATE SKIP LOCKED,
    then creates separate sessions for each token to ensure transaction isolation.

    Workflow:
    1. Create temporary session for locking
    2. Lock tokens via get_pending_for_generation() (FOR UPDATE SKIP LOCKED)
    3. Close locking session (tokens are detached from session)
    4. Process tokens concurrently with separate sessions per token
    5. Log successes and failures

    Args:
        session_factory: Factory function to create new database sessions
        settings: Application settings (batch size, API tokens)
    """
    # Step 1-2: Lock tokens with temporary session
    async with session_factory() as lock_session:
        token_repo = TokenRepository(lock_session)
        tokens = await token_repo.get_pending_for_generation(limit=settings.worker_batch_size)

    # Step 3: Session closed, tokens are now detached

    if not tokens:
        # No tokens to process
        return

    # Step 4: Process tokens concurrently (each gets its own session)
    tasks = [process_single_token(token, session_factory, settings) for token in tokens]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Step 5: Log errors (successes are logged in process_single_token)
    for token, result in zip(tokens, results):
        if isinstance(result, Exception):
            logger.error(
                "token.generation.failed",
                token_id=token.token_id,
                error=str(result),
                error_type=type(result).__name__,
            )


async def recover_orphaned_tokens(session: AsyncSession) -> None:
    """Reset tokens stuck in 'generating' status on startup.

    Worker crashes or restarts leave tokens in 'generating' status.
    All orphaned tokens are reset regardless of attempt count.

    Query:
        UPDATE tokens_s0
        SET status = 'detected'
        WHERE status = 'generating'

    Args:
        session: Database session for recovery query
    """
    result = await session.execute(
        update(Token)
        .where(Token.status == TokenStatus.GENERATING)  # type: ignore[arg-type]
        .values(status=TokenStatus.DETECTED)
    )
    await session.commit()

    recovered_count = result.rowcount  # type: ignore[attr-defined]
    if recovered_count > 0:
        logger.info("worker.recovery", orphaned_tokens_reset=recovered_count)


async def run_image_generation_worker(
    session_factory: Callable,
    settings: Settings,
) -> None:
    """Main worker loop for image generation.

    Polls at POLL_INTERVAL_SECONDS, processes batches, and handles graceful shutdown.

    Workflow:
    1. Run startup recovery (reset orphaned tokens)
    2. Poll at configured interval
    3. Call process_batch() with new session
    4. Handle CancelledError for graceful shutdown
    5. Log worker start/stop events

    Args:
        session_factory: Factory function that creates database sessions
        settings: Application settings (poll interval, batch size, API tokens)
    """
    # Startup recovery: reset orphaned tokens
    async with session_factory() as session:
        await recover_orphaned_tokens(session)

    logger.info(
        "worker.started",
        poll_interval=settings.poll_interval_seconds,
        batch_size=settings.worker_batch_size,
    )

    try:
        while True:
            try:
                # Process batch (creates sessions internally per token)
                await process_batch(session_factory, settings)

                # Wait for next polling interval
                await asyncio.sleep(settings.poll_interval_seconds)

            except asyncio.CancelledError:
                # Propagate cancellation for graceful shutdown
                raise

            except Exception as e:
                # Unexpected error in polling loop - log and continue with backoff
                logger.error(
                    "worker.error",
                    error_type=type(e).__name__,
                    error_message=str(e),
                    exc_info=True,
                )
                # Back off 5 seconds before retrying
                await asyncio.sleep(5)

    except asyncio.CancelledError:
        # Graceful shutdown
        logger.info("worker.stopped")
        raise
