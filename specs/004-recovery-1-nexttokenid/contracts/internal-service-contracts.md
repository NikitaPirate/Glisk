# Internal Service Contracts: Simplified Token Recovery

**Branch**: `004-recovery-1-nexttokenid` | **Date**: 2025-10-18

## Overview

This document defines the internal contracts (interfaces and behaviors) for services and repositories involved in the simplified token recovery mechanism. These are not public APIs - they are internal boundaries between modules within the backend codebase.

---

## TokenRecoveryService

**Module**: `backend/src/glisk/services/blockchain/token_recovery.py`

**Purpose**: Orchestrates the recovery process by querying the smart contract, identifying missing tokens, and creating database records.

### Interface

```python
class TokenRecoveryService:
    """Service for recovering missing tokens from blockchain state."""

    def __init__(
        self,
        web3_provider: Web3,
        contract_address: str,
        contract_abi: list[dict],
    ):
        """Initialize recovery service with blockchain connection.

        Args:
            web3_provider: Web3 instance for RPC calls
            contract_address: GliskNFT contract address (checksummed)
            contract_abi: Contract ABI for nextTokenId() function
        """

    async def get_next_token_id(self) -> int:
        """Query smart contract's nextTokenId counter.

        Returns:
            Next token ID that will be minted (exclusive upper bound)

        Raises:
            BlockchainConnectionError: If RPC call fails after retries
            ContractNotFoundError: If contract address is invalid

        Example:
            If 10 tokens have been minted (IDs 1-10), returns 11
        """

    async def recover_missing_tokens(
        self,
        uow: UnitOfWork,
        limit: int | None = None,
        dry_run: bool = False,
    ) -> RecoveryResult:
        """Identify and create database records for missing tokens.

        Process:
        1. Query contract.nextTokenId()
        2. Query database for missing token IDs
        3. Lookup default author from config
        4. Create Token records with status=DETECTED
        5. Commit transaction (or rollback if dry_run)

        Args:
            uow: Unit of Work for database transaction
            limit: Optional cap on number of tokens to recover
            dry_run: If True, rollback transaction (don't persist changes)

        Returns:
            RecoveryResult with statistics and details

        Raises:
            DefaultAuthorNotFoundError: If GLISK_DEFAULT_AUTHOR_WALLET not in DB
            BlockchainConnectionError: If contract query fails
        """


@dataclass
class RecoveryResult:
    """Result of a recovery operation."""

    total_on_chain: int  # Value from nextTokenId()
    total_in_db: int  # Count of tokens in database before recovery
    missing_count: int  # Number of gaps identified
    recovered_count: int  # Number of tokens created (may be less if duplicates)
    skipped_duplicate_count: int  # Tokens already created by webhook during recovery
    errors: list[str]  # Any non-fatal errors encountered
```

### Behavior Contracts

**`get_next_token_id()`**:
- **Pre-condition**: web3_provider is connected to network
- **Post-condition**: Returns integer >= 1 (contract starts token IDs at 1)
- **Idempotency**: Safe to call multiple times, returns current contract state
- **Error Handling**: Retries RPC call up to 3 times with exponential backoff (1s, 2s, 4s)

**`recover_missing_tokens()`**:
- **Pre-condition**: uow is an active transaction context
- **Post-condition**: If successful, database contains all tokens from [1, nextTokenId-1]
- **Atomicity**: All tokens created in single transaction. If any error, entire batch rolls back.
- **Idempotency**: Safe to run multiple times. Duplicate token_id raises IntegrityError, which is caught and logged. Operation continues with next token.
- **Error Handling**: Fatal errors (network down, DB connection lost) raise exception and rollback. Non-fatal errors (duplicate token) log and continue.

---

## TokenRepository (Extended)

**Module**: `backend/src/glisk/repositories/token.py`

**Purpose**: Data access layer for Token entities. Extended with recovery-specific query.

### New Method

