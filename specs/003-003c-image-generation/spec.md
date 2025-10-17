# Feature Specification: Image Generation Worker

**Feature Branch**: `003-003c-image-generation`
**Created**: 2025-10-17
**Status**: Draft
**Input**: User description: "003-003c-image-generation - Directory: specs/003-003c-image-generation/ - Branch: 003-003c-image-generation @.prompts/003c-image-generation.xml"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automatic Image Generation for New Mints (Priority: P1)

When a new NFT mint is detected by the system, the platform automatically generates an AI image based on the creator's text prompt. The generated image becomes available for subsequent processing (upload to IPFS and linking to the token).

**Why this priority**: This is the core value delivery of the feature. Without automatic image generation, the entire NFT creation pipeline is blocked. This represents the minimum viable functionality needed to demonstrate value.

**Independent Test**: Can be fully tested by inserting a token record with status='detected' into the database, verifying the system polls for it, calls an image generation service with the prompt text, and updates the token status to 'uploading' with the generated image URL stored.

**Acceptance Scenarios**:

1. **Given** a token exists with status='detected' and a valid text prompt, **When** the worker polls for work, **Then** the system generates an image, stores the image URL, and updates the token status to 'uploading'
2. **Given** multiple tokens exist with status='detected', **When** the worker polls for work, **Then** the system processes up to the batch size limit (default 10) of tokens concurrently
3. **Given** a token with status='detected' has been processed successfully, **When** querying the token record, **Then** the image_url field contains a valid URL pointing to the generated image

---

### User Story 2 - Resilient Image Generation with Automatic Retries (Priority: P2)

When image generation encounters temporary issues (network timeouts, rate limits, service unavailability), the system automatically retries the operation without manual intervention. This ensures that transient failures don't result in permanently failed NFTs.

**Why this priority**: Reliability is crucial for production use, but the basic generation flow must work first. This adds robustness to the P1 functionality without changing the core user value.

**Independent Test**: Can be tested by simulating network failures during image generation and verifying that the system retries up to the maximum attempts, then either succeeds (status='uploading') or marks the token as permanently failed (status='failed') with error details stored.

**Acceptance Scenarios**:

1. **Given** image generation fails due to a network timeout, **When** the worker retries the operation, **Then** the system resets the token status to 'detected', increments the attempt counter, and retries with exponential backoff
2. **Given** a token has failed 3 times due to transient errors, **When** the fourth attempt occurs, **Then** the system marks the token as permanently failed (status='failed') and stores the error message
3. **Given** a token fails due to an invalid prompt error, **When** the worker processes the error, **Then** the system immediately marks it as failed without retrying (non-retryable error)

---

### User Story 3 - Graceful Failure Handling and Error Visibility (Priority: P3)

When image generation fails permanently (invalid prompts, authentication issues, or exceeding retry limits), the system records detailed error information for debugging and monitoring. Users or administrators can identify which tokens failed and why.

**Why this priority**: Error visibility is important for operations and debugging, but the system can function without it initially. This adds observability without changing the core generation or retry logic.

**Independent Test**: Can be tested by triggering various failure scenarios (invalid API credentials, malformed prompts, rate limit exhaustion) and verifying that the token record contains the error message in the generation_error field and the attempt count in generation_attempts.

**Acceptance Scenarios**:

1. **Given** image generation fails with an invalid API token error, **When** the worker handles the failure, **Then** the token status is set to 'failed', generation_error contains "Invalid API token", and generation_attempts reflects the number of tries
2. **Given** a token has status='failed', **When** querying the database, **Then** the generation_error field contains a human-readable description of why generation failed
3. **Given** multiple tokens have failed for different reasons, **When** reviewing the error logs, **Then** each token's failure reason is clearly distinguishable and actionable

---

### Edge Cases

