# Data Model: X (Twitter) Account Linking

**Feature**: 007-link-x-twitter
**Date**: 2025-10-21

## Overview

This document describes the data model for X (Twitter) account linking. The key principle: **no new database tables needed** - we use existing Author model's `twitter_handle` field and in-memory state for temporary OAuth data.

## Database Schema

### Existing Tables (No Changes)

#### `authors` Table

**Status**: ✅ **No changes required** - `twitter_handle` field already exists

```sql
CREATE TABLE authors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    wallet_address VARCHAR(42) NOT NULL UNIQUE,
    twitter_handle VARCHAR(255) DEFAULT NULL,  -- ✅ Already exists
    farcaster_handle VARCHAR(255) DEFAULT NULL,
    prompt_text TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC'),
    CONSTRAINT authors_wallet_address_unique UNIQUE (wallet_address),
    CONSTRAINT authors_wallet_address_format CHECK (wallet_address ~ '^0x[a-fA-F0-9]{40}$')
);

CREATE INDEX idx_authors_wallet_address ON authors(wallet_address);
```

**Field Details**:
- `twitter_handle`: Optional[str], max_length=255
  - Stores X username (e.g., "gliskartist" without @ symbol)
  - NULL when author hasn't linked X account
  - No uniqueness constraint (multiple authors can link same X account per MVP decision)
  - Permanent once set (no unlink/re-link in MVP)

**SQLModel Definition** (already exists in `/backend/src/glisk/models/author.py`):
```python
class Author(SQLModel, table=True):
    """Author represents an NFT creator with wallet address and AI prompt."""

    __tablename__ = "authors"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    wallet_address: str = Field(max_length=42, unique=True, index=True)
    twitter_handle: Optional[str] = Field(default=None, max_length=255)  # ✅ Used for X linking
    farcaster_handle: Optional[str] = Field(default=None, max_length=255)
    prompt_text: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Validation methods omitted for brevity
```

### In-Memory State (Temporary, No Database)

**OAuth State Storage**:
- **Purpose**: Store PKCE code_verifier and wallet_address during OAuth flow (30s - 5 min)
- **Implementation**: Python `dict` in application memory (no Redis, no database)
- **Lifetime**: 5-minute TTL, auto-cleanup on access or manual periodic cleanup
- **Structure**:

```python
# In-memory dictionary (module-level or service instance)
oauth_state_storage: dict[str, OAuthState] = {}

class OAuthState:
    """Temporary OAuth state for PKCE flow."""

    state: str              # Random CSRF token (serves as dict key)
    code_verifier: str      # PKCE code verifier (43-128 chars)
    wallet_address: str     # Author's wallet (for updating after OAuth)
    created_at: float       # Unix timestamp (for TTL checks)
    expires_at: float       # created_at + 300 seconds (5 min TTL)

# Usage:
# 1. On /auth/start: oauth_state_storage[state] = OAuthState(...)
# 2. On /callback: retrieve by state, validate TTL, delete after use
# 3. Cleanup: Delete entries where current_time > expires_at
```

**Why In-Memory**:
1. **Simplest for MVP** (no Redis setup, no database table, no additional dependencies)
2. **Short-lived data** (5-minute max lifetime, single-use)
3. **Stateless after OAuth completes** (no session persistence requirement)
4. **Small scale** (few concurrent OAuth flows, minimal memory footprint)

**Limitations**:
- Lost on app restart (acceptable - users just retry OAuth)
- Not shared across multiple backend instances (acceptable for MVP single instance)
- Manual TTL management (acceptable for MVP - cleanup on access)

**Cleanup Strategy**:
```python
def cleanup_expired_oauth_states():
    """Remove expired OAuth state entries from in-memory storage."""
    now = time.time()
    expired_keys = [
        state for state, data in oauth_state_storage.items()
        if now > data.expires_at
    ]
    for key in expired_keys:
        del oauth_state_storage[key]
```

## Entity Relationships

```
┌─────────────────────┐
│      Author         │
│─────────────────────│
│ id (PK)            │
│ wallet_address (UQ)│
│ twitter_handle     │──── Optional X username (null until linked)
│ prompt_text        │
│ created_at         │
└─────────────────────┘
        │
        │ 1:N (one author, many tokens)
        ▼
┌─────────────────────┐
│      Token          │
│─────────────────────│
│ token_id (PK)      │
│ author_wallet      │──── Foreign key (many tokens to one author)
│ prompt_text        │
│ image_url          │
│ metadata_cid       │──── IPFS metadata includes author.twitter_handle if exists
│ status             │
└─────────────────────┘
```

**Key Point**: When IPFS metadata is generated, the `twitter_handle` from Author is conditionally included:

```json
// NFT Metadata (IPFS)
{
  "name": "GLISK S0 #123",
  "description": "GLISK Season 0. https://x.com/getglisk",
  "image": "ipfs://bafkreixxx...",
  "attributes": [],
  "creator": {
    "twitter": "gliskartist"  // ✅ Only if author.twitter_handle is not null
  }
}
```

