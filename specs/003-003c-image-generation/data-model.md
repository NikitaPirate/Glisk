# Data Model: Image Generation Worker

**Feature**: 003-003c-image-generation
**Date**: 2025-10-17
**Phase**: 1 - Design & Contracts

## Overview

This document defines the data entities, field specifications, relationships, and state transitions for the image generation worker feature. The feature extends the existing `tokens_s0` table with three new fields to support image generation workflow.

## Entities

### Token (Extended)

**Table**: `tokens_s0` (existing table from 003a, extended in this feature)

**Description**: Represents a minted NFT token that requires image generation. Tracks the token's lifecycle from detection through image generation to upload readiness.

**New Fields** (added by this feature):

| Field | Type | Nullable | Default | Constraints | Description |
|-------|------|----------|---------|-------------|-------------|
| `image_url` | `TEXT` | Yes | `NULL` | None | URL of the generated image (Replicate CDN link, expires after 10 days) |
| `generation_attempts` | `INTEGER` | No | `0` | `>= 0` | Number of image generation attempts for this token (max 3) |
| `generation_error` | `TEXT` | Yes | `NULL` | None | Error message from last failed generation attempt (for debugging) |

**Existing Fields** (from 003a/003b, relevant to this feature):

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `token_id` | `INTEGER` | No | Primary key, unique token identifier |
| `contract_address` | `TEXT` | No | NFT contract address (indexed) |
| `status` | `TEXT` | No | Token lifecycle status (enum: 'detected', 'generating', 'uploading', 'failed') |
| `detected_at` | `TIMESTAMP` | No | UTC timestamp when mint event was detected (used for FIFO ordering) |
| `author_id` | `INTEGER` | No | Foreign key to `authors` table |