- **Empty/invalid image URL returned**: System validates the response and treats empty or malformed URLs as generation failures, triggering retry logic
- **Worker crash with tokens in 'generating' status**: On startup, worker automatically recovers tokens where generation_attempts < max_retries by resetting status to 'detected'. Tokens at max attempts remain 'failed' and require manual operator intervention
- **Concurrent worker race conditions**: Database-level locking (FOR UPDATE SKIP LOCKED) prevents duplicate processing. If a token is locked by another worker, it's skipped and picked up in the next polling cycle
- **Oversized prompts exceeding service limits**: Prompts are validated to be ≤1000 characters. Oversized prompts are marked as 'failed' immediately (non-retryable error)
- **Idle polling with no work**: Worker continues polling at configured interval (1 second default) with minimal CPU overhead (<1%)
- **Service rate limits on concurrent requests**: Rate limit errors are treated as transient failures, triggering exponential backoff retry logic. No special circuit breaker—standard retry mechanism handles this
- **Content policy violations**: When the image service rejects content, the system uses a fallback prompt instead of marking the token as failed, ensuring the NFT pipeline continues

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST poll for tokens with status='detected' at a configurable interval (default 1 second)
- **FR-002**: System MUST lock tokens during processing to prevent duplicate processing by concurrent workers
- **FR-003**: System MUST generate images by sending the author's prompt text to Replicate API using the official Python SDK
- **FR-004**: System MUST store the generated image URL in the token record upon successful generation
- **FR-005**: System MUST update token status from 'detected' to 'generating' when starting image generation
- **FR-006**: System MUST update token status from 'generating' to 'uploading' after successful image generation
- **FR-007**: System MUST process up to a configurable batch size (default 10) of tokens concurrently per polling cycle
- **FR-008**: System MUST retry failed image generation requests up to 3 times for transient errors (network failures, timeouts, rate limits)
- **FR-009**: System MUST use exponential backoff between retry attempts (increasing delay: 1s, 2s, 4s)
- **FR-010**: System MUST distinguish between retryable errors (network issues, timeouts, rate limits) and non-retryable errors (invalid prompts, authentication failures)
- **FR-011**: System MUST reset token status to 'detected' and increment the attempt counter for transient failures
- **FR-012**: System MUST mark token status as 'failed' and store error details for permanent failures or after exceeding retry limit
- **FR-013**: System MUST track the number of generation attempts per token in a dedicated counter field
- **FR-014**: System MUST store error messages in a dedicated error field when generation fails permanently
- **FR-015**: System MUST start and stop the worker process via application lifecycle events
- **FR-016**: System MUST support configuring the polling interval, batch size, and image generation model via environment variables
- **FR-017**: System MUST log all image generation attempts, successes, failures, and retries with structured logging
- **FR-018**: System MUST validate prompt text for existence, non-empty content, and length ≤1000 characters before attempting generation
- **FR-019**: System MUST automatically recover tokens stuck in 'generating' status on worker startup by resetting status to 'detected' if generation_attempts < max_retries (3)
- **FR-020**: System MUST use a configurable fallback prompt when the image service rejects content due to content policy violations, allowing the token to proceed through the pipeline
- **FR-021**: System MUST log content policy violations as censorship events with the original prompt for audit purposes
- **FR-022**: System MUST distinguish between three error categories: (1) content policy violations → retry with fallback prompt, (2) network/timeout errors → retry with original prompt, (3) authentication/validation errors → mark failed immediately
- **FR-023**: System MUST support manual token recovery by allowing operators to reset failed tokens via database UPDATE operations (admin API deferred to future spec)
- **FR-024**: System MUST track standard operational metrics including generation counters (success/failed), queue depth (tokens in 'detected' status), and generation duration histograms
- **FR-025**: System MUST mark oversized prompts (>1000 characters) as non-retryable failures immediately without consuming API quota

### Key Entities

- **Token**: Represents an NFT mint event that requires image generation. Tracks the current processing status ('detected', 'generating', 'uploading', 'failed'), the number of generation attempts, error messages from failed attempts, and the URL of the successfully generated image.

- **Author**: The creator of the NFT who provided the original text prompt. The prompt text is used as input for image generation.

### Technical Dependencies