## State Transitions

### Author Twitter Handle

```
NULL (no X account linked)
  │
  ├──[User clicks "Link X Account"]
  │  └──[OAuth flow initiated]
  │     │
  │     ├──[User approves on X]
  │     │  └──[Callback receives username]
  │     │     └──[Update: twitter_handle = "username"]──► "username" (linked)
  │     │
  │     └──[User denies / OAuth error]
  │        └──[No update]──► NULL (remains unlinked)
  │
  └──[No change] (MVP: no unlink functionality)
```

**Permanent State**: Once `twitter_handle` is set, it **cannot be changed** or unlinked in MVP (per spec requirement).

### OAuth Flow State

```
[User clicks button]
  │
  └──► POST /api/authors/x/auth/start
         │
         └──► Create OAuthState in-memory
                │  {state, code_verifier, wallet_address}
                │  TTL: 5 minutes
                │
                ├──► Return authorization_url to frontend
                │      │
                │      └──► User redirects to X
                │            │
                │            ├──► User approves
                │            │      │
                │            │      └──► X redirects to /callback?code=xxx&state=yyy
                │            │            │
                │            │            └──► Retrieve OAuthState by state
                │            │                  │
                │            │                  ├──► Validate TTL
                │            │                  ├──► Exchange code for token
                │            │                  ├──► Fetch username from /users/me
                │            │                  ├──► Update author.twitter_handle
                │            │                  └──► Delete OAuthState ✅ (cleanup)
                │            │
                │            └──► User denies
                │                   └──► X redirects to /callback?error=access_denied
                │                         └──► Delete OAuthState (cleanup)
                │
                └──► [5 minutes pass]
                       └──► TTL expires
                              └──► Delete OAuthState (cleanup)
```

## Validation Rules

### Author.twitter_handle

- **Type**: Optional[str]
- **Max Length**: 255 characters
- **Format**: X username without @ symbol (e.g., "gliskartist" not "@gliskartist")
- **Uniqueness**: None (multiple authors can link same X account)
- **Allowed Characters**: Alphanumeric, underscores (X username rules)
- **Validation**:
  ```python
  @field_validator("twitter_handle")
  @classmethod
  def validate_twitter_handle(cls, v: Optional[str]) -> Optional[str]:
      """Validate X username format (alphanumeric + underscores only)."""
      if v is None:
          return v
      if len(v) < 1 or len(v) > 15:  # X username length limits
          raise ValueError("X username must be 1-15 characters")
      if not re.match(r'^[A-Za-z0-9_]+$', v):
          raise ValueError("X username can only contain letters, numbers, and underscores")
      return v
  ```

### OAuth State

- **state**: 32+ character random string (base64url-encoded)
- **code_verifier**: 43-128 character random string (PKCE RFC 7636)
- **wallet_address**: Valid Ethereum address (0x + 40 hex chars)
- **TTL**: 300 seconds (5 minutes) from creation

## Indexes

**No new indexes required** - existing index on `authors.wallet_address` is sufficient for lookups.

## Migration

**No migration needed** - `twitter_handle` field already exists in production database (added in initial schema migration `5c7554583d44_initial_schema.py`).

## Storage Estimates

### Database

- **Author record**: ~200 bytes overhead + field data
  - `twitter_handle`: 0-15 bytes (NULL or username)
- **Growth rate**: 1 author per wallet (bounded by unique wallet_address)
- **Scale**: Negligible impact (existing table)

### In-Memory OAuth State

- **Per OAuth flow**: ~300 bytes (state + code_verifier + wallet + timestamps)
- **Concurrent flows**: Assume 10-100 concurrent OAuth flows (MVP)
- **Total memory**: ~3-30 KB (negligible)
- **Auto-cleanup**: Every 5 minutes (TTL expiry)

## Backup and Recovery

**Database**: Standard PostgreSQL backup (no special considerations for `twitter_handle`)

**In-Memory State**: Not backed up (acceptable loss - users simply retry OAuth)

## Privacy Considerations

- **X username is public data** (publicly visible on X platform)
- **No sensitive tokens stored** (access tokens discarded immediately)
- **Wallet address already public** (on-chain data)
- **No PII beyond public username**

## Audit Trail

**Future Enhancement** (out of scope for MVP):
- Optional audit log table for X account linking events:
  - `wallet_address`, `twitter_handle`, `linked_at` timestamp
  - Useful for analytics and support debugging

**MVP**: Use application logs (structlog) for tracking:
```python
logger.info(
    "twitter_account_linked",
    wallet_address=author.wallet_address,
    twitter_handle=username,
)
```

## Summary

- ✅ **Zero database changes** (use existing `authors.twitter_handle` field)
- ✅ **No Redis dependency** (in-memory `dict` for 5-min OAuth state)
- ✅ **Simple cleanup** (TTL checks on access, minimal overhead)
- ✅ **Permanent linking** (no unlink logic in data model)
- ✅ **Privacy-compliant** (public data only, no token storage)
