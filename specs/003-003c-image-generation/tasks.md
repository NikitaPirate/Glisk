# Tasks: Image Generation Worker

**Input**: Design documents from `/specs/003-003c-image-generation/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/internal-service-contracts.md, research.md, quickstart.md

**Tests**: No explicit test tasks included per spec - focus on implementation with ad-hoc testing per quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions
- **Backend**: `backend/src/glisk/`, `backend/tests/`
- Monorepo structure from 003a/003b foundation

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure for image generation worker

- [X] T001 Add Replicate Python SDK dependency: `cd backend && uv add replicate`
- [X] T002 [P] Update environment configuration in `backend/src/glisk/core/config.py` with Replicate settings: `REPLICATE_API_TOKEN`, `REPLICATE_MODEL_VERSION`, `FALLBACK_CENSORED_PROMPT`, `POLL_INTERVAL_SECONDS`, `WORKER_BATCH_SIZE`
- [X] T003 [P] Create worker package directory structure: `backend/src/glisk/workers/__init__.py`
- [X] T004 [P] Create image generation service package: `backend/src/glisk/services/image_generation/__init__.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T005 Update SQLModel entity in `backend/src/glisk/db/models.py`: Add three new fields to `Token` model: `image_url: Optional[str]`, `generation_attempts: int = 0`, `generation_error: Optional[str]`
- [X] T006 Generate Alembic migration: `cd backend && uv run alembic revision --autogenerate -m "add_image_generation_fields"` for three new columns in `tokens_s0` table
- [X] T007 Verify and test migration idempotency: Apply migration, rollback, reapply per quickstart.md
- [X] T008 Apply database migration: `cd backend && uv run alembic upgrade head`
- [X] T009 [P] Create error classification hierarchy in `backend/src/glisk/services/image_generation/replicate_client.py`: Define `ReplicateError`, `TransientError`, `ContentPolicyError`, `PermanentError` exception classes

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Automatic Image Generation for New Mints (Priority: P1) 🎯 MVP

**Goal**: Automatically generate AI images for detected NFT mints using Replicate API, updating token status from 'detected' to 'uploading' with image URL stored.

**Independent Test**: Insert token with status='detected' into database, verify worker polls for it, calls Replicate API with prompt text, and updates token status to 'uploading' with image_url populated. Use manual testing per quickstart.md Test 1.

### Implementation for User Story 1

- [X] T010 [P] [US1] Create `PromptValidator` module in `backend/src/glisk/services/image_generation/prompt_validator.py`: Implement `validate_prompt(prompt: str)` function with length ≤1000 chars and non-empty validation
- [X] T011 [P] [US1] Create `ReplicateClient` service in `backend/src/glisk/services/image_generation/replicate_client.py`: Implement `generate_image(prompt: str, model_version: str | None = None) -> str` using official Replicate Python SDK (sync wrapped in asyncio via `to_thread`)
- [X] T012 [US1] Extend `TokenRepository` in `backend/src/glisk/repositories/token.py`: Add `find_for_generation(limit: int = 10) -> List[Token]` method with PostgreSQL `FOR UPDATE SKIP LOCKED` query filtering `status='detected' AND generation_attempts < 3`, ordered by `mint_timestamp ASC`
- [X] T013 [US1] Add repository method `update_image_url(token: Token, image_url: str)` in `backend/src/glisk/repositories/token.py`: Update token with image URL and set status to 'uploading', commit transaction
- [X] T014 [US1] Create worker module `backend/src/glisk/workers/image_generation_worker.py`: Implement `process_single_token(token: Token)` function to handle single token generation workflow (validate prompt → call Replicate → update status 'detected' → 'generating' → 'uploading')
- [X] T015 [US1] Implement `process_batch()` function in `backend/src/glisk/workers/image_generation_worker.py`: Lock tokens via `get_pending_for_generation()`, process concurrently with `asyncio.gather()` and `return_exceptions=True`
- [X] T016 [US1] Implement main worker loop `run_image_generation_worker()` in `backend/src/glisk/workers/image_generation_worker.py`: Poll at `POLL_INTERVAL_SECONDS`, call `process_batch()`, handle `CancelledError` for graceful shutdown
- [X] T017 [US1] Integrate worker with FastAPI lifecycle in `backend/src/glisk/app.py`: Create `@asynccontextmanager` lifespan function to start worker as background task on startup and cancel on shutdown
- [X] T018 [US1] Add structured logging to worker in `backend/src/glisk/workers/image_generation_worker.py`: Log events `worker.started`, `worker.stopped`, `token.generation.started`, `token.generation.succeeded` with structured fields (token_id, duration, image_url)

