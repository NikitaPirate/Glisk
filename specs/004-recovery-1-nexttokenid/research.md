# Research: Simplified Token Recovery via nextTokenId

**Branch**: `004-recovery-1-nexttokenid` | **Date**: 2025-10-18
**Purpose**: Resolve technical unknowns and document design decisions

## Research Questions

### Q1: How to expose nextTokenId from Solidity contract?

**Decision**: Add public getter function `nextTokenId()` that returns the private `_nextTokenId` state variable.

**Rationale**:
- Solidity automatically generates getters for public state variables
- However, `_nextTokenId` is currently private (line 124 in GliskNFT.sol)
- Adding a public getter function is the simplest approach without changing storage layout
- Does not introduce security risks (read-only operation, no access control needed)

**Implementation**:
```solidity
/**
 * @notice Get the next token ID that will be minted
 * @return The next token ID (starts at 1, increments after each mint)
 */
function nextTokenId() external view returns (uint256) {
    return _nextTokenId;
}
```

**Alternatives Considered**:
- Making `_nextTokenId` public: Rejected because underscore prefix convention indicates private variable, would be breaking convention
- Using totalSupply(): Rejected because it doesn't exist in current implementation and would require tracking total minted separately

---

### Q2: How to efficiently query missing token IDs from PostgreSQL?

**Decision**: Use `generate_series()` to create expected range, LEFT JOIN to find gaps, WHERE clause to filter missing IDs.

**Important**: Token IDs start at 1 (not 0) per contract implementation (line 177 in GliskNFT.sol: `_nextTokenId = 1`). Query must use `generate_series(1, :max_token_id - 1)`.

**Rationale**:
- PostgreSQL's `generate_series(start, end)` creates a set of integers representing all expected token IDs
- LEFT JOIN against tokens_s0 table identifies which IDs exist
- WHERE tokens_s0.token_id IS NULL filters to only missing IDs
- Single query execution (no N+1 problem)
- Scales well up to 100k tokens (sub-second performance)

**SQL Pattern**:
```sql
SELECT series.token_id
FROM generate_series(1, :max_token_id - 1) AS series(token_id)
LEFT JOIN tokens_s0 ON series.token_id = tokens_s0.token_id
WHERE tokens_s0.token_id IS NULL
ORDER BY series.token_id ASC;
```

**Alternatives Considered**:
- Python set difference (fetch all IDs, compare in memory): Rejected due to transport overhead for large token counts
- Window functions with LAG: Rejected as more complex and less performant for gap detection
- Recursive CTE: Rejected as overkill for simple range comparison

---

### Q3: How to populate author_id for recovered tokens?

**Decision**: Query `tokenPromptAuthor(tokenId)` from smart contract for each missing token to get the actual prompt author address, then lookup corresponding author in database.

**Rationale**:
- Prompt author addresses are stored on-chain in `tokenPromptAuthor` mapping (line 146 in GliskNFT.sol)
- Contract exposes public getter: `tokenPromptAuthor(uint256) returns (address)`
- Recovery by token_id is now cheap since we only recover missing tokens (not re-processing all)
- Provides accurate author attribution (not default fallback)
- Batch queries can be done via multicall for efficiency if needed

**Implementation**:
1. For each missing token_id, query `contract.functions.tokenPromptAuthor(token_id).call()`
2. Lookup author by wallet address in authors table
3. If author not found in DB, create new author record with that wallet address
4. Use author.id for recovered token

**Optimization for Large Gaps**:
- For >100 missing tokens, use multicall contract to batch RPC calls
- Single RPC call can query 100+ tokenPromptAuthor mappings
- Reduces network latency from O(n) calls to O(n/100) calls

**Alternatives Considered**:
- Use GLISK_DEFAULT_AUTHOR_WALLET for all recovered tokens: Rejected as loses author attribution accuracy
- Store prompt_author on Token model: Rejected as out of scope (would require additional schema changes)

---

### Q4: How to handle race conditions between recovery and webhook?

**Decision**: Rely on database UNIQUE constraint on token_id column to prevent duplicates. Handle IntegrityError gracefully.

**Rationale**:
- tokens_s0.token_id has UNIQUE constraint (line 36 in models/token.py)
- If webhook creates token while recovery is running, database will raise IntegrityError on duplicate
- Existing pattern: UoW (Unit of Work) pattern already handles transaction rollback
- No application-level locking needed (database enforces consistency)

**Implementation**:
```python
try:
    await uow.commit()  # Attempt to insert tokens
except IntegrityError:
    # Token already exists (webhook beat us to it)
    # Log info and continue - this is expected and safe
    logger.info("token_already_exists", token_id=token_id)
```

