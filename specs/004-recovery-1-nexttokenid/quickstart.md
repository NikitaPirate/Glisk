# Quickstart: Simplified Token Recovery via nextTokenId

**Branch**: `004-recovery-1-nexttokenid` | **Date**: 2025-10-18

## Prerequisites

Before implementing this feature, ensure:

- [x] Smart contract is deployed to testnet (will need redeploy after adding nextTokenId getter)
- [x] Backend is running with database migrations up to date
- [x] Default author wallet exists in database (GLISK_DEFAULT_AUTHOR_WALLET)
- [x] All existing tests pass (`cd backend && TZ=America/Los_Angeles uv run pytest tests/ -v`)

## Implementation Phases

This feature will be implemented in 3 user stories (prioritized P1 → P2 → P3):

### Phase 1: Automatic Token Discovery (P1)
**Goal**: Implement core recovery mechanism that discovers missing tokens

**Steps**:
1. Add `nextTokenId()` getter to smart contract
2. Redeploy contract to testnet, update .env with new address
3. Create `TokenRecoveryService` with contract query logic
4. Implement `TokenRepository.get_missing_token_ids()` query
5. Create `recover_tokens` CLI command
6. Write unit tests for gap detection logic
7. Write integration test with testcontainer
8. Manual testnet validation

**Success Criteria**: Run recovery CLI, verify missing tokens created with status='detected'

---

### Phase 2: Remove Unused Metadata Fields (P2)
**Goal**: Clean up database schema by removing fields we can't populate

**Steps**:
1. Update `Token` model: Remove `mint_timestamp` and `minter_address` fields
2. Generate Alembic migration: `uv run alembic revision --autogenerate -m "remove_unused_recovery_fields"`
3. Manually verify migration: Check upgrade() and add proper downgrade()
4. Grep codebase for field references: `rg "mint_timestamp|minter_address"`
5. Update all code references:
   - `repositories/token.py`: Change ORDER BY to use created_at
   - Remove field validations from model
6. Run migration: `uv run alembic upgrade head`
7. Verify all tests pass
8. Verify workers still function correctly

**Success Criteria**: Schema drops fields, all processes work without errors

---

### Phase 3: Deprecate Event-Based Recovery (P3)
**Goal**: Remove old recovery code

**Steps**:
1. Delete `backend/src/glisk/services/blockchain/event_recovery.py`
2. Delete `backend/src/glisk/cli/recover_events.py`
3. Delete tests: `backend/tests/unit/services/blockchain/test_event_recovery.py`
4. Delete tests: `backend/tests/unit/cli/test_recover_events.py`
5. Grep for imports: `rg "event_recovery|recover_events"`
6. Remove any remaining references
7. Run full test suite to verify nothing broke
8. Update CLAUDE.md to remove old recovery documentation

**Success Criteria**: 200+ LOC removed, all tests pass, no dead code references

---

## Step-by-Step Guide

### Step 1: Add nextTokenId Getter to Smart Contract

**File**: `contracts/src/GliskNFT.sol`

**Add after line 200** (after `supportsInterface` function):

```solidity
// ============================================
// TOKEN ID QUERY (Recovery Support)
// ============================================

/**
 * @notice Get the next token ID that will be minted
 * @dev Public getter for _nextTokenId state variable
 * @return The next token ID (starts at 1, increments after each mint)
 */
function nextTokenId() external view returns (uint256) {
    return _nextTokenId;
}
```

**Redeploy Contract**:
```bash
cd contracts
forge build
forge script script/Deploy.s.sol:DeployScript --rpc-url base-sepolia --broadcast
# Update backend/.env with new CONTRACT_ADDRESS
```

---

### Step 2: Create TokenRecoveryService

**File**: `backend/src/glisk/services/blockchain/token_recovery.py` (new file)