**Checkpoint**: At this point, User Story 1 should be fully functional - tokens with status='detected' automatically get images generated and progress to 'uploading' status. Validate with manual test from quickstart.md.

---

## Phase 4: User Story 2 - Resilient Image Generation with Automatic Retries (Priority: P2)

**Goal**: Automatically retry image generation on transient failures (network timeouts, rate limits, service unavailability) without manual intervention. Use exponential backoff and respect max retry limit (3 attempts).

**Independent Test**: Simulate network failures by temporarily setting invalid `REPLICATE_API_TOKEN` or breaking connectivity, verify system retries up to 3 times with exponential backoff, then either succeeds (status='uploading') or marks as permanently failed (status='failed'). Use manual testing per quickstart.md Test 2.

### Implementation for User Story 2

- [X] T019 [US2] Implement error classification function `classify_error(exception: Exception) -> ReplicateError` in `backend/src/glisk/services/image_generation/replicate_client.py`: Map Python exceptions to error categories (timeout → TransientError, 429/503 → TransientError, 401 → PermanentError, content policy → ContentPolicyError)
- [X] T020 [US2] Add retry logic to `process_single_token()` in `backend/src/glisk/workers/image_generation_worker.py`: Wrap Replicate API call in try-except, classify errors, handle `TransientError` by calling `increment_attempts()` and resetting status to 'detected'
- [X] T021 [US2] Add repository method `increment_attempts(token: Token, error_message: str)` in `backend/src/glisk/repositories/token.py`: Increment `generation_attempts`, set status='detected', store error message, commit transaction
- [X] T022 [US2] Implement exponential backoff in `process_single_token()` in `backend/src/glisk/workers/image_generation_worker.py`: Add `await asyncio.sleep(2 ** token.generation_attempts)` before retrying (1s, 2s, 4s delays)
- [X] T023 [US2] Add max retry check to `process_single_token()` in `backend/src/glisk/workers/image_generation_worker.py`: If `token.generation_attempts >= 3` after error, call `mark_failed()` instead of `increment_attempts()`
- [X] T024 [US2] Add repository method `mark_failed(token: Token, error_message: str)` in `backend/src/glisk/repositories/token.py`: Set status='failed', store error message (truncated to 1000 chars), commit transaction
- [X] T025 [US2] Implement startup recovery function `recover_orphaned_tokens(session: AsyncSession)` in `backend/src/glisk/workers/image_generation_worker.py`: Run SQL `UPDATE tokens_s0 SET status='detected' WHERE status='generating' AND generation_attempts < 3` on worker startup
- [X] T026 [US2] Call `recover_orphaned_tokens()` in worker startup in `backend/src/glisk/workers/image_generation_worker.py`: Execute before starting worker background task
- [X] T027 [US2] Add retry logging to `process_single_token()` in `backend/src/glisk/workers/image_generation_worker.py`: Log `token.generation.retry` events with error type, attempt number, and max attempts; log `token.generation.exhausted` when retry limit reached

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently - transient failures trigger automatic retries with exponential backoff, permanent failures and retry exhaustion mark tokens as failed.

---

## Phase 5: User Story 3 - Graceful Failure Handling and Error Visibility (Priority: P3)

**Goal**: Record detailed error information for permanently failed tokens (invalid prompts, authentication issues, retry exhaustion) to enable debugging and monitoring. Operators can identify which tokens failed and why via database queries.

**Independent Test**: Trigger various failure scenarios (invalid API credentials, malformed prompts, rate limit exhaustion, content policy violations), verify token records contain error messages in `generation_error` field and attempt counts in `generation_attempts`. Use manual testing per quickstart.md Tests 2 & 3.

### Implementation for User Story 3

