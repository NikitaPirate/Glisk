# Internal Service Contracts: IPFS Upload and Batch Reveal

**Feature**: 003-003d-ipfs-reveal
**Date**: 2025-10-17
**Phase**: 1 - Design & Contracts

## Overview

This document defines the internal API contracts for services used by IPFS upload and reveal workers. These are **not external HTTP APIs**, but Python service classes with well-defined interfaces. Contracts specify method signatures, return types, error conditions, and usage patterns.

---

## Service 1: Pinata Client

**Module**: `backend/src/glisk/services/ipfs/pinata_client.py`

**Purpose**: Upload images and metadata JSON to IPFS via Pinata API. Handles authentication, error classification, and CID extraction.

### Class: PinataClient

```python
class PinataClient:
    """IPFS upload client using Pinata pinning service."""

    def __init__(self, jwt_token: str, gateway_domain: str = "gateway.pinata.cloud"):
        """
        Initialize Pinata client.

        Args:
            jwt_token: Pinata API JWT token (from PINATA_JWT env var)
            gateway_domain: Gateway domain for URL generation (default: public gateway)
        """
        pass

    async def upload_image(self, image_url: str) -> str:
        """
        Download image from URL and upload to IPFS via Pinata.

        Args:
            image_url: HTTP/HTTPS URL of image to upload (e.g., Replicate CDN URL)

        Returns:
            IPFS CID (Content Identifier) as string (CIDv1 format, e.g., "bafkrei...")

        Raises:
            TransientError: Network timeout, rate limit (429), service unavailable (503)
            PermanentError: Invalid API key (401), forbidden (403), bad request (400)

        Example:
            cid = await client.upload_image("https://replicate.delivery/pbxt/abc123/out.png")
            # Returns: "bafkreih5aznjvttude6c3wbvqeebb6rlx5wkbzyppv7garjiubll2ceym4"
        """
        pass

    async def upload_metadata(self, metadata: dict[str, Any]) -> str:
        """
        Upload metadata JSON to IPFS via Pinata.

        Args:
            metadata: ERC721 metadata dictionary with keys:
                - name (str): Token name
                - description (str): Token description
                - image (str): IPFS URI (ipfs://<CID>)
                - attributes (list, optional): Array of trait objects

        Returns:
            IPFS CID (Content Identifier) as string (CIDv1 format)

        Raises:
            TransientError: Network timeout, rate limit (429), service unavailable (503)
            PermanentError: Invalid API key (401), forbidden (403), bad request (400)

        Example:
            metadata = {
                "name": "Token #123",
                "description": "Generated NFT from Season 0",
                "image": "ipfs://bafkreih5aznjvttude6c3wbvqeebb6rlx5wkbzyppv7garjiubll2ceym4",
                "attributes": []
            }
            cid = await client.upload_metadata(metadata)
            # Returns: "bafkreihjk9abc123..."
        """
        pass

    def get_gateway_url(self, cid: str) -> str:
        """
        Convert CID to gateway URL for browser access.

        Args:
            cid: IPFS CID

        Returns:
            Gateway URL (e.g., "https://gateway.pinata.cloud/ipfs/<CID>")

        Example:
            url = client.get_gateway_url("bafkreih5aznjvttude...")
            # Returns: "https://gateway.pinata.cloud/ipfs/bafkreih5aznjvttude..."
        """
        pass
```

### Error Classification

**Transient Errors** (caller should retry with exponential backoff):

```python
class TransientError(Exception):
    """Transient error that may succeed on retry."""
    pass
```

| HTTP Status | Condition | Retry Strategy |
|-------------|-----------|----------------|
| 429 | Rate limit exceeded | Read `Retry-After` header, wait + jitter (0-5s) |
| 500 | Internal server error | Exponential backoff: 1s → 2s → 4s (max 3 attempts) |
| 503 | Service unavailable | Exponential backoff: 1s → 2s → 4s (max 3 attempts) |
| Network timeout | Request exceeds 30s timeout | Exponential backoff: 1s → 2s → 4s |

**Permanent Errors** (caller should mark token as failed):