**Indexes** (existing from 003a):
- Primary key on `token_id`
- Index on `contract_address` (for contract-specific queries)
- Index on `status` (used by worker's `WHERE status = 'detected'` query)

**No new indexes needed**: Worker query filters on `status` (already indexed) and orders by `detected_at` (no range queries, so index not required).

---

### Author (No Changes)

**Table**: `authors` (existing table from 003a, no changes)

**Description**: Represents the creator who provided the text prompt. Referenced by tokens for prompt text retrieval.

**Relevant Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `author_id` | `INTEGER` | Primary key |
| `wallet_address` | `TEXT` | Ethereum wallet address (unique) |
| `prompt_text` | `TEXT` | Creator's text prompt (input for image generation) |

**Relationship**: `Token.author_id` → `Author.author_id` (many-to-one)

---

## State Transitions

### Token Status Lifecycle (Image Generation Phase)

**State Machine**:

```
┌──────────┐
│ detected │ ← Initial state (from 003b event detection)
└────┬─────┘
     │ Worker polls and locks token
     │ Status: detected → generating
     ▼
┌────────────┐
│ generating │
└────┬───┬───┘
     │   │
     │   │ ┌─────────────────────────────────────┐
     │   │ │ On generation failure:              │
     │   │ │ - Transient error (network/rate     │
     │   └─┤   limit): Status → detected,        │
     │     │   generation_attempts += 1          │
     │     │ - Content policy violation:         │
     │     │   Retry with fallback prompt        │
     │     │ - Permanent error (auth/validation):│
     │     │   Status → failed, store error      │
     │     └─────────────────────────────────────┘
     │
     │ On generation success
     │ Status: generating → uploading
     ▼
┌───────────┐
│ uploading │ ← Success state (ready for 003d IPFS upload)
└───────────┘

┌────────┐
│ failed │ ← Terminal state (permanent failure or retry exhausted)
└────────┘
```

**Transition Rules**:

| From State | To State | Trigger | Field Updates |
|------------|----------|---------|---------------|
| `detected` | `generating` | Worker starts generation | None |
| `generating` | `uploading` | Generation succeeds | `image_url` = Replicate URL |
| `generating` | `detected` | Transient error (retry) | `generation_attempts` += 1 |
| `generating` | `detected` | Content policy violation | Use fallback prompt, `generation_attempts` += 1 |
| `generating` | `failed` | Permanent error | `generation_error` = error message |
| `generating` | `failed` | Retry exhausted (attempts >= 3) | `generation_error` = "Max retries exceeded" |

**Startup Recovery** (orphaned tokens):

| From State | To State | Trigger | Condition |
|------------|----------|---------|-----------|
| `generating` | `detected` | Worker startup | `generation_attempts < 3` |
| `generating` | `failed` | Worker startup | `generation_attempts >= 3` (no change, leave as-is) |

---

## Validation Rules

### Field-Level Validation

**Prompt Text** (from `Author.prompt_text`):
- Must be non-empty and non-null
- Maximum length: 1000 characters
- No sanitization (trust upstream smart contract access control)
- Validation enforced before calling Replicate API

**Generation Attempts**:
- Must be `>= 0`
- Maximum value: 3 (retry exhausted)
- Incremented atomically during retry transitions

**Image URL**:
- Must be valid HTTP/HTTPS URL format (if present)
- No validation on URL reachability (trust Replicate CDN)
- Null until generation succeeds

**Generation Error**:
- Maximum length: 1000 characters (truncate if necessary)
- Stores last error message only (no history)
- Cleared on successful retry

---

## Invariants

**Business Logic Invariants**:

1. **Retry Budget**: A token MUST NOT exceed 3 generation attempts (`generation_attempts <= 3`)
2. **Status Consistency**: A token with status='uploading' MUST have non-null `image_url`
3. **Error Presence**: A token with status='failed' MUST have non-null `generation_error`
4. **Attempt Correlation**: A token with `generation_attempts > 0` MUST have status in {'detected', 'generating', 'failed'} (not 'uploading')
5. **Idempotency**: A token MUST NOT be processed by multiple workers simultaneously (enforced via `FOR UPDATE SKIP LOCKED`)

**Database-Level Invariants**:

1. **Foreign Key**: `Token.author_id` MUST reference valid `Author.author_id`
2. **Non-Negative Attempts**: `generation_attempts >= 0` (CHECK constraint)
3. **Status Enum**: `status` MUST be one of {'detected', 'generating', 'uploading', 'failed'} (enforced at application level)

---

## Example Data Flow

### Successful Generation (First Attempt)

```
Initial State:
  token_id: 123
  status: 'detected'
  author_id: 42 (prompt_text: "A sunset over mountains")
  image_url: NULL
  generation_attempts: 0
  generation_error: NULL

Worker Processing:
  1. Lock token (FOR UPDATE SKIP LOCKED)
  2. Update status: 'detected' → 'generating'
  3. Call Replicate API with prompt "A sunset over mountains"
  4. Receive image URL: "https://replicate.delivery/pbxt/abc123/output.png"
  5. Update token:
     - status: 'generating' → 'uploading'
     - image_url: "https://replicate.delivery/pbxt/abc123/output.png"
  6. Commit transaction

Final State:
  token_id: 123
  status: 'uploading'
  image_url: "https://replicate.delivery/pbxt/abc123/output.png"
  generation_attempts: 0
  generation_error: NULL
```

---

### Transient Failure with Retry

```
Initial State:
  token_id: 456
  status: 'detected'
  generation_attempts: 1 (previous attempt failed)
  generation_error: "Network timeout" (from previous attempt)

Worker Processing:
  1. Lock token
  2. Update status: 'detected' → 'generating'
  3. Call Replicate API
  4. Network timeout exception (transient error)
  5. Update token:
     - status: 'generating' → 'detected'
     - generation_attempts: 1 → 2
     - generation_error: "Network timeout"
  6. Commit transaction

Final State:
  token_id: 456
  status: 'detected' (ready for retry)
  generation_attempts: 2
  generation_error: "Network timeout"
```

---

### Content Policy Violation with Fallback

```
Initial State:
  token_id: 789
  status: 'detected'
  author_id: 99 (prompt_text: "Violent battle scene")
  generation_attempts: 0

Worker Processing:
  1. Lock token
  2. Update status: 'detected' → 'generating'
  3. Call Replicate API with prompt "Violent battle scene"
  4. Receive ContentPolicyError
  5. Log censorship event: token_id=789, original_prompt="Violent battle scene"
  6. Retry with fallback prompt: "Cute kittens and flowers..."
  7. Receive image URL: "https://replicate.delivery/pbxt/xyz789/output.png"
  8. Update token:
     - status: 'generating' → 'uploading'
     - image_url: "https://replicate.delivery/pbxt/xyz789/output.png"
     - generation_attempts: 0 → 1 (counts as one attempt)
  9. Commit transaction

Final State:
  token_id: 789
  status: 'uploading'
  image_url: "https://replicate.delivery/pbxt/xyz789/output.png" (fallback image)
  generation_attempts: 1
  generation_error: NULL (success on fallback)
```

---

### Permanent Failure (Retry Exhausted)

```
Initial State:
  token_id: 321
  status: 'detected'
  generation_attempts: 2 (two previous failures)

Worker Processing:
  1. Lock token
  2. Update status: 'detected' → 'generating'
  3. Call Replicate API
  4. Rate limit error (transient)
  5. Increment attempts: 2 → 3 (max retries reached)
  6. Update token:
     - status: 'generating' → 'failed'
     - generation_attempts: 2 → 3
     - generation_error: "Max retries exceeded after rate limit errors"
  7. Commit transaction

Final State:
  token_id: 321
  status: 'failed' (terminal state)
  generation_attempts: 3
  generation_error: "Max retries exceeded after rate limit errors"
```

---

## Migration Script (Alembic)

**File**: `backend/alembic/versions/XXXX_add_image_generation_fields.py`

```python
"""add_image_generation_fields

Revision ID: XXXX
Revises: YYYY (previous migration)
Create Date: 2025-10-17

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'XXXX'
down_revision = 'YYYY'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add three new columns to tokens_s0 table
    op.add_column('tokens_s0', sa.Column('image_url', sa.Text(), nullable=True))
    op.add_column('tokens_s0', sa.Column('generation_attempts', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('tokens_s0', sa.Column('generation_error', sa.Text(), nullable=True))

def downgrade() -> None:
    # Remove columns in reverse order
    op.drop_column('tokens_s0', 'generation_error')
    op.drop_column('tokens_s0', 'generation_attempts')
    op.drop_column('tokens_s0', 'image_url')
```

**Testing Idempotency**:
```bash
cd backend
alembic upgrade head       # Apply migration
alembic downgrade -1       # Rollback migration
alembic upgrade head       # Reapply migration (should succeed)
```

---

## SQLModel Definition

**File**: `backend/src/glisk/db/models.py` (updated)

```python
from sqlmodel import Field, SQLModel
from datetime import datetime
from typing import Optional

class Token(SQLModel, table=True):
    __tablename__ = "tokens_s0"

    token_id: int = Field(primary_key=True)
    contract_address: str = Field(index=True)
    status: str = Field(index=True)  # 'detected', 'generating', 'uploading', 'failed'
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    author_id: int = Field(foreign_key="authors.author_id")

    # New fields for image generation (003c)
    image_url: Optional[str] = Field(default=None, sa_column_kwargs={"nullable": True})
    generation_attempts: int = Field(default=0, ge=0)  # >= 0 constraint
    generation_error: Optional[str] = Field(default=None, sa_column_kwargs={"nullable": True})
```

---

## Repository Methods

**File**: `backend/src/glisk/repositories/token_repository.py` (extended)

```python
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from glisk.db.models import Token
from typing import List

class TokenRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_for_generation(self, limit: int = 10) -> List[Token]:
        """
        Find tokens ready for image generation with row-level locking.

        Uses FOR UPDATE SKIP LOCKED to prevent duplicate processing.
        """
        stmt = (
            select(Token)
            .where(Token.status == "detected")
            .where(Token.generation_attempts < 3)
            .order_by(Token.detected_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def update_image_url(self, token: Token, image_url: str) -> None:
        """Update token with generated image URL and mark as ready for upload."""
        token.image_url = image_url
        token.status = "uploading"
        self.session.add(token)
        await self.session.commit()
        await self.session.refresh(token)

    async def mark_failed(self, token: Token, error_message: str) -> None:
        """Mark token as permanently failed with error message."""
        token.status = "failed"
        token.generation_error = error_message[:1000]  # Truncate to 1000 chars
        self.session.add(token)
        await self.session.commit()
        await self.session.refresh(token)

    async def increment_attempts(self, token: Token, error_message: str) -> None:
        """Increment retry counter and reset status for transient failure."""
        token.generation_attempts += 1
        token.status = "detected"
        token.generation_error = error_message[:1000]
        self.session.add(token)
        await self.session.commit()
        await self.session.refresh(token)
```

---

## Summary

**Schema Changes**:
- Add 3 columns to `tokens_s0`: `image_url`, `generation_attempts`, `generation_error`
- No new tables, no new indexes
- Migration file: `XXXX_add_image_generation_fields.py`

**State Machine**:
- 4 states: `detected` → `generating` → `uploading` | `failed`
- Retry transitions: `generating` → `detected` (increment attempts)
- Terminal states: `uploading` (success), `failed` (permanent)

**Validation**:
- Prompt: non-empty, ≤1000 characters
- Attempts: 0-3 range, non-negative constraint
- Image URL: valid URL format (if present)

**Relationships**:
- `Token` → `Author` (many-to-one, foreign key)
- No new tables or relationships added
