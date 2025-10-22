# Data Model: Unified Profile Page

**Feature Branch**: `008-unified-profile-page`
**Date**: 2025-10-22

This document describes the data entities, relationships, and state management for the unified profile page feature.

---

## Overview

The unified profile page **reads existing data** from the backend database and blockchain. No new database entities are required. This document describes how existing entities are consumed by the frontend.

---

## Entity Diagram

```
┌─────────────────┐         ┌─────────────────┐
│     Author      │         │      Token      │
├─────────────────┤         ├─────────────────┤
│ id (PK)         │◄────────│ author_id (FK)  │
│ wallet_address  │    1:N  │ token_id        │
│ prompt_text     │         │ status          │
│ twitter_handle  │         │ image_cid       │
│ created_at      │         │ metadata_cid    │
└─────────────────┘         │ created_at      │
                            └─────────────────┘

┌──────────────────────────────────────┐
│       ERC721Enumerable Contract      │
├──────────────────────────────────────┤
│ balanceOf(address)                   │
│ tokenOfOwnerByIndex(address, index)  │
│ tokenURI(tokenId)                    │
└──────────────────────────────────────┘
```

---

## Existing Entities (Database)

### 1. Author

**Table**: `authors`
**Source**: Backend database (PostgreSQL)

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `wallet_address` | String (42 chars) | Ethereum address (checksummed) |
| `prompt_text` | String (1-1000 chars) | AI generation prompt (nullable) |
| `twitter_handle` | String (255 chars) | X username (nullable) |
| `farcaster_handle` | String (255 chars) | Farcaster username (nullable, unused in this feature) |
| `created_at` | Timestamp (UTC) | Record creation time |

**Indexes**:
- Primary key on `id`
- Unique index on `wallet_address`

**Usage in Feature**:
- Prompt management UI reads/writes `prompt_text`
- X linking UI reads/writes `twitter_handle`
- Authored NFTs query uses `id` to filter tokens

---

### 2. Token

**Table**: `tokens_s0`
**Source**: Backend database (PostgreSQL)

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `token_id` | Integer | On-chain token ID (unique) |
| `author_id` | UUID | Foreign key to `authors.id` |
| `status` | Enum | Lifecycle status (detected, generating, uploading, ready, revealed, failed) |
| `image_cid` | String (255 chars) | IPFS CID for image (nullable) |
| `metadata_cid` | String (255 chars) | IPFS CID for metadata JSON (nullable) |
| `image_url` | String | Replicate URL for generated image (nullable) |
| `generation_attempts` | Integer | Retry counter for image generation |
| `generation_error` | String (1000 chars) | Error message if generation failed (nullable) |
| `reveal_tx_hash` | String (66 chars) | Transaction hash for reveal (nullable) |
| `error_data` | JSON | Additional error context (nullable) |
| `created_at` | Timestamp (UTC) | Record creation time |

**Indexes**:
- Primary key on `id`
- Unique index on `token_id`
- Index on `author_id` (for authored NFTs query)
- Index on `status` (for worker queries)

**Usage in Feature**:
- Prompt Author tab queries tokens where `author_id = current_user.author_id`
- NFT cards display `image_cid`, `metadata_cid`, `status`
- Pagination uses `created_at DESC` ordering

---

## Blockchain Data (Read-Only)

### 3. ERC721Enumerable Contract

**Contract**: `GliskNFT.sol`
**Network**: Base Sepolia
**Address**: `0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0` (from env var)

**Methods Used**:

| Function | Signature | Return Type | Description |
|----------|-----------|-------------|-------------|
| `balanceOf` | `balanceOf(address owner)` | `uint256` | Total NFTs owned by address |
| `tokenOfOwnerByIndex` | `tokenOfOwnerByIndex(address owner, uint256 index)` | `uint256` | Token ID at given index in owner's list |
| `tokenURI` | `tokenURI(uint256 tokenId)` | `string` | IPFS URI for token metadata (unused in MVP - OnchainKit handles) |