**Alternatives Considered**:
- Application-level distributed lock (Redis): Rejected as overkill for seasonal MVP
- SELECT FOR UPDATE before INSERT: Rejected as doesn't prevent race (time gap between SELECT and INSERT)
- Disable webhooks during recovery: Rejected as would miss real-time mints

---

### Q5: How to remove mint_timestamp and minter_address fields safely?

**Decision**: Generate Alembic migration with `--autogenerate`, manually verify column drops, test rollback.

**Rationale**:
- Constitution v1.1.0 mandates Alembic autogenerate workflow (lines 177-182 in constitution.md)
- Alembic will detect removed fields from Token model and generate DROP COLUMN statements
- Must manually verify migration doesn't break existing queries or worker logic
- Test migration idempotency: `downgrade -1 && upgrade head` must succeed

**Migration Steps**:
1. Update Token model: Remove `mint_timestamp` and `minter_address` field definitions
2. Run `alembic revision --autogenerate -m "remove_unused_recovery_fields"`
3. Manually review generated migration:
   - Verify `op.drop_column('tokens_s0', 'mint_timestamp')`
   - Verify `op.drop_column('tokens_s0', 'minter_address')`
   - Add `downgrade()` to recreate columns (for rollback safety)
4. Grep codebase for field references: `rg "mint_timestamp|minter_address"`
5. Update all references found (repositories, workers, tests)
6. Run tests to verify no breakage

**Code References to Update** (from grep analysis):
- `backend/src/glisk/repositories/token.py`: Remove mint_timestamp from ORDER BY clause in `get_pending_for_generation()`
- `backend/src/glisk/models/token.py`: Field definitions and validator (lines 38-40, 54-64)
- Any tests that reference these fields

**Alternatives Considered**:
- Manual migration writing: Rejected per constitution (must use autogenerate)
- Soft delete (keep columns, mark as deprecated): Rejected as adds complexity without benefit

---

## Best Practices Applied

### Web3.py Contract Interaction
- Use `contract.functions.nextTokenId().call()` for read-only operations
- No transaction signing needed (view function)
- Handle RPC errors with exponential backoff retry (network transient failures)

### PostgreSQL Query Optimization
- Use `EXPLAIN ANALYZE` to verify query plan uses index on token_id
- Limit result set if gap is large (batch processing for 10k+ missing tokens)
- Connection pooling via psycopg3 (already configured)

### Alembic Migration Safety
- Always add downgrade() implementation for rollback capability
- Test migration on dev database before applying to production
- Use `alembic current` to verify migration state before changes
- Document migration dependencies (e.g., "must run after X migration")

### CLI Command Design
- Use `python -m glisk.cli.recover_tokens` invocation pattern (consistent with existing CLIs)
- Accept `--dry-run` flag for safe testing
- Accept `--limit` flag to cap number of tokens recovered (prevent accidental mass operations)
- Verbose logging with structlog for auditability
- Exit codes: 0 = success, 1 = error, 2 = partial success (some tokens failed)

---

## Implementation Notes

### Smart Contract Deployment
- After adding `nextTokenId()` getter, contract must be redeployed to testnet
- Update GLISK_NFT_CONTRACT_ADDRESS in backend .env file
- Existing contract state (minted tokens) will be lost - acceptable for testnet iteration
- For mainnet (future), would use proxy upgrade pattern - not in scope for Season 0

### Testing Strategy
- Unit tests: Mock web3 responses, test gap detection logic
- Integration tests: Use testcontainers PostgreSQL, seed with known gaps, verify recovery
- Manual testnet testing: Mint tokens directly via Etherscan, run recovery, verify DB state

### Performance Considerations
- For 100k+ token gaps, batch recovery in chunks of 1000 tokens
- Use asyncio.gather() to parallelize author lookups if needed (future optimization)
- Monitor Alchemy RPC rate limits (300 req/s on free tier)

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Recovery runs during webhook downtime, creates duplicates | Low | Medium | Database UNIQUE constraint prevents duplicates, IntegrityError handling logs and continues |
| Large gaps (10k+ tokens) cause timeout | Medium | Low | Add --limit flag, batch processing, timeout handling in CLI |
| Removed fields break existing code | Low | High | Grep codebase before migration, comprehensive test suite, staged rollout |
| nextTokenId() not available on old contract | Medium (testnet) | Medium | Document contract redeploy requirement, update deployment docs |

---

## Open Questions (None Remaining)

All technical unknowns have been resolved. Ready to proceed to Phase 1 (Design & Contracts).
