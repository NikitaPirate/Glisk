# Feature Specification: Simplified Token Recovery via nextTokenId

**Feature Branch**: `004-recovery-1-nexttokenid`
**Created**: 2025-10-18
**Status**: Draft
**Input**: User description: "I want to change the recovery mechanism and logic. I've figured out how to make it much simpler, cheaper, and more efficient:
1. Make nextTokenId public in the contract
2. Recovery mechanism on the server:

1. Query nextTokenId
2. Query the database, passing nextTokenId as an argument in case there are many tokens to avoid overloading the transport. The database returns the IDs of tokens that are missing.
3. Run the normal token pipeline

- The existing web3 events recovery logic and its tests are no longer needed.
- The token table has fields that we cannot fill having only the token ID: mint_timestamp and minter_address. I decided that for us now this is not necessary, and I want to remove these fields so as not to complicate recovery for now."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automatic Token Discovery (Priority: P1)

When tokens are minted on-chain but missed by the webhook system (due to downtime, network issues, or webhook failures), the system must automatically discover and recover these missing tokens without requiring manual intervention or parsing complex blockchain event logs.

**Why this priority**: This is the core value proposition of the simplified recovery mechanism. Without this, the system has gaps in token data that break the entire pipeline (image generation, IPFS upload, reveal).

**Independent Test**: Can be fully tested by minting tokens directly on-chain (bypassing webhooks), running the recovery mechanism, and verifying that all missing tokens appear in the database with status 'detected' and enter the normal processing pipeline.

**Acceptance Scenarios**:

1. **Given** 10 tokens exist on-chain (nextTokenId = 11) and only 7 are in the database, **When** recovery runs, **Then** system identifies token IDs 8, 9, 10 as missing and creates database records for them with status 'detected'
2. **Given** database and on-chain state are synchronized (all tokens present), **When** recovery runs, **Then** system identifies no missing tokens and performs no database operations
3. **Given** recovery discovers 100 missing tokens, **When** processing the gap, **Then** system creates records efficiently without overwhelming the database or network transport

---

### User Story 2 - Remove Unused Metadata Fields (Priority: P2)

The system should only store token data that is actually used by the application. Fields that cannot be populated during recovery (mint_timestamp, minter_address) and are not required for current functionality should be removed to simplify the data model and avoid confusion.

**Why this priority**: Simplifies recovery logic and prevents confusion about incomplete/null data. This is a prerequisite for clean recovery implementation but doesn't directly provide user-facing value.

**Independent Test**: Can be tested by verifying storage schema no longer contains timestamp and minter address fields, and that all application processes function correctly without these fields.

**Acceptance Scenarios**:

1. **Given** token storage has timestamp and minter address fields, **When** migration runs, **Then** these fields are removed from storage schema
2. **Given** migration has removed fields, **When** image generation process runs, **Then** process operates normally without referencing removed fields
3. **Given** migration has removed fields, **When** IPFS upload process runs, **Then** process operates normally without referencing removed fields

---

### User Story 3 - Deprecate Event-Based Recovery (Priority: P3)

The existing web3 event-based recovery mechanism (eth_getLogs parsing) and its associated tests should be removed since the simplified nextTokenId-based approach makes it obsolete.

**Why this priority**: Reduces maintenance burden and code complexity, but is less critical than implementing the new mechanism. Can be done after the new system is proven stable.

**Independent Test**: Can be tested by verifying that event-based recovery modules and CLI commands are removed, their tests are deleted, and all remaining tests pass.

**Acceptance Scenarios**:

1. **Given** event-based recovery module exists in codebase, **When** deprecation cleanup runs, **Then** module is deleted and no code references it
2. **Given** event-based recovery CLI command exists, **When** deprecation cleanup runs, **Then** CLI command is removed and attempting to run it results in appropriate error
3. **Given** tests for event recovery exist, **When** deprecation cleanup runs, **Then** these tests are deleted and remaining test suite passes

---

### Edge Cases

- What happens when on-chain nextTokenId decreases (blockchain reorganization/rollback)?
- How does system handle database query failure when checking for missing tokens?
- What happens if nextTokenId query returns invalid data (network error, malformed response)?
- How does system behave if there's a gap of 10,000+ missing tokens?
- What happens when recovery runs concurrently with webhook receiving new mints (race condition on token creation)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Smart contract MUST expose a public nextTokenId value representing the next token ID to be minted
- **FR-002**: System MUST query the smart contract's nextTokenId to determine total tokens minted
- **FR-003**: System MUST query the database to identify which token IDs (from 0 to nextTokenId-1) are missing
- **FR-004**: Database query MUST accept nextTokenId as parameter to optimize query performance for large token counts
- **FR-005**: System MUST create database records for missing tokens with status 'detected' to trigger normal pipeline processing
- **FR-006**: System MUST remove timestamp metadata from token storage (not needed for recovery)
- **FR-007**: System MUST remove minter address metadata from token storage (not needed for recovery)
- **FR-008**: System MUST remove event-based recovery logic from codebase
- **FR-009**: System MUST remove event-based recovery CLI command from codebase
- **FR-010**: System MUST remove tests associated with event-based recovery mechanism
- **FR-011**: Recovery mechanism MUST handle network errors when querying nextTokenId gracefully
- **FR-012**: Recovery mechanism MUST handle database errors when querying or inserting tokens gracefully

### Key Entities

- **Smart Contract State**: Maintains nextTokenId counter (public, read-only from server perspective)
- **Token Record**: Represents a minted NFT with essential fields: unique identifier, processing status, author reference, and user-provided prompt - excludes timestamp and minter address
- **Missing Token Set**: Computed difference between on-chain token range [0, nextTokenId-1] and tokens present in database

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Recovery mechanism identifies all missing tokens (0% false negatives) when on-chain state diverges from database
- **SC-002**: Recovery mechanism produces zero false positives (does not create duplicate tokens)
- **SC-003**: Recovery operation completes in under 5 seconds for gaps of up to 100 tokens
- **SC-004**: Database query for missing tokens scales efficiently (sub-second response) for token counts up to 100,000
- **SC-005**: Code complexity reduction: at least 200 lines of code removed (event-based recovery logic and associated tests)
- **SC-006**: Zero application errors after removing timestamp and minter address fields (all processes and tests pass)

## Assumptions

- **A-001**: Recovery will run automatically on application startup before workers start (ensures database consistency)
- **A-002**: Blockchain reorganizations are rare and can be handled by re-running recovery (no automatic rollback detection required)
- **A-003**: Author attribution for recovered tokens will query `tokenPromptAuthor(tokenId)` from smart contract to get actual author addresses
- **A-004**: If author wallet from contract doesn't exist in database, system will create new author record automatically
- **A-005**: Recovery can run while workers are active (database constraints prevent duplicate token creation)
- **A-006**: Smart contract modification to add public nextTokenId is in scope (requires Solidity changes)
- **A-007**: Token IDs start at 1 (not 0) as per contract implementation

## Dependencies

- **D-001**: Smart contract must be modified to expose public nextTokenId getter (Solidity changes required)
- **D-002**: Smart contract must be redeployed or upgraded to include nextTokenId visibility
- **D-003**: Existing database schema migration framework (Alembic)
- **D-004**: Existing web3 provider configuration for reading contract state

## Out of Scope

- Automatic rollback detection for blockchain reorganizations
- Preserving historical mint_timestamp and minter_address data (explicitly deleted)
- Migration path for existing mint_timestamp/minter_address data (acceptable data loss per user decision)
- Recovery of prompt text from on-chain events (assumes contract stores prompts or uses defaults)