```python
class PermanentError(Exception):
    """Permanent error that will not succeed on retry."""
    pass
```

| HTTP Status | Condition | Action |
|-------------|-----------|--------|
| 400 | Bad request (invalid JSON, missing fields) | Log error, mark token failed |
| 401 | Unauthorized (invalid/missing API key) | Log error, halt worker (configuration issue) |
| 403 | Forbidden (quota exceeded, account suspended) | Log error, halt worker (requires manual intervention) |

### Usage Example

```python
from glisk.services.ipfs.pinata_client import PinataClient, TransientError, PermanentError
from glisk.core.config import settings
import structlog

logger = structlog.get_logger()

client = PinataClient(
    jwt_token=settings.pinata_jwt,
    gateway_domain=settings.pinata_gateway
)

try:
    # Upload image
    image_cid = await client.upload_image(token.image_url)
    logger.info("ipfs.image_uploaded", token_id=token.token_id, cid=image_cid)

    # Build and upload metadata
    metadata = {
        "name": f"Token #{token.token_id}",
        "description": "Generated NFT from Season 0",
        "image": f"ipfs://{image_cid}",
        "attributes": []
    }
    metadata_cid = await client.upload_metadata(metadata)
    logger.info("ipfs.metadata_uploaded", token_id=token.token_id, cid=metadata_cid)

    # Update token
    await token_repo.update_ipfs_cids(token, image_cid, metadata_cid)

except TransientError as e:
    # Retry with exponential backoff
    logger.warning("ipfs.transient_error", token_id=token.token_id, error=str(e))
    # Increment attempts, requeue for retry

except PermanentError as e:
    # Mark failed
    logger.error("ipfs.permanent_error", token_id=token.token_id, error=str(e))
    await token_repo.mark_failed(token, str(e))
```

---

## Service 2: Keeper Service

**Module**: `backend/src/glisk/services/blockchain/keeper.py`

**Purpose**: Submit batch reveal transactions to blockchain network using keeper wallet. Handles gas estimation, transaction signing, submission, and confirmation monitoring.

### Class: KeeperService

```python
class KeeperService:
    """Blockchain keeper service for batch reveal operations."""

    def __init__(
        self,
        w3: Web3,
        contract_address: str,
        keeper_private_key: str,
        gas_buffer_percentage: float = 0.20,
        transaction_timeout: int = 180,
    ):
        """
        Initialize keeper service.

        Args:
            w3: Web3 instance (connected to Base L2)
            contract_address: GliskNFT contract address
            keeper_private_key: Private key for keeper wallet (0x-prefixed hex)
            gas_buffer_percentage: Safety buffer for gas estimation (default: 0.20 = 20%)
            transaction_timeout: Max wait time for confirmation in seconds (default: 180)
        """
        pass

    async def reveal_batch(
        self,
        token_ids: list[int],
        metadata_uris: list[str],
    ) -> tuple[str, int, int]:
        """
        Submit batch reveal transaction to blockchain and wait for confirmation.

        Args:
            token_ids: Array of token IDs to reveal (length 1-50)
            metadata_uris: Array of metadata URIs (ipfs://<CID> format, same length as token_ids)

        Returns:
            Tuple of (tx_hash, block_number, gas_used)
            - tx_hash: Transaction hash (0x-prefixed hex string)
            - block_number: Block number where transaction confirmed
            - gas_used: Actual gas used by transaction

        Raises:
            TransientError: Gas estimation failed, submission failed, confirmation timeout
            PermanentError: Transaction reverted on-chain, invalid parameters

        Example:
            tx_hash, block_num, gas = await keeper.reveal_batch(
                token_ids=[123, 124, 125],
                metadata_uris=[
                    "ipfs://bafkreiabc123...",
                    "ipfs://bafkreixyz456...",
                    "ipfs://bafkreiqwe789..."
                ]
            )
            # Returns: ("0xabcdef123...", 98765432, 145000)
        """
        pass

    async def estimate_gas(
        self,
        token_ids: list[int],
        metadata_uris: list[str],
    ) -> tuple[int, int, int]:
        """
        Estimate gas parameters for batch reveal transaction.

        Args:
            token_ids: Array of token IDs to reveal
            metadata_uris: Array of metadata URIs

        Returns:
            Tuple of (gas_limit, max_fee_per_gas, max_priority_fee_per_gas)
            - gas_limit: Estimated gas limit with buffer applied (wei)
            - max_fee_per_gas: EIP-1559 max fee per gas with buffer (wei)
            - max_priority_fee_per_gas: EIP-1559 priority fee with buffer (wei)

        Raises:
            TransientError: RPC error, network timeout, estimation failure

        Example:
            gas_limit, max_fee, priority_fee = await keeper.estimate_gas(
                token_ids=[123, 124],
                metadata_uris=["ipfs://...", "ipfs://..."]
            )
            # Returns: (180000, 4600000000, 600000000)
        """
        pass

    def get_keeper_address(self) -> str:
        """
        Get keeper wallet address.

        Returns:
            Ethereum address (checksummed, 0x-prefixed)

        Example:
            address = keeper.get_keeper_address()
            # Returns: "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"
        """
        pass
```

