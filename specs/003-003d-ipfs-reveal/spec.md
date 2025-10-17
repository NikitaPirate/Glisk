# Feature Specification: IPFS Upload and Batch Reveal Mechanism

**Feature Branch**: `003-003d-ipfs-reveal`
**Created**: 2025-10-17
**Status**: Draft
**Input**: User description: "003-003d-ipfs-reveal IPFS Upload and Batch Reveal Mechanism"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automatic IPFS Upload (Priority: P1)

When the system generates an image for a minted NFT, it automatically uploads the image and metadata to IPFS so the content is permanently stored and accessible via decentralized storage.

**Why this priority**: Core functionality required for NFT metadata to be accessible. Without IPFS upload, generated images have no permanent storage and cannot be referenced by token URIs. This is the critical path for making NFTs viewable.

**Independent Test**: Can be fully tested by generating an image for a token, triggering the upload process, and verifying that both image and metadata CIDs are stored in the token record and accessible via IPFS gateway URLs.

**Acceptance Scenarios**:

1. **Given** a token has status='uploading' with a generated image URL, **When** the upload worker processes the token, **Then** the image is uploaded to IPFS and an image CID is returned
2. **Given** an image has been uploaded to IPFS, **When** the worker builds metadata, **Then** a valid ERC721 metadata JSON is created with name, description, image IPFS URI, and attributes
3. **Given** valid metadata JSON has been created, **When** the worker uploads metadata, **Then** metadata is uploaded to IPFS and a metadata CID is returned
4. **Given** both image and metadata CIDs are received, **When** the worker updates the token, **Then** token status changes to 'ready' and both CIDs are stored in the token record
5. **Given** IPFS upload encounters a network timeout, **When** the error is classified, **Then** it is marked as transient and the token is queued for retry with incremented attempt count
6. **Given** IPFS upload encounters authentication failure, **When** the error is classified, **Then** it is marked as permanent and the token status changes to 'failed' with error message recorded

---

### User Story 2 - Automatic Batch Reveal (Priority: P1)

When tokens have been uploaded to IPFS, the system automatically batches them and reveals them on-chain so users can see their NFTs with proper metadata.

**Why this priority**: Final step in the NFT reveal pipeline. Without batch reveal, tokens remain unrevealed on-chain and users cannot view their NFTs. Batching optimizes gas costs compared to individual reveals.

**Independent Test**: Can be fully tested by creating multiple tokens with status='ready' and valid metadata CIDs, triggering the reveal worker, and verifying that a single batch transaction reveals all tokens on-chain with their reveal transaction hash recorded.

**Acceptance Scenarios**:

1. **Given** tokens have status='ready' with metadata CIDs, **When** the reveal worker polls for ready tokens, **Then** tokens are selected and locked for processing using database row-level locking
2. **Given** the reveal worker has selected tokens, **When** batch accumulation begins, **Then** the worker waits for a configured time period (default 5 seconds) to collect more tokens OR until batch reaches maximum size (default 50 tokens)
3. **Given** a batch of tokens is ready for reveal, **When** gas estimation is performed, **Then** the system calculates required gas and applies a safety buffer (default 20%) to prevent transaction failures
4. **Given** gas has been estimated, **When** the batch reveal transaction is submitted, **Then** the transaction is sent to the blockchain using the keeper wallet and a transaction hash is returned
5. **Given** a reveal transaction has been submitted, **When** waiting for confirmation, **Then** the system monitors the transaction status and waits for receipt with timeout protection
6. **Given** a reveal transaction is confirmed, **When** updating token records, **Then** all tokens in the batch have status changed to 'revealed', reveal transaction hash recorded, and transaction details logged
7. **Given** a reveal transaction fails due to gas estimation error, **When** handling the error, **Then** transaction is marked as failed, error is logged, and tokens remain in 'ready' state for retry
8. **Given** a reveal transaction reverts on-chain, **When** handling the revert, **Then** transaction is marked as failed with revert reason, and tokens remain in 'ready' state for investigation

---

### User Story 3 - Resilient Error Handling (Priority: P2)

When external services encounter failures or network issues, the system automatically retries transient failures and clearly marks permanent failures so the pipeline remains operational.