```python
"""Token recovery service using nextTokenId counter."""

from dataclasses import dataclass

import structlog
from web3 import Web3
from web3.exceptions import ContractLogicError
from sqlalchemy.exc import IntegrityError

from glisk.uow import UnitOfWork
from glisk.models.token import Token, TokenStatus
from glisk.services.exceptions import (
    BlockchainConnectionError,
    ContractNotFoundError,
    DefaultAuthorNotFoundError,
)

logger = structlog.get_logger(__name__)


@dataclass
class RecoveryResult:
    """Result of recovery operation."""

    total_on_chain: int
    total_in_db: int
    missing_count: int
    recovered_count: int
    skipped_duplicate_count: int
    errors: list[str]


class TokenRecoveryService:
    """Recovers missing tokens by comparing contract state with database."""

    def __init__(
        self,
        web3: Web3,
        contract_address: str,
        contract_abi: list[dict],
    ):
        self.web3 = web3
        self.contract = web3.eth.contract(address=contract_address, abi=contract_abi)

    async def get_next_token_id(self) -> int:
        """Query contract's nextTokenId with retry logic."""
        for attempt in range(3):
            try:
                return self.contract.functions.nextTokenId().call()
            except ContractLogicError:
                raise ContractNotFoundError("Contract not found or nextTokenId() not available")
            except Exception as e:
                if attempt == 2:
                    raise BlockchainConnectionError(f"RPC call failed after 3 attempts: {e}")
                await asyncio.sleep(2**attempt)  # Exponential backoff: 1s, 2s

    async def recover_missing_tokens(
        self,
        uow: UnitOfWork,
        default_author_wallet: str,
        limit: int | None = None,
        dry_run: bool = False,
    ) -> RecoveryResult:
        """Recover missing tokens from blockchain state."""
        logger.info("recovery.started", limit=limit, dry_run=dry_run)

        # Step 1: Query contract
        next_token_id = await self.get_next_token_id()
        logger.info("recovery.contract_queried", next_token_id=next_token_id)

        # Step 2: Find missing IDs
        missing_ids = await uow.tokens.get_missing_token_ids(next_token_id, limit)
        logger.info(
            "recovery.gaps_detected",
            missing_count=len(missing_ids),
            first_missing=missing_ids[0] if missing_ids else None,
            last_missing=missing_ids[-1] if missing_ids else None,
        )

        if not missing_ids:
            logger.info("recovery.no_gaps")
            return RecoveryResult(
                total_on_chain=next_token_id,
                total_in_db=next_token_id,
                missing_count=0,
                recovered_count=0,
                skipped_duplicate_count=0,
                errors=[],
            )

        # Step 3: Query author addresses from contract
        author_cache = {}  # Cache to avoid duplicate DB queries

        # Step 4: Create tokens
        recovered_count = 0
        skipped_duplicate_count = 0
        errors = []

        for token_id in missing_ids:
            try:
                # Query prompt author from contract
                author_wallet = self.contract.functions.tokenPromptAuthor(token_id).call()
                author_wallet_lower = author_wallet.lower()

                # Check cache first
                if author_wallet_lower not in author_cache:
                    # Lookup or create author in database
                    author = await uow.authors.get_by_wallet(author_wallet_lower)
                    if not author:
                        # Create new author if doesn't exist
                        from glisk.models.author import Author
                        author = Author(wallet_address=author_wallet_lower)
                        await uow.authors.add(author)
                        logger.info("recovery.author_created", wallet=author_wallet_lower)
                    author_cache[author_wallet_lower] = author
                else:
                    author = author_cache[author_wallet_lower]

                # Create token with actual author from contract
                token = Token(
                    token_id=token_id,
                    author_id=author.id,
                    status=TokenStatus.DETECTED,
                )
                await uow.tokens.add(token)
                recovered_count += 1
                logger.info("recovery.token_created", token_id=token_id, author=author_wallet_lower)
            except IntegrityError:
                # Webhook created token concurrently - expected race condition
                skipped_duplicate_count += 1
                logger.info("recovery.duplicate_skipped", token_id=token_id)

        # Step 5: Commit or rollback
        if dry_run:
            await uow.rollback()
            logger.info("recovery.dry_run_rollback")
        else:
            await uow.commit()

        logger.info(
            "recovery.completed",
            recovered_count=recovered_count,
            skipped_duplicate_count=skipped_duplicate_count,
        )

        return RecoveryResult(
            total_on_chain=next_token_id,
            total_in_db=next_token_id - len(missing_ids) + skipped_duplicate_count,
            missing_count=len(missing_ids),
            recovered_count=recovered_count,
            skipped_duplicate_count=skipped_duplicate_count,
            errors=errors,
        )
```