- [X] T028 [US3] Add content policy violation handling to `process_single_token()` in `backend/src/glisk/workers/image_generation_worker.py`: Catch `ContentPolicyError`, log censorship event with original prompt, retry generation with `FALLBACK_CENSORED_PROMPT` value from config
- [X] T029 [US3] Add censorship logging to `process_single_token()` in `backend/src/glisk/workers/image_generation_worker.py`: Log `token.censored` event with token_id, original_prompt (redacted), fallback_prompt, reason='content_policy_violation'
- [X] T030 [US3] Add permanent error handling to `process_single_token()` in `backend/src/glisk/workers/image_generation_worker.py`: Catch `PermanentError`, immediately call `mark_failed()` without retry (no increment), log `token.generation.failed` with error details
- [X] T031 [US3] Add prompt validation error handling to `process_single_token()` in `backend/src/glisk/workers/image_generation_worker.py`: Catch `ValueError` from `validate_prompt()`, treat as non-retryable, mark failed immediately with error "Prompt validation failed: {message}"
- [X] T032 [US3] Add worker error handling to `run_image_generation_worker()` in `backend/src/glisk/workers/image_generation_worker.py`: Wrap polling loop in try-except, log `worker.error` events with exc_info, backoff 5 seconds on unexpected exceptions, continue loop
- [X] T033 [US3] Add error message truncation to `mark_failed()` and `increment_attempts()` in `backend/src/glisk/repositories/token.py`: Ensure error messages are truncated to 1000 characters before database write
- [X] T034 [US3] Update logging throughout worker in `backend/src/glisk/workers/image_generation_worker.py`: Add comprehensive logging for all error paths - permanent failures, validation failures, retry exhaustion, content policy violations with actionable error details

**Checkpoint**: All user stories should now be independently functional - error visibility is complete, operators can query failed tokens and understand failure reasons.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories, documentation, and validation

- [ ] T035 [P] Add quickstart validation: Manually execute all tests from `specs/003-003c-image-generation/quickstart.md` (Test 1: single token generation, Test 2: transient failure, Test 3: content policy violation)
- [X] T036 [P] Update project documentation in `CLAUDE.md`: Add Image Generation Worker section documenting worker usage, configuration, monitoring, and manual recovery procedures per quickstart.md
- [X] T037 [P] Code cleanup: Review all worker and service code for clarity, remove debug statements, ensure consistent error handling patterns across all three user stories
- [X] T038 [P] Configuration validation: Add startup checks in `backend/src/glisk/core/config.py` to validate required environment variables (`REPLICATE_API_TOKEN`, `FALLBACK_CENSORED_PROMPT`) are set, fail fast with clear error messages if missing
- [X] T039 Verify database schema: Query `tokens_s0` table to confirm all three new columns exist (`image_url`, `generation_attempts`, `generation_error`) with correct types and defaults
- [ ] T040 End-to-end validation: Insert test token with status='detected', verify complete workflow from detection → generation → uploading status with valid image URL, check logs for all expected events

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories - Basic generation workflow
- **User Story 2 (P2)**: Depends on User Story 1 completion - Adds retry logic to existing generation workflow
- **User Story 3 (P3)**: Depends on User Story 2 completion - Adds error visibility to existing retry logic

### Within Each User Story

- Models/schema changes before services
- Services before worker logic
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- **Phase 1**: All Setup tasks marked [P] can run in parallel (T002, T003, T004)
- **Phase 3**: Within US1, tasks T010 and T011 can run in parallel (different service modules)
- **Phase 6**: All Polish tasks marked [P] can run in parallel (T035, T036, T037, T038)
- **Note**: User Stories 2 and 3 have sequential dependencies on previous stories due to extending the same workflow

---

## Parallel Example: User Story 1 Core Services

```bash
# Launch core services together (different files, no dependencies):
Task T010: "Create PromptValidator module in backend/src/glisk/services/image_generation/prompt_validator.py"
Task T011: "Create ReplicateClient service in backend/src/glisk/services/image_generation/replicate_client.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T004)
2. Complete Phase 2: Foundational (T005-T009) - CRITICAL, blocks all stories
3. Complete Phase 3: User Story 1 (T010-T018)
4. **STOP and VALIDATE**: Test User Story 1 with quickstart.md Test 1
5. Deploy/demo if ready - basic image generation working

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready (database schema, dependencies)
2. Add User Story 1 → Test independently → Deploy/Demo (MVP! - basic generation works)
3. Add User Story 2 → Test independently → Deploy/Demo (reliability added - retries work)
4. Add User Story 3 → Test independently → Deploy/Demo (observability added - error visibility)
5. Complete Polish → Production ready

### Sequential Story Strategy (Recommended)

Due to story dependencies:

1. Complete Setup + Foundational together (T001-T009)
2. Complete User Story 1 → Validate with quickstart.md Test 1 (T010-T018)
3. Complete User Story 2 → Validate with quickstart.md Test 2 (T019-T027)
4. Complete User Story 3 → Validate with quickstart.md Test 3 (T028-T034)
5. Complete Polish → Full validation (T035-T040)

**Rationale**: US2 extends US1 workflow, US3 extends US2 workflow - sequential implementation is most efficient.

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- User Stories 2 and 3 extend User Story 1's workflow - sequential implementation recommended
- Manual testing per quickstart.md replaces automated test suite for MVP
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, breaking existing 003a/003b functionality