### Error Classification

**Transient Errors** (caller should retry on next poll):

```python
class TransientError(Exception):
    """Transient error that may succeed on retry."""
    pass
```

| Condition | Error Message | Retry Strategy |
|-----------|---------------|----------------|
| Gas estimation fails | "Gas estimation failed: <details>" | Retry on next poll (5s delay) |
| Transaction submission fails | "Transaction submission failed: <details>" | Retry on next poll (nonce may need refresh) |
| Confirmation timeout (180s) | "Transaction confirmation timeout: <tx_hash>" | Retry on next poll (transaction may confirm later) |
| Network RPC error | "RPC error: <details>" | Retry on next poll |

**Permanent Errors** (caller should log for manual investigation):

```python
class PermanentError(Exception):
    """Permanent error requiring manual investigation."""
    pass
```

| Condition | Error Message | Action |
|-----------|---------------|--------|
| Transaction reverts | "Transaction reverted: <revert_reason>" | Log error, tokens remain 'ready', investigate revert reason |
| Invalid token IDs | "Invalid parameters: <details>" | Log error, investigate why validation failed |

### Usage Example

```python
from glisk.services.blockchain.keeper import KeeperService, TransientError, PermanentError
from glisk.core.config import settings
from web3 import Web3
import structlog

logger = structlog.get_logger()

# Initialize Web3 and keeper service
w3 = Web3(Web3.HTTPProvider(f"https://base-sepolia.g.alchemy.com/v2/{settings.alchemy_api_key}"))
keeper = KeeperService(
    w3=w3,
    contract_address=settings.glisk_nft_contract_address,
    keeper_private_key=settings.keeper_private_key,
    gas_buffer_percentage=settings.reveal_gas_buffer,
    transaction_timeout=settings.transaction_timeout_seconds,
)

try:
    # Prepare batch
    token_ids = [t.token_id for t in tokens]
    metadata_uris = [f"ipfs://{t.metadata_cid}" for t in tokens]

    # Estimate gas (optional, reveal_batch does this internally)
    gas_limit, max_fee, priority_fee = await keeper.estimate_gas(token_ids, metadata_uris)
    logger.info("reveal.gas_estimated",
        token_count=len(token_ids),
        gas_limit=gas_limit,
        max_fee_per_gas=max_fee)

    # Submit batch reveal
    tx_hash, block_number, gas_used = await keeper.reveal_batch(token_ids, metadata_uris)
    logger.info("reveal.batch_confirmed",
        tx_hash=tx_hash,
        block_number=block_number,
        gas_used=gas_used,
        token_count=len(token_ids))

    # Update tokens and audit record
    await token_repo.mark_revealed(tokens, tx_hash)
    await reveal_tx_repo.mark_confirmed(tx_hash, block_number, gas_used)

except TransientError as e:
    # Retry on next poll
    logger.warning("reveal.transient_error", error=str(e))
    # Tokens remain in 'ready' state, retry next poll

except PermanentError as e:
    # Manual investigation required
    logger.error("reveal.permanent_error", error=str(e), token_ids=token_ids)
    # Tokens remain in 'ready' state, investigate revert reason
```