**Usage in Feature**:
- Collector tab calls `balanceOf` to get total owned NFTs
- Collector tab calls `tokenOfOwnerByIndex` for each index to get token IDs (batched via multicall)

---

## Frontend State Management

### 4. Tab State (Query Parameters)

**Source**: React Router `useSearchParams`

| Parameter | Type | Default | Valid Values |
|-----------|------|---------|--------------|
| `tab` | String | `"author"` | `"author"`, `"collector"` |

**State Transitions**:
```
No param → Set to "author" (replace history)
"author" → "collector" (user clicks tab, create history entry)
"collector" → "author" (user clicks tab, create history entry)
"invalid" → Render as "author" (validation fallback, no URL change)
```

**Persistence**: URL query parameter (survives refresh, shareable)

---

### 5. Pagination State (Component State)

**Source**: React `useState` per tab

| Tab | State Variable | Type | Default | Max |
|-----|----------------|------|---------|-----|
| Prompt Author | `authoredPage` | Number | 1 | `Math.ceil(totalAuthored / 20)` |
| Collector | `ownedPage` | Number | 1 | `Math.ceil(totalOwned / 20)` |

**State Lifecycle**:
- Created on tab mount
- Destroyed on tab unmount (state not preserved between switches)
- Reset to 1 when wallet address changes

**Rationale**: Simple `useState` aligns with constitution (no state management libraries for MVP)

---

### 6. NFT Data State (React Query/Wagmi)

**Source**: TanStack Query (via wagmi hooks)

| Data Source | Hook | Cache Key | Stale Time | Refetch Trigger |
|-------------|------|-----------|------------|-----------------|
| Authored NFTs | `useQuery` | `['authored-nfts', address, page]` | 30s | Wallet change, page change |
| Owned NFTs | `useInfiniteReadContracts` | `['owned-nfts', address]` | 30s | Wallet change |
| Author Status | `useQuery` | `['author', address]` | 60s | Wallet change |

**Cache Behavior**:
- Data persists in memory while tabs are mounted
- Switching tabs preserves cache (no refetch unless stale)
- Wallet change invalidates all caches

---

## Data Flow Diagrams

### Prompt Author Tab - Authored NFTs

```
┌────────────┐     GET /api/authors/{address}/tokens?offset=0&limit=20
│  Frontend  │────────────────────────────────────────────────────────►
│ (React)    │                                                         │
└────────────┘                                                         │
      ▲                                                                │
      │                                                                ▼
      │   { tokens: [...], total: 45, offset: 0, limit: 20 }   ┌──────────┐
      └────────────────────────────────────────────────────────│ FastAPI  │
                                                                │ Backend  │
                                                                └──────────┘
                                                                      │
                                                                      ▼
                                           SELECT * FROM tokens_s0
                                           WHERE author_id = ?
                                           ORDER BY created_at DESC
                                           OFFSET 0 LIMIT 20
                                                                ┌──────────┐
                                                                │PostgreSQL│
                                                                └──────────┘
```

### Collector Tab - Owned NFTs

```
┌────────────┐     balanceOf(address) → 45n
│  Frontend  │─────────────────────────────────────►
│ (React)    │                                      │
└────────────┘                                      │
      ▲                                             │
      │                                             ▼
      │   Multicall [                        ┌────────────┐
      │     tokenOfOwnerByIndex(addr, 0),    │   Base     │
      │     tokenOfOwnerByIndex(addr, 1),    │  Sepolia   │
      │     ...                              │    RPC     │
      │     tokenOfOwnerByIndex(addr, 19)    └────────────┘
      │   ] → [1n, 2n, 3n, ...]                    │
      └────────────────────────────────────────────┘
```

---

## Validation Rules

### Frontend Validation