---

### Step 3: Add Repository Method

**File**: `backend/src/glisk/repositories/token.py`

**Add method to TokenRepository class**:

```python
async def get_missing_token_ids(
    self,
    max_token_id: int,
    limit: int | None = None,
) -> list[int]:
    """Get token IDs missing from database within on-chain range.

    Args:
        max_token_id: Upper bound from contract.nextTokenId() (exclusive)
        limit: Optional cap on results

    Returns:
        List of missing token IDs in ascending order
    """
    from sqlalchemy import text

    query = text("""
        SELECT series.token_id
        FROM generate_series(1, :max_token_id - 1) AS series(token_id)
        LEFT JOIN tokens_s0 ON series.token_id = tokens_s0.token_id
        WHERE tokens_s0.token_id IS NULL
        ORDER BY series.token_id ASC
        LIMIT :limit
    """)
    # Note: Token IDs start at 1 (not 0) per contract implementation

    result = await self.session.execute(
        query,
        {"max_token_id": max_token_id, "limit": limit or 1000000},
    )
    return [row[0] for row in result.fetchall()]
```

---

### Step 4: Create CLI Command

**File**: `backend/src/glisk/cli/recover_tokens.py` (new file)

```python
"""CLI command for token recovery."""

import asyncio
import sys

import structlog
from web3 import Web3

from glisk.core.config import get_settings
from glisk.core.database import get_uow
from glisk.services.blockchain.token_recovery import TokenRecoveryService
from glisk.services.exceptions import RecoveryError

logger = structlog.get_logger(__name__)


async def main(limit: int | None = None, dry_run: bool = False):
    """Run token recovery from CLI."""
    settings = get_settings()

    # Initialize Web3
    web3 = Web3(Web3.HTTPProvider(settings.ALCHEMY_RPC_URL))

    # Load contract ABI (simplified - add proper ABI loading)
    contract_abi = [
        {
            "inputs": [],
            "name": "nextTokenId",
            "outputs": [{"name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function",
        }
    ]

    recovery_service = TokenRecoveryService(
        web3=web3,
        contract_address=settings.GLISK_NFT_CONTRACT_ADDRESS,
        contract_abi=contract_abi,
    )

    async with get_uow() as uow:
        try:
            result = await recovery_service.recover_missing_tokens(
                uow=uow,
                default_author_wallet=settings.GLISK_DEFAULT_AUTHOR_WALLET,
                limit=limit,
                dry_run=dry_run,
            )

            # Print summary
            print(f"\n{'='*60}")
            print("Token Recovery Complete")
            print(f"{'='*60}")
            print(f"On-chain tokens:      {result.total_on_chain}")
            print(f"Database tokens:      {result.total_in_db}")
            print(f"Missing tokens:       {result.missing_count}")
            print(f"Recovered tokens:     {result.recovered_count}")
            print(f"Skipped duplicates:   {result.skipped_duplicate_count}")
            if dry_run:
                print("\nDRY RUN - No changes persisted")
            print(f"{'='*60}\n")

            return 0

        except RecoveryError as e:
            logger.error("recovery.failed", error=str(e))
            print(f"\nError: {e}", file=sys.stderr)
            return 1


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Recover missing tokens from blockchain")
    parser.add_argument("--limit", type=int, help="Max tokens to recover")
    parser.add_argument("--dry-run", action="store_true", help="Don't persist changes")
    args = parser.parse_args()

    exit_code = asyncio.run(main(limit=args.limit, dry_run=args.dry_run))
    sys.exit(exit_code)
```