---

## Service 3: Metadata Builder (Inline in Worker)

**Module**: `backend/src/glisk/workers/ipfs_upload_worker.py` (inline function, not separate service)

**Purpose**: Build ERC721-compliant metadata JSON from token data. Inline implementation (20 LOC) per Constitution "Simplicity First" principle.

### Function: build_metadata

```python
def build_metadata(token: Token, image_cid: str, author: Author) -> dict[str, Any]:
    """
    Build ERC721 metadata JSON for token.

    Args:
        token: Token model instance
        image_cid: IPFS CID of uploaded image
        author: Author model instance (for prompt text)

    Returns:
        ERC721 metadata dictionary with keys:
        - name (str): Token name
        - description (str): Token description
        - image (str): IPFS URI (ipfs://<image_cid>)
        - attributes (list): Empty array for MVP (future: prompt, author, generation params)

    Example:
        metadata = build_metadata(token, "bafkreiabc123...", author)
        # Returns:
        # {
        #     "name": "Token #123",
        #     "description": "Generated NFT from Season 0 - Prompt: \"<author_prompt>\"",
        #     "image": "ipfs://bafkreiabc123...",
        #     "attributes": []
        # }
    """
    return {
        "name": f"Token #{token.token_id}",
        "description": f"Generated NFT from Season 0 - Prompt: \"{author.prompt_text}\"",
        "image": f"ipfs://{image_cid}",
        "attributes": [],  # Future: Add generation params, author info
    }
```

**Rationale for Inline**:
- Only 20 LOC (including docstring)
- Tightly coupled to IPFS upload worker (not reusable elsewhere)
- No complex logic (just dictionary construction)
- Per Constitution v1.1.0: "Repository pattern without generic base classes. Refactor only if >3 identical methods."
- Inline approach aligns with "Simplicity First" and "Clear Over Clever" principles

**When to Extract**:
- If metadata builder grows beyond 40 LOC
- If multiple workers need to build metadata (reusability trigger)
- If metadata logic becomes complex (e.g., dynamic attribute generation, image processing)

---

## Error Hierarchy

### Base Exceptions

```python
# File: backend/src/glisk/services/exceptions.py

class ServiceError(Exception):
    """Base exception for all service errors."""
    pass

class TransientError(ServiceError):
    """Transient error that may succeed on retry."""
    pass

class PermanentError(ServiceError):
    """Permanent error that will not succeed on retry."""
    pass
```

### Service-Specific Exceptions

```python
# IPFS Errors
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

# Blockchain Errors
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
```

---

## Configuration

### Environment Variables

**File**: `backend/.env.example` (additions)

```bash
# IPFS Upload (Pinata)
PINATA_JWT=your_pinata_jwt_token_here
PINATA_GATEWAY=gateway.pinata.cloud  # Default: public gateway

# Blockchain Keeper
KEEPER_PRIVATE_KEY=0x_your_private_key_here
KEEPER_GAS_STRATEGY=medium  # Options: slow, medium, fast (unused for EIP-1559)
REVEAL_GAS_BUFFER=1.2  # 20% safety buffer (float, e.g., 1.2 = 20%)
TRANSACTION_TIMEOUT_SECONDS=180  # Wait up to 3 minutes for confirmation

# Workers
BATCH_REVEAL_WAIT_SECONDS=5  # Wait 5 seconds to accumulate batch
BATCH_REVEAL_MAX_TOKENS=50  # Maximum tokens per batch
```

### Settings Class

**File**: `backend/src/glisk/core/config.py` (additions)