| Field | Rule | Error Message |
|-------|------|---------------|
| `tab` query param | Must be "author" or "collector" | Fallback to "author" (silent) |
| `page` state | Must be >= 1 and <= maxPages | Disable pagination buttons |
| Wallet connection | Must be connected to view page | Show "Connect wallet" message |

### Backend Validation

| Field | Rule | Error Response |
|-------|------|----------------|
| `wallet_address` in URL | Must be valid Ethereum address (42 chars, 0x prefix) | 400 Bad Request (silent fallback in GET) |
| `offset` query param | Must be >= 0 | 400 Bad Request |
| `limit` query param | Must be 1-100 | 400 Bad Request |

---

## State Transitions

### Token Status (Not Modified by This Feature)

Existing token lifecycle (unchanged):

```
detected → generating → uploading → ready → revealed
   ↓           ↓           ↓          ↓
 failed      failed      failed    failed
```

**Feature Impact**: Frontend displays all statuses (no filtering). Unrevealed tokens show placeholder in NFTCard.

### Tab Navigation State Machine

```
State: "author"
  User clicks "Collector" → State: "collector" (URL: ?tab=collector)

State: "collector"
  User clicks "Author" → State: "author" (URL: ?tab=author)

State: undefined (no query param)
  On mount → State: "author" (URL: ?tab=author, replace history)

State: "invalid"
  On render → Display "author" tab (no URL change)
```

---

## Performance Considerations

### Database Queries

**Authored NFTs Endpoint**:
```sql
-- Count query (total for pagination)
SELECT COUNT(id) FROM tokens_s0 WHERE author_id = ?;

-- Data query (page 1)
SELECT * FROM tokens_s0
WHERE author_id = ?
ORDER BY created_at DESC
OFFSET 0 LIMIT 20;
```

**Indexes Used**:
- `author_id` index (FK) → O(log n) lookup
- `created_at` for ordering (consider adding index if queries slow)

**Expected Latency**: <100ms for 1000 tokens

### Blockchain Reads

**Multicall Batching**:
- Without batching: 21 RPC calls (1 balance + 20 tokens) → ~2 seconds
- With batching: 2 RPC calls (1 balance + 1 multicall) → ~500ms

**Rate Limits**:
- Free tier: 50 RPS
- With batching: 2 RPS for 20 NFTs → 25x safety margin

---

## Error States

### Backend API Errors

| Error | Cause | Frontend Behavior |
|-------|-------|-------------------|
| 500 Internal Server Error | Database connection failure | Show error message in Prompt Author tab NFT section, keep prompt/X sections functional |
| 400 Bad Request | Invalid wallet address format | Silent fallback (treat as 0 tokens) |
| 404 Not Found | Author doesn't exist | Return empty array (0 tokens) |

### Blockchain RPC Errors

| Error | Cause | Frontend Behavior |
|-------|-------|-------------------|
| Timeout | RPC endpoint overloaded | Show "Failed to load NFTs" with retry button |
| Rate Limit (429) | Exceeded 50 RPS | Automatic retry with exponential backoff |
| Network Error | User offline or RPC down | Show "Network error" with retry button |

---

## Security Considerations

**No sensitive data exposure**:
- Prompt text never returned via API (write-only per 006-author-profile-management)
- All queries scoped to connected wallet address (users can only see own data)
- Read-only blockchain calls (no transactions, no wallet signatures)

**Wallet validation**:
- Backend validates wallet address format before database query
- Frontend uses wagmi's `useAccount` (validated by wallet provider)

---

## Schema Changes

**None required**. This feature uses existing database schema:
- `authors` table (created in 006-author-profile-management)
- `tokens_s0` table (created in 003-003b-event-detection)
- `author_id` foreign key (created in 003-003b-event-detection)

---

## Summary

This feature is **read-only** and **schema-stable**:
- No new database tables or columns
- No database migrations required
- Backend adds 1 GET endpoint using existing repository patterns
- Frontend manages state via React hooks (useState, useSearchParams)
- Data fetching via wagmi (blockchain) and fetch (backend API)
