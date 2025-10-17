"""Replicate API client for image generation with error classification."""

import asyncio
import os
from typing import Any, Optional

import replicate
from replicate.exceptions import ReplicateError as ReplicateAPIError


class ReplicateError(Exception):
    """Base class for categorized Replicate API errors."""

    retryable: bool = False


class TransientError(ReplicateError):
    """Transient errors that should be retried (network, rate limits, service unavailability)."""

    retryable = True


class ContentPolicyError(ReplicateError):
    """Content policy violation - should retry with fallback prompt."""

    retryable = True


class PermanentError(ReplicateError):
    """Permanent errors that should not be retried (auth, validation)."""

    retryable = False


def classify_error(exception: Exception) -> ReplicateError:
    """Classify exception into retry category.

    Args:
        exception: Original exception from Replicate SDK or network layer

    Returns:
        Classified ReplicateError subclass instance

    Classification rules:
        - Timeout errors → TransientError
        - 429 (rate limit) → TransientError
        - 503 (service unavailable) → TransientError
        - 401/403 (authentication) → PermanentError
        - Content policy violations → ContentPolicyError
        - Other HTTP errors → PermanentError
        - Connection errors → TransientError
    """
    error_message = str(exception)
    error_message_lower = error_message.lower()

    # Check for timeout errors
    if "timeout" in error_message_lower:
        return TransientError(f"Network timeout: {error_message}")

    # Check for rate limiting
    if "429" in error_message or "rate limit" in error_message_lower:
        return TransientError(f"Rate limit exceeded: {error_message}")

    # Check for service unavailability
    if "503" in error_message or "service unavailable" in error_message_lower:
        return TransientError(f"Service unavailable: {error_message}")

    # Check for authentication issues
    if (
        "401" in error_message
        or "403" in error_message
        or "unauthorized" in error_message_lower
        or "forbidden" in error_message_lower
        or "authentication" in error_message_lower
        or "invalid api token" in error_message_lower
    ):
        return PermanentError(f"Authentication failed: {error_message}")

    # Check for content policy violations
    if (
        "content policy" in error_message_lower
        or "nsfw" in error_message_lower
        or "safety" in error_message_lower
        or "inappropriate" in error_message_lower
    ):
        return ContentPolicyError(f"Content policy violation: {error_message}")

    # Check for connection errors (network layer)
    if isinstance(exception, (ConnectionError, OSError)):
        return TransientError(f"Connection error: {error_message}")

    # Default: treat as permanent error
    return PermanentError(f"Permanent error: {error_message}")


async def generate_image(prompt: str, api_token: str, model_version: Optional[str] = None) -> str:
    """Generate image using Replicate API.

    Args:
        prompt: Text prompt for image generation
        api_token: Replicate API authentication token
        model_version: Model identifier (default: "black-forest-labs/flux-schnell")

    Returns:
        Image URL from Replicate CDN (expires after 10 days)

    Raises:
        ReplicateError: Base class for all errors
        TransientError: Temporary failure, should retry
        ContentPolicyError: Content policy violation, should use fallback prompt
        PermanentError: Permanent failure, should not retry
    """
    if not api_token:
        raise PermanentError("REPLICATE_API_TOKEN not configured")

    model = model_version or "black-forest-labs/flux-schnell"

    try:
        # Set API token via environment (Replicate SDK reads from REPLICATE_API_TOKEN env var)
        # Run in thread pool as SDK is synchronous
        def _run_replicate() -> Any:
            # Temporarily set environment variable for this thread
            old_token = os.environ.get("REPLICATE_API_TOKEN")
            os.environ["REPLICATE_API_TOKEN"] = api_token
            try:
                return replicate.run(model, input={"prompt": prompt})
            finally:
                # Restore old token or remove if it didn't exist
                if old_token is not None:
                    os.environ["REPLICATE_API_TOKEN"] = old_token
                else:
                    os.environ.pop("REPLICATE_API_TOKEN", None)

        output = await asyncio.to_thread(_run_replicate)

        # Extract URL from output (format varies by model)
        if isinstance(output, list) and len(output) > 0:
            image_url = str(output[0])
        elif isinstance(output, str):
            image_url = output
        else:
            raise PermanentError(f"Unexpected output format from Replicate: {type(output)}")

        return image_url

    except ReplicateAPIError as e:
        # Classify and re-raise with appropriate error type
        classified = classify_error(e)
        raise classified from e

    except (ConnectionError, OSError, TimeoutError) as e:
        # Network-level errors
        classified = classify_error(e)
        raise classified from e

    except Exception as e:
        # Unexpected errors - treat as permanent to avoid infinite retries
        raise PermanentError(f"Unexpected error: {e}") from e