**Why this priority**: Ensures system reliability and reduces manual intervention. External dependencies (IPFS service, blockchain network) will have intermittent issues, so automatic recovery is essential for production operation.

**Independent Test**: Can be fully tested by simulating various error conditions (network timeouts, authentication failures, gas spikes) and verifying that transient errors trigger retries with exponential backoff while permanent errors are marked appropriately without wasting retry attempts.

**Acceptance Scenarios**:

1. **Given** IPFS upload encounters a rate limit error (429), **When** the error is classified, **Then** it is marked as transient and token is queued for retry with exponential backoff delay
2. **Given** a token has failed with transient error, **When** retry is attempted, **Then** the attempt count is incremented and backoff delay is applied before next processing
3. **Given** a token has reached maximum retry attempts (default 3), **When** another failure occurs, **Then** token status changes to 'failed' with final error message recorded
4. **Given** the worker crashes or restarts, **When** startup recovery runs, **Then** any tokens in transient processing states are reset to their previous stable state and requeued for processing
5. **Given** multiple workers are running, **When** polling for tokens to process, **Then** database row-level locking prevents multiple workers from processing the same token simultaneously

---

### Edge Cases

- What happens when IPFS service is down for extended period? (Tokens remain in 'uploading' state with retry attempts, process resumes when service recovers)
- What happens when keeper wallet runs out of gas funds? (Transaction submission fails with clear error logged, manual intervention required to fund wallet)
- What happens when gas prices spike suddenly? (Gas buffer provides safety margin, if insufficient transaction may fail and retry on next iteration with updated gas price)
- What happens when batch reveal transaction is stuck pending for long time? (Timeout protection prevents indefinite waiting, transaction may confirm later and be handled on next poll)
- What happens when generated image URL is no longer accessible? (Upload fails with permanent error, token marked as failed for investigation)
- What happens when metadata CID format changes in future IPFS versions? (CID stored as flexible string field supports both current and future formats)
- What happens when blockchain network is congested? (Transaction waits in mempool, timeout allows retry with higher gas price if needed)
- What happens when token IDs in batch are invalid? (Gas estimation or transaction execution fails, batch marked failed, tokens remain in 'ready' for investigation)

## Requirements *(mandatory)*

### Functional Requirements

**IPFS Upload Requirements**:

- **FR-001**: System MUST poll tokens with status='uploading' at regular intervals and select them for processing using database row-level locking
- **FR-002**: System MUST upload generated images to IPFS storage service and receive content identifier (CID) as proof of storage
- **FR-003**: System MUST build ERC721-compliant metadata JSON containing token name, description, IPFS image URI, and attributes
- **FR-004**: System MUST upload metadata JSON to IPFS storage service and receive metadata CID
- **FR-005**: System MUST store both image CID and metadata CID in token record upon successful upload
- **FR-006**: System MUST update token status from 'uploading' to 'ready' after both uploads complete successfully
- **FR-007**: System MUST classify IPFS errors as transient (network timeouts, rate limits, service unavailable) or permanent (authentication failures, invalid content)
- **FR-008**: System MUST retry transient IPFS failures with exponential backoff up to maximum retry attempts
- **FR-009**: System MUST mark tokens as 'failed' with error messages when permanent errors occur or retry limit exceeded
- **FR-010**: System MUST create audit records for each IPFS upload operation tracking upload type, CID, status, and attempt count

**Batch Reveal Requirements**:

- **FR-011**: System MUST poll tokens with status='ready' at regular intervals and select them for batch processing using database row-level locking
- **FR-012**: System MUST accumulate tokens into batches using either time trigger (wait period expires) or size trigger (maximum batch size reached)
- **FR-013**: System MUST estimate gas required for batch reveal transaction and apply configurable safety buffer percentage
- **FR-014**: System MUST submit batch reveal transaction to blockchain network using authenticated keeper wallet with estimated gas parameters
- **FR-015**: System MUST track batch reveal transactions in audit table with transaction hash, token IDs array, metadata URIs array, and status
- **FR-016**: System MUST monitor submitted transactions for confirmation and wait for transaction receipt with timeout protection
- **FR-017**: System MUST update all tokens in confirmed batch to status='revealed' with reveal transaction hash recorded
- **FR-018**: System MUST handle transaction failures (gas estimation errors, reverts, nonce conflicts) by logging errors and keeping tokens in 'ready' state
- **FR-019**: System MUST recover from worker crashes by resetting orphaned tokens and checking pending transaction statuses on startup

