"""Replicate API client for image generation with error classification."""


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
