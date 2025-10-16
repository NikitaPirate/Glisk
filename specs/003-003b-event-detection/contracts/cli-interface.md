# CLI Interface Contract

**Feature**: 003-003b-event-detection
**Created**: 2025-10-17
**Type**: Command-Line Interface

## Overview

This document defines the command-line interface for the event recovery mechanism that fetches historical mint events from the blockchain.

---

## Command: Recover Events

### Synopsis

```bash
python -m glisk.cli.recover_events [OPTIONS]
```

### Description

Fetches missed NFT mint events from blockchain history using `eth_getLogs` and stores them in the database. Useful for:
- Recovering events missed during server downtime
- Initial blockchain sync when deploying backend
- Backfilling events after contract deployment

### Options

#### `--from-block` (optional)

**Type**: Integer

**Description**: Starting block number for recovery. If not provided, uses `last_processed_block` from `system_state` table.

**Example**:
```bash
python -m glisk.cli.recover_events --from-block 12345000
```

**Behavior**:
- If `--from-block` provided: Start from that block
- If NOT provided: Load `system_state.value WHERE key='last_processed_block'`
- If NOT provided AND no state exists: ERROR (must provide --from-block)

---

#### `--to-block` (optional)

**Type**: Integer or "latest"

**Description**: Ending block number for recovery. Defaults to "latest".

**Example**:
```bash
python -m glisk.cli.recover_events --from-block 12345000 --to-block 12346000
```

**Behavior**:
- If `--to-block` provided: Stop at that block
- If NOT provided: Use "latest" (current blockchain head)

---

#### `--batch-size` (optional)

**Type**: Integer

**Default**: 1000

**Description**: Number of blocks to process per `eth_getLogs` request. Adjust based on event density and RPC limits.

**Example**:
```bash
python -m glisk.cli.recover_events --from-block 12345000 --batch-size 500
```

**Constraints**:
- Minimum: 1
- Maximum: 2000 (Alchemy paid tier limit)
- Free tier: Recommended 100-500 (10-block limit per request)

---

#### `--network` (optional)

**Type**: String

**Default**: Uses `NETWORK` environment variable

**Description**: Override network setting (BASE_SEPOLIA or BASE_MAINNET).

**Example**:
```bash
python -m glisk.cli.recover_events --network BASE_MAINNET --from-block 12345000
```

---

#### `--dry-run` (optional)

**Type**: Boolean flag

**Description**: Fetch events and parse them, but do NOT write to database. Useful for testing.

**Example**:
```bash
python -m glisk.cli.recover_events --from-block 12345000 --dry-run
```

**Output**: Prints events to stdout without database modifications.

---

#### `--verbose` / `-v` (optional)

**Type**: Boolean flag

**Description**: Enable verbose logging (DEBUG level).

**Example**:
```bash
python -m glisk.cli.recover_events --from-block 12345000 -v
```

---

### Exit Codes

- `0` - Success (all events recovered and stored)
- `1` - Error (database connection failed, RPC error, invalid arguments)
- `2` - Partial success (some events recovered, then error occurred)

---

## Usage Examples

### Example 1: First-Time Recovery (Fresh Database)

```bash
# Contract deployed at block 12,345,000
# Want to sync all events from deployment to now
python -m glisk.cli.recover_events --from-block 12345000
```

**Expected Output**:
```
[2025-10-17 00:40:00] INFO: Starting event recovery from block 12345000 to latest
[2025-10-17 00:40:01] INFO: Processing blocks 12345000 - 12346000 (batch 1/50)
[2025-10-17 00:40:03] INFO: Found 12 events in batch, stored successfully
[2025-10-17 00:40:03] INFO: Updated last_processed_block to 12346000
...
[2025-10-17 00:42:15] INFO: Recovery complete! Total: 587 events processed
```

---

### Example 2: Incremental Recovery (Resume from Last Checkpoint)

```bash
# System already processed up to block 12,350,000
# Want to catch up to latest
python -m glisk.cli.recover_events
```

**Expected Output**:
```
[2025-10-17 00:45:00] INFO: Loading last_processed_block from system_state
[2025-10-17 00:45:00] INFO: Starting event recovery from block 12350001 to latest
[2025-10-17 00:45:01] INFO: Processing blocks 12350001 - 12351001 (batch 1/10)
[2025-10-17 00:45:02] INFO: Found 3 events in batch, stored successfully
...
[2025-10-17 00:45:25] INFO: Recovery complete! Total: 15 events processed
```

---

### Example 3: Specific Block Range Recovery

```bash
# Know that events were missed between blocks 12,348,000 and 12,349,000
python -m glisk.cli.recover_events --from-block 12348000 --to-block 12349000
```

**Expected Output**:
```
[2025-10-17 00:50:00] INFO: Starting event recovery from block 12348000 to 12349000
[2025-10-17 00:50:01] INFO: Processing blocks 12348000 - 12349000 (batch 1/1)
[2025-10-17 00:50:02] INFO: Found 8 events in batch, stored successfully
[2025-10-17 00:50:02] INFO: Updated last_processed_block to 12349000
[2025-10-17 00:50:02] INFO: Recovery complete! Total: 8 events processed
```

---

### Example 4: Dry Run (Test Mode)

```bash
# Test recovery without database writes
python -m glisk.cli.recover_events --from-block 12345000 --to-block 12346000 --dry-run
```

**Expected Output**:
```
[2025-10-17 00:55:00] INFO: DRY RUN MODE - No database modifications
[2025-10-17 00:55:00] INFO: Starting event recovery from block 12345000 to 12346000
[2025-10-17 00:55:01] INFO: Processing blocks 12345000 - 12346000 (batch 1/1)
[2025-10-17 00:55:02] INFO: Found 12 events (would be stored):
  - MintEvent: tx=0x1234..., log_index=0, token_id=1
  - MintEvent: tx=0x1234..., log_index=1, token_id=2
  ...
[2025-10-17 00:55:02] INFO: DRY RUN COMPLETE - No changes made
```