**Make executable**:
```bash
cd backend
python -m glisk.cli.recover_tokens --help
```

---

### Step 5: Update Token Model

**File**: `backend/src/glisk/models/token.py`

**Remove lines 38-40** (mint_timestamp and minter_address fields):
```python
# DELETE THESE LINES:
# minter_address: str = Field(max_length=42)
# mint_timestamp: datetime = Field(index=True)
```

**Remove lines 54-64** (minter_address validator):
```python
# DELETE THIS VALIDATOR:
# @field_validator("minter_address")
# @classmethod
# def validate_minter_address(cls, v: str) -> str:
#     ...
```

---

### Step 6: Generate and Apply Migration

```bash
cd backend

# Step 1: Generate migration
uv run alembic revision --autogenerate -m "remove_unused_recovery_fields"

# Step 2: Verify generated migration
# Check alembic/versions/*_remove_unused_recovery_fields.py
# Should contain:
#   op.drop_column('tokens_s0', 'mint_timestamp')
#   op.drop_column('tokens_s0', 'minter_address')

# Step 3: Manually add downgrade()
# Edit migration file, add to downgrade():
#   op.add_column('tokens_s0', sa.Column('mint_timestamp', sa.DateTime(), nullable=True))
#   op.add_column('tokens_s0', sa.Column('minter_address', sa.String(42), nullable=True))

# Step 4: Apply migration
uv run alembic upgrade head

# Step 5: Verify schema
docker exec backend-postgres-1 psql -U glisk -d glisk -c "\d tokens_s0"
# Should NOT show mint_timestamp or minter_address columns
```

---

### Step 7: Update Repository Query

**File**: `backend/src/glisk/repositories/token.py`

**Find `get_pending_for_generation` method** (around line 66):

**Change**:
```python
# OLD:
.order_by(Token.mint_timestamp.asc())

# NEW:
.order_by(Token.created_at.asc())
```

---

### Step 8: Run Tests

```bash
cd backend

# Run all tests
TZ=America/Los_Angeles uv run pytest tests/ -v

# All tests should pass
# If any fail, check for mint_timestamp or minter_address references
```

---

### Step 9: Manual Validation

**Test Recovery on Testnet**:

1. Mint tokens directly on-chain (bypass webhook):
   ```bash
   # Use Etherscan or cast to mint directly to contract
   cast send $CONTRACT_ADDRESS "mint(address,uint256)" $AUTHOR_WALLET 3 \
     --value 0.00015ether --rpc-url base-sepolia --private-key $PRIVATE_KEY
   ```

2. Verify tokens missing from database:
   ```bash
   docker exec backend-postgres-1 psql -U glisk -d glisk \
     -c "SELECT token_id FROM tokens_s0 ORDER BY token_id"
   # Should show gaps
   ```

3. Run recovery (dry run first):
   ```bash
   cd backend
   python -m glisk.cli.recover_tokens --dry-run
   # Verify output shows missing tokens detected
   ```

4. Run recovery (real):
   ```bash
   python -m glisk.cli.recover_tokens
   ```

5. Verify tokens created:
   ```bash
   docker exec backend-postgres-1 psql -U glisk -d glisk \
     -c "SELECT token_id, status FROM tokens_s0 ORDER BY token_id"
   # Should show all tokens with status='detected'
   ```

6. Verify image generation worker picks them up:
   ```bash
   # Check logs for worker processing newly detected tokens
   tail -f backend/logs/glisk.log | grep "worker\."
   ```

---

## Troubleshooting

### Contract not found error
**Symptom**: `ContractNotFoundError: Contract not found or nextTokenId() not available`

