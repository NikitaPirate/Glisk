"""Service error hierarchy for IPFS upload and blockchain operations.

This module defines the exception hierarchy for service-level errors:
- ServiceError: Base for all service errors
- TransientError: Retryable errors (network, rate limits, timeouts)
- PermanentError: Non-retryable errors (authentication, validation)
"""


class ServiceError(Exception):
    """Base exception for all service errors."""

    pass


class TransientError(ServiceError):
    """Transient error that may succeed on retry.

    Examples:
    - Network timeouts
    - Rate limit exceeded (429)
    - Service unavailable (503)
    - Gas estimation failures
    - Transaction submission failures
    """

    pass


class PermanentError(ServiceError):
    """Permanent error that will not succeed on retry.

    Examples:
    - Authentication failures (401, 403)
    - Invalid request parameters (400)
    - Transaction reverts
    - Configuration errors
    """

    pass


# IPFS-specific errors
class IPFSUploadError(ServiceError):
    """Base exception for IPFS upload errors."""

    pass


class IPFSRateLimitError(TransientError):
    """Rate limit exceeded (429)."""

    pass


class IPFSNetworkError(TransientError):
    """Network timeout or service unavailable."""

    pass


class IPFSAuthError(PermanentError):
    """Authentication failure (401, 403)."""

    pass


class IPFSValidationError(PermanentError):
    """Bad request (400)."""

    pass


# Blockchain-specific errors
class BlockchainError(ServiceError):
    """Base exception for blockchain errors."""

    pass


class GasEstimationError(TransientError):
    """Gas estimation failed."""

    pass


class TransactionSubmissionError(TransientError):
    """Transaction submission failed."""

    pass


class TransactionTimeoutError(TransientError):
    """Transaction confirmation timeout."""

    pass


class TransactionRevertError(PermanentError):
    """Transaction reverted on-chain."""

    pass


# Token Recovery-specific errors
class RecoveryError(ServiceError):
    """Base exception for token recovery errors."""

    pass


class BlockchainConnectionError(TransientError):
    """Failed to connect to blockchain RPC endpoint."""

    pass


class ContractNotFoundError(PermanentError):
    """Smart contract not found at specified address."""

    pass


class DefaultAuthorNotFoundError(PermanentError):
    """Default author wallet not found in authors table."""

    pass