---

### Example 5: Verbose Logging

```bash
# Debug RPC issues or event parsing
python -m glisk.cli.recover_events --from-block 12345000 --verbose
```

**Expected Output**:
```
[2025-10-17 01:00:00] DEBUG: Loaded config: network=BASE_SEPOLIA, contract=0x742d...
[2025-10-17 01:00:00] DEBUG: Connecting to Alchemy RPC: https://base-sepolia.g.alchemy.com/v2/...
[2025-10-17 01:00:00] INFO: Starting event recovery from block 12345000 to latest
[2025-10-17 01:00:01] DEBUG: eth_getLogs request: fromBlock=0xbc614e, toBlock=0xbc654e
[2025-10-17 01:00:01] DEBUG: RPC response: 12 logs returned
[2025-10-17 01:00:01] DEBUG: Parsing log 0: topics=[0x..., 0x..., 0x..., 0x...]
[2025-10-17 01:00:01] DEBUG: Decoded event: minter=0xA1b2..., author=0xB2c3..., token_id=1
...
```

---

## Output Format

### Standard Output (INFO level)

**Progress Updates**:
```
[timestamp] INFO: Processing blocks {from_block} - {to_block} (batch {current}/{total})
[timestamp] INFO: Found {count} events in batch, stored successfully
[timestamp] INFO: Updated last_processed_block to {block_number}
```

**Summary**:
```
[timestamp] INFO: Recovery complete! Total: {count} events processed
```

**Errors**:
```
[timestamp] ERROR: {error_message}
[timestamp] ERROR: Recovery failed at block {block_number}
```

### Verbose Output (DEBUG level)

- RPC request/response details
- Event parsing steps
- Database query execution
- Author lookup results

---

## Error Handling

### Missing `--from-block` and No State

**Error**:
```
ERROR: Cannot determine starting block. Provide --from-block or ensure last_processed_block exists in system_state.
```

**Exit Code**: 1

---

### RPC Connection Failure

**Error**:
```
ERROR: Failed to connect to Alchemy RPC: Connection timeout
```

**Exit Code**: 1

**Recommendation**: Check network connectivity, verify `ALCHEMY_API_KEY`.

---

### Rate Limit Exceeded

**Behavior**: Automatic retry with exponential backoff (3 attempts).

**Output**:
```
[timestamp] WARNING: Rate limit exceeded, retrying in 5 seconds (attempt 1/3)
[timestamp] WARNING: Rate limit exceeded, retrying in 10 seconds (attempt 2/3)
```

**Error (after 3 attempts)**:
```
ERROR: Rate limit exceeded after 3 retries. Use smaller --batch-size or wait before retrying.
```

**Exit Code**: 1

---

### Database Connection Failure

**Error**:
```
ERROR: Database connection failed: FATAL: password authentication failed for user "glisk"
```

**Exit Code**: 1

**Recommendation**: Check `DATABASE_URL` environment variable.

---

### Duplicate Events (Expected)

**Behavior**: Skip gracefully (UNIQUE constraint violation).

**Output**:
```
[timestamp] INFO: Skipped 3 duplicate events (already processed)
```

**Exit Code**: 0 (success)

---

### Partial Success (Network Interruption)

**Behavior**: Stop at last successfully processed block.

**Output**:
```
[timestamp] INFO: Processed 500 events successfully
[timestamp] ERROR: Network interruption at block 12,347,500
[timestamp] INFO: Recovery stopped. Run again to resume from block 12,347,001.
```

**Exit Code**: 2 (partial success)

---

## Performance

**Target Throughput**: 1000 events in 2 minutes

**Breakdown**:
- `eth_getLogs` request: ~1-2 seconds per batch (1000 blocks)
- Database INSERT: ~50-100ms per event
- Batch commit: ~200ms per batch

**Rate Limits** (Alchemy Free Tier):
- 500 CUPs (Compute Units Per Second)
- `eth_getLogs` = 75 CU per request
- Max requests/second: ~6.67
- Recommended: 1 request every 2 seconds (3000 blocks/minute with batch-size=1000)

---

## Database Transactions

**Atomicity**: Each batch is a single transaction.

**Behavior**:
1. Fetch logs via `eth_getLogs` (fromBlock to toBlock)
2. Begin database transaction
3. For each log:
   - Lookup author by wallet
   - INSERT mint_event (skip if UNIQUE constraint violated)
   - INSERT token (skip if PK constraint violated)
4. UPDATE system_state.last_processed_block = toBlock
5. Commit transaction

**On Failure**: Entire batch rolls back, retry from same fromBlock.

---

## Configuration

**Environment Variables**:
```bash
ALCHEMY_API_KEY=your_api_key_here
GLISK_NFT_CONTRACT_ADDRESS=0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0
NETWORK=BASE_SEPOLIA
GLISK_DEFAULT_AUTHOR_WALLET=0x0000000000000000000000000000000000000001
DATABASE_URL=postgresql+psycopg://localhost/glisk
```

---

## Future Enhancements (Out of Scope)

- **Parallel batch processing**: Process multiple block ranges concurrently (deferred until throughput issues)
- **Resume after partial failure**: Automatic retry from last checkpoint (deferred)
- **Progress bar**: Visual progress indicator for long recoveries (deferred)
- **Event verification**: Cross-check with Alchemy's indexed data (deferred)
- **Multi-contract support**: Recover events from multiple contracts (deferred)