**Solution**: Verify contract is redeployed with nextTokenId() function, and .env has correct address

### Default author not found
**Symptom**: `DefaultAuthorNotFoundError: Default author 0x... not found`

**Solution**:
```bash
# Check authors table
docker exec backend-postgres-1 psql -U glisk -d glisk \
  -c "SELECT id, wallet_address FROM authors"

# If missing, insert default author
docker exec backend-postgres-1 psql -U glisk -d glisk \
  -c "INSERT INTO authors (id, wallet_address) VALUES (gen_random_uuid(), '0x0000000000000000000000000000000000000001')"
```

### Migration fails
**Symptom**: Alembic migration fails with "column does not exist"

**Solution**: Check if fields were already removed manually. Run `alembic current` to verify state. If needed, create manual migration or reset alembic history for dev environment.

### Tests fail after migration
**Symptom**: Tests reference mint_timestamp or minter_address

**Solution**:
```bash
# Find all references
rg "mint_timestamp|minter_address" backend/

# Update each file to remove field usage
# For tests, use created_at instead of mint_timestamp
# For minter_address, simply remove if not essential to test
```

---

## Success Criteria Checklist

After completing all phases, verify:

- [ ] Smart contract has public nextTokenId() function
- [ ] Contract redeployed to testnet with new address in .env
- [ ] CLI command `python -m glisk.cli.recover_tokens` runs successfully
- [ ] Recovery detects missing tokens and creates records with status='detected'
- [ ] Database schema no longer has mint_timestamp or minter_address columns
- [ ] All workers function correctly without removed fields
- [ ] Old recovery code (event_recovery.py, recover_events.py) is deleted
- [ ] Old recovery tests are deleted
- [ ] All tests pass: `TZ=America/Los_Angeles uv run pytest tests/ -v`
- [ ] Manual testnet validation: Mint directly, run recovery, verify tokens created
- [ ] Image generation worker processes recovered tokens normally

---

## Integration: Run Recovery on Application Startup

**Recommended Approach**: Run recovery automatically before starting workers to ensure database consistency.

### Implementation

**File**: `backend/src/glisk/app.py`

Add recovery call in startup lifecycle hook:

```python
from glisk.services.blockchain.token_recovery import TokenRecoveryService

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager."""
    logger.info("application.startup")

    # Run recovery before starting workers
    logger.info("recovery.startup_check")
    try:
        settings = get_settings()
        web3 = Web3(Web3.HTTPProvider(settings.ALCHEMY_RPC_URL))
        recovery_service = TokenRecoveryService(
            web3=web3,
            contract_address=settings.GLISK_NFT_CONTRACT_ADDRESS,
            contract_abi=CONTRACT_ABI,  # Load from file
        )

        async with get_uow() as uow:
            result = await recovery_service.recover_missing_tokens(
                uow=uow,
                limit=1000,  # Reasonable batch for startup
                dry_run=False,
            )
            logger.info(
                "recovery.startup_complete",
                recovered=result.recovered_count,
                skipped=result.skipped_duplicate_count,
            )
    except Exception as e:
        logger.error("recovery.startup_failed", error=str(e))
        # Don't fail startup, just log error
        # Workers can still process new tokens from webhooks

    # Start background workers after recovery
    asyncio.create_task(image_generation_worker())
    asyncio.create_task(ipfs_upload_worker())
    asyncio.create_task(reveal_worker())

    yield  # Application runs

    logger.info("application.shutdown")
```

**Benefits**:
- Guarantees database consistency before workers start
- No manual CLI invocation needed
- Fast startup (typically <2s for most cases)
- Graceful degradation (logs error but doesn't block startup)

---

## Next Steps (Post-Implementation)

1. Update CLAUDE.md with new recovery mechanism documentation
2. Integrate recovery into application startup lifecycle (see above)
3. Add monitoring alert if gap count exceeds threshold (indicates webhook issues)
4. Plan for mainnet deployment (contract upgrade via proxy pattern)