```python
async def get_missing_token_ids(
    self,
    max_token_id: int,
    limit: int | None = None,
) -> list[int]:
    """Retrieve token IDs missing from database within on-chain range.

    Uses PostgreSQL generate_series() to create expected range,
    then LEFT JOIN to identify gaps.

    Args:
        max_token_id: Upper bound from contract.nextTokenId() (exclusive)
        limit: Optional cap on result count (for batching large gaps)

    Returns:
        List of missing token IDs in ascending order

    Raises:
        None (empty list if no gaps)

    Example:
        max_token_id=11 (expect tokens 0-10)
        DB contains: [0, 1, 2, 5, 6, 7]
        Returns: [3, 4, 8, 9, 10]

    Performance:
        - O(n) where n = max_token_id (single table scan)
        - Sub-second for max_token_id up to 100,000
        - Uses index on tokens_s0.token_id for LEFT JOIN
    """
```

### Behavior Contracts

**`get_missing_token_ids()`**:
- **Pre-condition**: max_token_id >= 0 (contract never decreases except on chain reorg)
- **Post-condition**: Returns sorted list of integers in range [0, max_token_id-1]
- **Edge Cases**:
  - max_token_id=0: Returns empty list (no tokens minted yet)
  - max_token_id=1, DB empty: Returns [0]
  - All tokens present: Returns empty list
  - max_token_id=100000, DB empty: Returns [0..99999] (may want to apply limit)
- **Performance**: If result set is large (10k+ tokens), consider calling with limit and processing in batches

---

## AuthorRepository (Unchanged)

**Module**: `backend/src/glisk/repositories/author.py`

**Purpose**: Data access layer for Author entities. Used to lookup default author.

### Relevant Method (Existing)

```python
async def get_by_wallet(self, wallet_address: str) -> Author | None:
    """Retrieve author by Ethereum wallet address.

    Args:
        wallet_address: Ethereum address (checksummed or lowercase)

    Returns:
        Author if found, None otherwise
    """
```

### Usage in Recovery

```python
default_wallet = config.GLISK_DEFAULT_AUTHOR_WALLET
default_author = await uow.authors.get_by_wallet(default_wallet)
if not default_author:
    raise DefaultAuthorNotFoundError(
        f"Default author wallet {default_wallet} not found in database. "
        "Run data seed script or update GLISK_DEFAULT_AUTHOR_WALLET in .env"
    )
```

---

## Configuration Contract

**Module**: `backend/src/glisk/core/config.py`

**Purpose**: Centralized configuration management. Extended with recovery-specific settings.

### New Configuration

```python
class Settings(BaseSettings):
    # ... existing config ...

    # Recovery settings
    GLISK_DEFAULT_AUTHOR_WALLET: str = "0x0000000000000000000000000000000000000001"
    RECOVERY_BATCH_SIZE: int = 1000  # Max tokens to recover in single operation

    @field_validator("GLISK_DEFAULT_AUTHOR_WALLET")
    @classmethod
    def validate_default_author_wallet(cls, v: str) -> str:
        """Validate default author wallet is valid Ethereum address."""
        if not v.startswith("0x") or len(v) != 42:
            raise ValueError("GLISK_DEFAULT_AUTHOR_WALLET must be valid Ethereum address")
        return v.lower()  # Normalize to lowercase for DB comparison
```

**Behavior Contracts**:
- **`GLISK_DEFAULT_AUTHOR_WALLET`**: Must be valid Ethereum address format. Used for all recovered tokens. Should match an author in the database (verified at runtime by recovery service).
- **`RECOVERY_BATCH_SIZE`**: Caps number of tokens recovered in single operation. Prevents memory exhaustion for large gaps. Default 1000 balances performance vs memory.

---

## Exception Hierarchy

**Module**: `backend/src/glisk/services/exceptions.py` (extended)

