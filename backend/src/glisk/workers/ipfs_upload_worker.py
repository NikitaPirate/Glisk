"""IPFS upload worker for processing tokens with generated images.

Polls for tokens with status='uploading', uploads images and metadata to IPFS via Pinata,
and updates token status to 'ready' for batch reveal.

This worker follows the same session-per-token pattern as image_generation_worker.py.
See that file for detailed justification of bypassing UoW pattern.
"""

import asyncio
import time
from typing import Callable

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from glisk.core.config import Settings
from glisk.models.token import Token
from glisk.repositories.ipfs_record import IPFSUploadRecordRepository
from glisk.repositories.token import TokenRepository
from glisk.services.exceptions import PermanentError, TransientError
from glisk.services.ipfs.pinata_client import PinataClient

logger = structlog.get_logger(__name__)


def build_metadata(token: Token, image_cid: str) -> dict:
    """Build ERC721 metadata JSON for token.

    Args:
        token: Token model instance
        image_cid: IPFS CID of uploaded image

    Returns:
        ERC721 metadata dictionary with keys:
        - name (str): Token name (e.g., "GLISK S0 #123")
        - description (str): Token description with social link
        - image (str): IPFS URI (ipfs://<image_cid>)
        - attributes (list): Empty array for MVP
    """
    return {
        "name": f"GLISK S0 #{token.token_id}",
        "description": "GLISK Season 0. https://x.com/getglisk",
        "image": f"ipfs://{image_cid}",
        "attributes": [],
    }