**Worker Management Requirements**:

- **FR-020**: System MUST run IPFS upload worker and reveal worker as separate background processes with independent polling loops
- **FR-021**: System MUST process tokens using session-per-token isolation to prevent failure cascade across batch
- **FR-022**: System MUST implement graceful shutdown handling for worker processes to complete in-flight operations
- **FR-023**: System MUST emit structured log events for all operations including worker lifecycle, token processing, uploads, reveals, and errors

### Key Entities

- **Token**: Represents an NFT with lifecycle tracking through states (detected → generating → uploading → ready → revealed or failed). Key attributes include token ID, status, image URL, image CID, metadata CID, reveal transaction hash, generation attempts, and error messages.

- **IPFS Upload Record**: Audit trail for IPFS operations. Key attributes include token ID reference, upload type (image or metadata), IPFS CID, status, attempt number, error message, and timestamp. Used for debugging and compliance tracking.

- **Reveal Transaction**: Batch reveal operation tracking. Key attributes include transaction hash, array of token IDs, array of metadata URIs, status (pending/confirmed/failed), gas price, block number, error message, and timestamps. Used for monitoring batch efficiency and troubleshooting blockchain interactions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Tokens with generated images are automatically uploaded to IPFS storage within 30 seconds of generation completion under normal service conditions
- **SC-002**: Tokens with completed IPFS uploads are automatically revealed on-chain within 10 seconds of batch trigger conditions being met (time or size limit)
- **SC-003**: System maintains minimum 95% success rate for IPFS uploads excluding service outages
- **SC-004**: System maintains minimum 95% success rate for batch reveal transactions excluding network congestion
- **SC-005**: Batch reveal transactions reduce gas costs by minimum 60% compared to individual token reveals for batches of 10 or more tokens
- **SC-006**: System automatically recovers from transient failures with zero manual intervention required for 90% of retry scenarios
- **SC-007**: System processes minimum 1000 tokens per hour through complete pipeline (upload and reveal) under normal load conditions
- **SC-008**: Worker startup recovery completes within 60 seconds and correctly resets all orphaned tokens to processable states
- **SC-009**: Failed tokens provide actionable error messages sufficient for operators to identify root cause without code inspection
- **SC-010**: System handles concurrent processing by multiple workers without token duplication or lock contention errors

## Assumptions

1. **External Service Dependencies**: IPFS storage service (Pinata) provides API with authentication via API key and secret, returns CIDs in response, and has documented error codes for classification.

2. **Blockchain Integration**: Smart contract provides `revealBatch(uint256[] tokenIds, string[] metadataURIs)` function, blockchain library supports gas estimation and transaction monitoring, keeper wallet is pre-funded with sufficient gas for operations.

3. **Worker Infrastructure**: Application framework supports background task lifecycle management, database supports row-level locking with SKIP LOCKED semantics, workers can be scaled horizontally if needed.

4. **Error Recovery**: Transient failures resolve within minutes to hours (service recovers, network stabilizes), permanent failures require operator intervention (fix configuration, investigate data issues), retry limits prevent infinite loops.

5. **Performance Characteristics**: IPFS uploads complete in 1-5 seconds per operation, blockchain transaction confirmation takes 10-60 seconds depending on network, database queries for token selection complete in under 100ms.

6. **Metadata Standard**: ERC721 metadata follows OpenSea standard with name, description, image URI, and attributes array, IPFS URIs use `ipfs://` scheme, CID format is flexible string supporting current and future versions.

7. **Configuration Defaults**: Batch wait time defaults to 5 seconds for responsive UX, batch size limit defaults to 50 tokens balancing gas efficiency and transaction success rate, gas buffer defaults to 20% safety margin, retry limit defaults to 3 attempts.

8. **Operational Context**: System operates in MVP phase prioritizing working end-to-end pipeline over advanced features, manual admin tools for edge case handling are acceptable initial approach, structured logging provides sufficient observability for debugging.