- **Replicate Python SDK**: Official `replicate` package for API integration
- **External Service**: Replicate API (https://replicate.com) for image generation
- **Authentication**: Requires `REPLICATE_API_TOKEN` environment variable
- **Configuration Variables**:
  - `REPLICATE_MODEL_VERSION`: Model identifier (e.g., "black-forest-labs/flux-schnell")
  - `FALLBACK_CENSORED_PROMPT`: Fallback prompt for content policy violations
  - Polling interval, batch size (inherited from worker configuration)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: System successfully generates images for 95% of detected tokens within 60 seconds of detection
- **SC-002**: System processes batches of up to 10 tokens concurrently without blocking or deadlocks
- **SC-003**: Transient failures (network timeouts, rate limits) result in successful retries within 10 seconds for at least 90% of affected tokens
- **SC-004**: Permanent failures (invalid prompts, authentication errors) are identified and marked as failed within 5 seconds without unnecessary retries
- **SC-005**: System maintains zero duplicate image generation requests for the same token (idempotency maintained)
- **SC-006**: All failed tokens have error messages stored that provide actionable debugging information
- **SC-007**: System gracefully starts and stops without orphaning tokens in 'generating' status across application restarts
- **SC-008**: Worker polling overhead (when no tokens are available) consumes less than 1% CPU utilization

## Clarifications

### Session 2025-10-17: Edge Case Decisions

**Design Philosophy**: Focus on monthly-frequency events with 95% automatic handling. Simple solutions over complex logic for rare scenarios. Operators handle extreme edge cases manually.

#### Q1: Worker Crash Recovery - Orphaned Tokens

**Decision**: Auto-recover tokens with status='generating' if generation_attempts < max_retries

- **Answer**: Reset to 'detected' only if generation_attempts < max_retries (Option B)
- **Implementation**: On worker startup, run recovery query: `UPDATE tokens_s0 SET status='detected' WHERE status='generating' AND generation_attempts < 3`
- **Edge case handling**: Tokens at max attempts remain 'failed', requiring manual reset if the crash wasn't their fault
- **Frequency**: Worker crashes/restarts happen weekly to monthly (deployments, OOM). Must handle automatically for 95% of cases.
- **Implication**: Respects retry budget, prevents infinite loops, provides predictable recovery behavior

#### Q2: Prompt Text Validation and Sanitization

**Decision**: Length validation (max 1000 characters) + fallback prompt for censored content

- **Answer**: Option B + Fallback approach
- **Validation rules**:
  - Prompt length ≤ 1000 characters (API service limit)
  - Prompt exists and is non-empty
  - Oversized prompts → immediate failure (non-retryable)
- **Content policy handling**: When image service rejects due to content violations:
  - Use fallback prompt: "Cute kittens and flowers in a peaceful garden, with text overlay saying 'Content moderated by AI service'"
  - Token continues through pipeline (status → 'uploading')
  - Log original prompt as censorship event for audit trail
- **Security rationale**: Smart contract controls who can mint (trust upstream). Length validation prevents API errors.
- **Frequency**: Censored prompts occur monthly or less—worth auto-handling to prevent manual intervention
- **Configuration**: Add `FALLBACK_CENSORED_PROMPT` environment variable

#### Q3: Manual Recovery for Permanently Failed Tokens

**Decision**: Operator can reset failed tokens via SQL UPDATE

- **Answer**: Manual reset allowed (Option B)
- **Recovery procedure**: `UPDATE tokens_s0 SET status='detected', generation_attempts=0, generation_error=NULL WHERE token_id=X`
- **Use case**: API outages that exhaust retries, then service recovers
- **Frequency**: Major outages requiring bulk resets occur monthly or less
- **MVP approach**: Direct SQL access for operators. Defer admin API to spec 003e (operations)
- **Documentation**: Include recovery procedure in quickstart.md

#### Q4: Operational Metrics and Monitoring

**Decision**: Standard worker metrics (counters, queue depth, latency histogram)

- **Answer**: Option B - Standard metrics set
- **Metrics to track**:
  - `image_generation_total` (counter with success/failed labels)
  - `image_generation_queue_depth` (gauge: tokens in 'detected' status)
  - `image_generation_duration_seconds` (histogram: P50, P95, P99)
  - `image_generation_retries_total` (counter with attempt_number label)
- **Format**: Prometheus-compatible format (industry standard)
- **Implementation timing**: Defer metrics endpoint to production deployment. Structured logs sufficient for MVP.
- **Rationale**: Enables SLO tracking and capacity planning without over-instrumentation overhead

#### Q5: Behavior During Extended Service Outage

**Decision**: No circuit breaker logic—rely on monitoring alerts

- **Answer**: Option D - No special handling
- **Rationale**: Major multi-hour outages occur yearly or less (not monthly). Don't build complex circuit breaker for rare events.
- **Operational response**:
  1. Monitoring alerts operator when failure rate > 50% for 5+ minutes
  2. Operator checks external service status page
  3. Operator pauses worker manually if confirmed major outage (docker stop)
  4. After service recovery: operator resets failed tokens if within retry window
- **Behavior**: Keep trying until retry limit (simple, predictable)
- **Future consideration**: Add circuit breaker in later spec if outages become monthly

#### Q6: Image Generation Service Selection

**Decision**: Use Replicate with its Python SDK

- **Q**: Which image generation service should the system integrate with? → **A**: Replicate with its Python SDK
- **Service**: Replicate (https://replicate.com)
- **Integration**: Official `replicate` Python SDK
- **Model flexibility**: Replicate supports multiple models (FLUX, SDXL, etc.) via model version parameters
- **Pricing**: Pay-per-second compute model
- **Image URLs**: Replicate returns temporary hosted URLs (CDN-backed, expire after 10 days)
- **Authentication**: API token via `REPLICATE_API_TOKEN` environment variable
- **Dependencies**: Add `replicate` to Python dependencies (uv add replicate)
- **Implementation note**: Model selection configurable via `REPLICATE_MODEL_VERSION` environment variable (e.g., "black-forest-labs/flux-schnell" for fast generation)

#### Q7: Image URL Persistence Strategy

**Decision**: Store Replicate's temporary URL directly (10-day expiration accepted)

- **Q**: What should the system do with Replicate's temporary image URLs? → **A**: Store temporary URL directly (Option A)
- **URL Expiration**: Replicate-hosted URLs expire after 10 days (not 24h as initially assumed)
- **Storage approach**: Store Replicate's CDN URL directly in `image_url` field without copying to permanent storage
- **Rationale**: 10-day window is sufficient for MVP since spec 003d (IPFS Upload) will migrate images to permanent IPFS storage within hours/days of generation
- **Risk acceptance**: If 003d pipeline fails or is delayed, images may expire before permanent storage—acceptable for MVP
- **Future**: Spec 003d will read `image_url`, download from Replicate, upload to IPFS, and update token with IPFS URI