```python
class Settings(BaseSettings):
    # ... existing fields ...

    # IPFS (Pinata)
    pinata_jwt: str = Field(default="", alias="PINATA_JWT")
    pinata_gateway: str = Field(default="gateway.pinata.cloud", alias="PINATA_GATEWAY")

    # Blockchain (Keeper)
    keeper_private_key: str = Field(default="", alias="KEEPER_PRIVATE_KEY")
    keeper_gas_strategy: str = Field(default="medium", alias="KEEPER_GAS_STRATEGY")  # Unused for EIP-1559
    reveal_gas_buffer: float = Field(default=1.2, alias="REVEAL_GAS_BUFFER")
    transaction_timeout_seconds: int = Field(default=180, alias="TRANSACTION_TIMEOUT_SECONDS")

    # Workers
    batch_reveal_wait_seconds: int = Field(default=5, alias="BATCH_REVEAL_WAIT_SECONDS")
    batch_reveal_max_tokens: int = Field(default=50, alias="BATCH_REVEAL_MAX_TOKENS")

    @model_validator(mode="after")
    def validate_ipfs_reveal_config(self) -> "Settings":
        """Validate IPFS and reveal configuration on startup."""
        if self.app_env in ("test", "testing"):
            return self

        # PINATA_JWT is required for IPFS upload worker
        if not self.pinata_jwt:
            structlog.get_logger().warning(
                "config.validation.warning",
                message="PINATA_JWT not set - IPFS upload worker will fail",
                hint="Get your JWT token from https://pinata.cloud",
            )

        # KEEPER_PRIVATE_KEY is required for reveal worker
        if not self.keeper_private_key:
            structlog.get_logger().warning(
                "config.validation.warning",
                message="KEEPER_PRIVATE_KEY not set - reveal worker will fail",
                hint="Generate a keeper wallet and fund with ETH for gas",
            )

        return self
```

---

## Testing Strategy

### Unit Tests

**Pinata Client** (`test_pinata_client.py`):
- Test error classification (429 → TransientError, 401 → PermanentError)
- Test CID parsing from successful responses
- Mock HTTP requests (use `responses` library)

**Keeper Service** (`test_keeper_service.py`):
- Test gas estimation with buffer calculation
- Test transaction submission with nonce management
- Test revert detection (receipt.status == 0)
- Mock Web3 calls (use `eth-tester` or `unittest.mock`)

### Integration Tests

**IPFS Worker** (`test_ipfs_worker_integration.py`):
- Use testcontainers for PostgreSQL
- Mock Pinata API responses
- Test full upload flow (token → image CID → metadata CID → ready)
- Test retry logic (transient error → exponential backoff → success)
- Test failure handling (permanent error → failed status)

**Reveal Worker** (`test_reveal_worker_integration.py`):
- Use testcontainers for PostgreSQL
- Use `eth-tester` for local blockchain simulation
- Test batch accumulation (time trigger, size trigger)
- Test transaction submission and confirmation
- Test timeout handling (TimeExhausted exception)

### End-to-End Test

**Full Pipeline** (`test_e2e_pipeline.py`):
- Simulate full flow: detected → generating → uploading → ready → revealed
- Mock Replicate, Pinata, and blockchain responses
- Verify all state transitions
- Verify audit records created (ipfs_upload_records, reveal_transactions)

---

## Summary

**Service Contracts Defined**:
1. **PinataClient**: IPFS upload with error classification (TransientError, PermanentError)
2. **KeeperService**: Blockchain batch reveal with gas estimation and confirmation monitoring
3. **build_metadata()**: Inline metadata builder (20 LOC, no separate service)

**Error Hierarchy**:
- Base: `ServiceError` → `TransientError` / `PermanentError`
- Service-specific: `IPFSUploadError`, `BlockchainError` with typed subclasses

**Configuration**:
- Pinata: JWT token, gateway domain
- Keeper: Private key, gas buffer (20%), transaction timeout (180s)
- Workers: Batch wait time (5s), batch max size (50 tokens)

**Testing**:
- Unit tests: Mock HTTP and Web3 calls
- Integration tests: testcontainers + eth-tester
- E2E test: Full pipeline verification

All contracts follow Constitution v1.1.0 principles: Simplicity First, Clear Over Clever, backend standards (UTC, Alembic, repository pattern, testcontainers-first).