async def process_single_token(
    token: Token,
    session_factory: Callable,
    settings: Settings,
) -> None:
    """Process a single token for IPFS upload with retry logic.

    Creates its own database session to ensure transaction isolation.

    Workflow:
    1. Create dedicated session for this token
    2. Fetch token by ID (attach to session)
    3. Create Pinata client
    4. Upload image to IPFS → get image CID
    5. Build metadata with image CID
    6. Upload metadata to IPFS → get metadata CID
    7. Update token with CIDs and status: uploading → ready
    8. Create audit records for both uploads
    9. Handle errors:
       - TransientError: Increment attempts, keep status='uploading' for retry
       - PermanentError: Mark as failed
       - Max retries (3): Mark as failed

    Args:
        token: Token entity to process (detached from session)
        session_factory: Factory function to create new database sessions
        settings: Application settings (Pinata JWT, config)
    """
    start_time = time.time()

    # Create dedicated session for this token's processing
    async with session_factory() as session:
        token_repo = TokenRepository(session)
        ipfs_repo = IPFSUploadRecordRepository(session)

        # Step 1: Fetch token by ID (attach to this session)
        attached_token = await token_repo.get_by_token_id(token.token_id)
        if not attached_token:
            raise ValueError(f"Token {token.token_id} not found")

        attempt_number = attached_token.generation_attempts + 1

        # Log start of processing
        logger.info(
            "ipfs.upload.started",
            token_id=attached_token.token_id,
            attempt_number=attempt_number,
        )

        # Create Pinata client
        pinata = PinataClient(
            jwt_token=settings.pinata_jwt,
            gateway_domain=settings.pinata_gateway,
        )

        try:
            # Step 2: Upload image to IPFS
            if not attached_token.image_url:
                raise ValueError(f"Token {attached_token.token_id} has no image_url")

            image_cid = await pinata.upload_image(attached_token.image_url, attached_token.token_id)
            logger.info(
                "ipfs.image_uploaded",
                token_id=attached_token.token_id,
                cid=image_cid,
                attempt_number=attempt_number,
            )

            # Create audit record for image upload
            await ipfs_repo.create(
                token_id=attached_token.id,
                record_type="image",
                cid=image_cid,
                status="completed",
                retry_count=attempt_number - 1,
            )

            # Step 3: Build metadata
            metadata = build_metadata(attached_token, image_cid)

            # Step 4: Upload metadata to IPFS
            metadata_cid = await pinata.upload_metadata(metadata, attached_token.token_id)
            logger.info(
                "ipfs.metadata_uploaded",
                token_id=attached_token.token_id,
                cid=metadata_cid,
                attempt_number=attempt_number,
            )

            # Create audit record for metadata upload
            await ipfs_repo.create(
                token_id=attached_token.id,
                record_type="metadata",
                cid=metadata_cid,
                status="completed",
                retry_count=attempt_number - 1,
            )

            # Step 5: Update token with CIDs and mark as ready
            await token_repo.update_ipfs_cids(attached_token, image_cid, metadata_cid)
            await session.commit()

            # Log successful completion
            duration = time.time() - start_time
            logger.info(
                "ipfs.upload.succeeded",
                token_id=attached_token.token_id,
                image_cid=image_cid,
                metadata_cid=metadata_cid,
                duration_seconds=duration,
                attempt_number=attempt_number,
            )

        except TransientError as e:
            # Transient error (network timeout, rate limit, service unavailable)
            await session.rollback()

            # Check if max retries exceeded
            if attached_token.generation_attempts >= 2:  # 0-indexed, so >= 2 means 3rd attempt
                # Max retries exhausted
                await token_repo.mark_failed(attached_token, f"Max IPFS retries exceeded: {str(e)}")
                await session.commit()

                # Create audit record for failure
                await ipfs_repo.create(
                    token_id=attached_token.id,
                    record_type="metadata",  # Last attempted operation
                    cid=None,
                    status="failed",
                    retry_count=attached_token.generation_attempts,
                )
                await session.commit()

                logger.error(
                    "ipfs.upload.exhausted",
                    token_id=attached_token.token_id,
                    attempts=attached_token.generation_attempts + 1,
                    last_error=str(e),
                )
            else:
                # Increment attempts and keep status='uploading' for retry
                attached_token.generation_attempts += 1
                attached_token.generation_error = str(e)[:1000]
                session.add(attached_token)
                await session.commit()

                # Exponential backoff: 2^attempts seconds (1s, 2s, 4s)
                backoff_seconds = 2**attached_token.generation_attempts
                await asyncio.sleep(backoff_seconds)

                logger.warning(
                    "ipfs.transient_error",
                    token_id=attached_token.token_id,
                    error_type="TransientError",
                    error_message=str(e),
                    attempt_number=attempt_number,
                    max_attempts=3,
                    backoff_seconds=backoff_seconds,
                )

        except PermanentError as e:
            # Permanent error (authentication, validation)
            await session.rollback()
            await token_repo.mark_failed(attached_token, f"IPFS upload failed: {str(e)}")
            await session.commit()

            # Create audit record for failure
            await ipfs_repo.create(
                token_id=attached_token.id,
                record_type="metadata",  # Last attempted operation
                cid=None,
                status="failed",
                retry_count=attached_token.generation_attempts,
            )
            await session.commit()

            logger.error(
                "ipfs.permanent_error",
                token_id=attached_token.token_id,
                error_type="PermanentError",
                error_message=str(e),
                attempt_number=attempt_number,
            )

        except ValueError as e:
            # Missing data - treat as permanent
            await session.rollback()
            await token_repo.mark_failed(attached_token, f"IPFS upload failed: {str(e)}")
            await session.commit()
            logger.error(
                "ipfs.upload.failed",
                token_id=attached_token.token_id,
                error_type="ValueError",
                error_message=str(e),
                attempt_number=attempt_number,
            )

        except Exception as e:
            # Unexpected error - rollback and re-raise
            await session.rollback()
            logger.error(
                "ipfs.upload.failed",
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
    """Process a batch of tokens concurrently for IPFS upload.

    Uses a temporary session to lock tokens via FOR UPDATE SKIP LOCKED,
    then creates separate sessions for each token to ensure transaction isolation.

    Args:
        session_factory: Factory function to create new database sessions
        settings: Application settings (batch size, Pinata JWT)
    """
    # Lock tokens with temporary session
    async with session_factory() as lock_session:
        token_repo = TokenRepository(lock_session)
        tokens = await token_repo.get_pending_for_upload(limit=settings.worker_batch_size)

    # Session closed, tokens are now detached

    if not tokens:
        # No tokens to process
        return

    # Process tokens concurrently (each gets its own session)
    tasks = [process_single_token(token, session_factory, settings) for token in tokens]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Log errors (successes are logged in process_single_token)
    for token, result in zip(tokens, results):
        if isinstance(result, Exception):
            logger.error(
                "ipfs.upload.failed",
                token_id=token.token_id,
                error=str(result),
                error_type=type(result).__name__,
            )


async def recover_orphaned_tokens(session: AsyncSession) -> None:
    """Reset tokens stuck in 'uploading' status on startup.

    Worker crashes or restarts leave tokens in 'uploading' status.
    This function leaves them as-is (status='uploading' is stable, ready for retry).

    Unlike 'generating' status, 'uploading' tokens are already past the image generation
    phase, so they just need to be picked up by the worker again.

    Args:
        session: Database session for recovery query
    """
    # For IPFS upload, 'uploading' is a stable state - no recovery needed
    # Tokens will be picked up on next poll if they have retry budget
    logger.info("worker.recovery", message="IPFS upload worker started (no orphan recovery needed)")


async def run_ipfs_upload_worker(
    session_factory: Callable,
    settings: Settings,
) -> None:
    """Main worker loop for IPFS upload.

    Polls at POLL_INTERVAL_SECONDS, processes batches, and handles graceful shutdown.

    Args:
        session_factory: Factory function that creates database sessions
        settings: Application settings (poll interval, batch size, Pinata JWT)
    """
    # Startup recovery (no-op for IPFS upload)
    async with session_factory() as session:
        await recover_orphaned_tokens(session)

    logger.info(
        "worker.started",
        worker_type="ipfs_upload",
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
                    worker_type="ipfs_upload",
                    error_type=type(e).__name__,
                    error_message=str(e),
                    exc_info=True,
                )
                # Back off 5 seconds before retrying
                await asyncio.sleep(5)

    except asyncio.CancelledError:
        # Graceful shutdown
        logger.info("worker.stopped", worker_type="ipfs_upload")
        raise