```python
class RecoveryError(Exception):
    """Base exception for recovery operations."""
    pass

class BlockchainConnectionError(RecoveryError):
    """Failed to connect to blockchain RPC after retries."""
    pass

class ContractNotFoundError(RecoveryError):
    """Contract not found at specified address."""
    pass

class DefaultAuthorNotFoundError(RecoveryError):
    """Default author wallet not found in database."""
    pass
```

**Usage**:
- CLI catches `RecoveryError` base class and exits with code 1
- Specific exceptions provide actionable error messages to user
- Non-recovery errors (IntegrityError for duplicates) are not subclasses of RecoveryError

---

## Logging Contract

**Module**: All recovery modules use `structlog` for structured logging

**Required Log Events**:

```python
# Recovery start
logger.info(
    "recovery.started",
    max_token_id=next_token_id,
    limit=limit,
    dry_run=dry_run,
)

# Missing tokens identified
logger.info(
    "recovery.gaps_detected",
    missing_count=len(missing_ids),
    first_missing=missing_ids[0] if missing_ids else None,
    last_missing=missing_ids[-1] if missing_ids else None,
)

# Token created
logger.info(
    "recovery.token_created",
    token_id=token_id,
    author_id=str(author_id),
)

# Duplicate detected (webhook won race)
logger.info(
    "recovery.duplicate_skipped",
    token_id=token_id,
    reason="webhook_concurrent_creation",
)

# Recovery complete
logger.info(
    "recovery.completed",
    total_on_chain=result.total_on_chain,
    total_in_db=result.total_in_db,
    recovered_count=result.recovered_count,
    skipped_duplicate_count=result.skipped_duplicate_count,
    duration_seconds=duration,
)

# Error during recovery
logger.error(
    "recovery.failed",
    error=str(e),
    error_type=type(e).__name__,
)
```

**Log Level Guidelines**:
- INFO: Normal operations (start, gaps detected, tokens created, complete)
- WARNING: Non-fatal issues (duplicate token skipped - expected in race condition)
- ERROR: Fatal issues that abort recovery (network error, DB connection lost)

---

## Transaction Boundaries

**Pattern**: Unit of Work (UoW) pattern for transaction management

```python
async with get_uow() as uow:
    try:
        result = await recovery_service.recover_missing_tokens(
            uow=uow,
            limit=args.limit,
            dry_run=args.dry_run,
        )
        # UoW commits automatically on context exit if no exception
    except RecoveryError as e:
        # UoW rolls back automatically on exception
        logger.error("recovery.failed", error=str(e))
        raise
```

**Guarantees**:
- Single transaction for entire recovery operation
- All-or-nothing: Either all tokens created, or none (rollback on error)
- Duplicate handling: IntegrityError caught inside transaction, logged, transaction continues
- Dry run: Transaction always rolled back at end if dry_run=True

---

## Performance Contracts

**Latency Requirements** (from spec SC-003, SC-004):
- `get_next_token_id()`: <1 second for RPC call
- `get_missing_token_ids()`: <1 second for queries up to 100k token range
- `recover_missing_tokens()`: <5 seconds for 100 missing tokens (includes DB inserts)

**Scalability**:
- Batch size (RECOVERY_BATCH_SIZE): 1000 tokens per operation to prevent memory exhaustion
- For >1000 missing tokens, CLI should call recovery service in batches

**Resource Limits**:
- Memory: O(n) where n = number of missing tokens (list in memory)
- Database connections: Single connection via UoW (no connection pool exhaustion)
- RPC calls: Single call to nextTokenId() per recovery operation

---

## Summary

These internal contracts define the behavior and interfaces for recovery services. Key principles:
1. **Idempotency**: Safe to run recovery multiple times (database UNIQUE constraint prevents duplicates)
2. **Atomicity**: Single transaction, all-or-nothing
3. **Error Handling**: Distinguish fatal errors (abort) vs non-fatal (log and continue)
4. **Performance**: Meet latency requirements via efficient queries and batching
5. **Observability**: Structured logging for auditability and debugging
