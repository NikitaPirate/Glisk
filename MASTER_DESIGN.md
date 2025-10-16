# Backend Architecture Master Design

**Version**: 1.1
**Last Updated**: 2025-10-16
**Purpose**: Compact reference for all backend implementation specs (003a, 003b, 003c...)

This document consolidates key architectural decisions from spec.md, plan.md, research.md, data-model.md, and API contracts into a single reference.

---

## Implementation Strategy

**Chosen Approach**: **Strategy 3 - Feature-Priority Incremental**

Implement complete features one at a time based on priority. Each spec adds one complete user story.

### Spec Sequence

**003a - Foundation** (1 week)
- **Scope**: Complete shared infrastructure only
- **Includes**: Database models, repositories, UoW, core services, Alembic migrations, test infrastructure, FastAPI skeleton
- **Deliverable**: Foundation ready, no features yet

**003b - Event Detection (US1)** (3-5 days)
- **Scope**: Mint event detection and storage
- **Includes**: Webhook handler, signature validation, event parsing, event recovery, webhook API route
- **Deliverable**: System detects and stores mints (but doesn't process them)

**003c - Image Generation (US2)** (4-6 days)
- **Scope**: AI image generation pipeline
- **Includes**: Replicate client + fallback service, image generation worker, retry logic + error handling
- **Deliverable**: Images generated for detected mints (but not uploaded)

**003d - IPFS & Reveal (US3 + US4)** (5-7 days)
- **Scope**: Complete the reveal pipeline
- **Includes**: Pinata client + IPFS worker, Keeper service + reveal worker, batch reveal + gas optimization
- **Deliverable**: **MVP - End-to-end pipeline working**

**003e - Operations (US5 + US6 + US7)** (1 week)
- **Scope**: All operational tooling
- **Includes**: Author management, manual reveal CLI, health monitoring, admin API
- **Deliverable**: Production-ready with full tooling

**MVP Timeline**: 3-4 weeks total (003a → 003d)

**Rationale**: Solid foundation first, then features incrementally. Each spec is focused and testable independently. Clear feature boundaries for tracking progress.

---

## Executive Summary

**What**: Backend system for NFT reveal automation
**How**: Event-driven pipeline (mint → generate → IPFS → reveal)
**Stack**: Python 3.14 + FastAPI + PostgreSQL + SQLModel + psycopg
**Philosophy**: Seasonal MVP, simple direct implementations, rebuild > maintain

---

## Architectural Decisions (from research.md)

### 1. Event Detection Strategy

**Decision**: Alchemy webhooks (native retry/replay)
**Why**: Production-grade delivery, no custom polling needed

- Primary: Alchemy webhook endpoint (`POST /webhooks/alchemy`)
- Recovery: `eth_getLogs` via Alchemy SDK for missed events
- Deduplication: Database UNIQUE constraint on `(tx_hash, log_index)`
- State: Store `last_processed_block` for recovery verification

**No custom event listener** - Alchemy already solved this problem.

### 2. Retry & Queue Strategy

**Decision**: Database queue + worker polling (0.1-1s intervals)
**Why**: Simplicity, durability, no external dependencies (Redis/RabbitMQ)

- Workers poll: `SELECT ... WHERE status='X' LIMIT N FOR UPDATE SKIP LOCKED`
- Short outages: Workers keep polling, backlog processed naturally
- Long outages: Tokens accumulate, workers process when service recovers
- Per-token retry tracking: `attempt_count` field in job tables
- External API retries: `tenacity` library (3 attempts for network blips)

**Key**: Controlled batching prevents overwhelming services when they recover.

### 3. Batch Reveal & Gas Handling

**Decision**: Short wait (3-5s) + web3.py gas strategies
**Why**: Fast UX (don't make users wait), leverage web3.py EIP-1559 optimization

- Batch triggers: Wait 3-5s for more tokens OR collect 50 tokens OR manual trigger
- Gas: Use `web3.py` built-in `medium_gas_price_strategy` (no custom monitoring)
- Gas buffer: 20% (`gas_limit = int(estimate * 1.2)`)
- Batch size: Max 50 tokens per transaction

**No custom gas monitoring** - web3.py handles EIP-1559 automatically.

### 4. Task Queue Pattern

**Decision**: Direct database polling (no message broker)
**Why**: Seasonal MVP simplicity

- State machine: Token status as queue: `detected → generating → uploading → ready → revealed`
- Polling interval: **1 second** (configurable 0.1-5s)
- Concurrency: `FOR UPDATE SKIP LOCKED` for worker coordination
- Scale: Works well for 50-500 tasks/minute (far exceeds needs)

### 5. Python Version

**Decision**: Standard Python 3.14 (with GIL)
**Why**: Workload is I/O-bound (API calls), asyncio handles concurrency

- Use `python:3.14-slim` Docker image
- No free-threaded mode needed (would add compatibility risks)
- GIL is not a bottleneck for I/O-bound operations

### 6. Repository Pattern

**Decision**: Simple direct repositories (no generic base classes)
**Why**: Seasonal MVP, AI-generated code, easy to write specific methods

- ✅ Keep: UoW pattern, `setup_db_session()`, `create_uow_factory()`
- ❌ Skip: Generic repository base classes
- ✅ Write: Direct methods (`get_pending_for_generation()` vs generic `get_all()`)

**Clear intent over abstraction.**

### 7. Docker Compose Architecture

**Decision**: Monolithic FastAPI with background workers
**Why**: Seasonal MVP simplicity, easier deployment, shared resources

Services:
- `postgres` - Database (PostgreSQL 17)
- `backend` - FastAPI application with 3 background asyncio workers

Workers run as background tasks within FastAPI lifespan:
- Image generation worker (polls detected tokens)
- IPFS upload worker (polls uploading tokens)
- Reveal worker (polls ready tokens, batch reveals)

All workers share the same UoW factory and database connection pool.

---

## Data Model (Compact Schema)

### Tables

#### 1. `authors` (Global table)
- `id` (PK), `wallet_address` (UNIQUE), `twitter_handle`, `farcaster_handle`, `prompt_text`
- Indexed: `wallet_address`

#### 2. `tokens_s0` (Season 0 table)
- `token_id` (PK), `author_id` (FK), `minter_address`, `mint_timestamp`
- `status` (enum), `image_cid`, `metadata_cid`, `reveal_tx_hash`, `error_log` (jsonb)
- Indexed: `(status, mint_timestamp)`, `author_id`, `minter_address`

**Status enum**: `detected` → `generating` → `uploading` → `ready` → `revealed` | `failed`

#### 3. `mint_events`
- Event log: `tx_hash`, `block_number`, `log_index`, `minter`, `author`, `token_ids`, `quantity`
- UNIQUE: `(tx_hash, log_index)` for deduplication

#### 4. `image_generation_jobs`
- Tracking: `token_id` (FK), `prompt_text`, `service` (replicate/selfhosted), `status`, `attempt_number`

#### 5. `ipfs_upload_records`
- Tracking: `token_id` (FK), `upload_type` (image/metadata), `ipfs_cid`, `status`, `attempt_number`

#### 6. `reveal_transactions`
- Batch tracking: `tx_hash`, `token_ids[]`, `metadata_uris[]`, `status`, `gas_price_gwei`

#### 7. `system_state`
- Singleton: `state_key` (PK), `state_value` (jsonb)
- Keys: `last_processed_block`, `current_gas_price_gwei`, `service_health`

### State Machine

```
Mint Event → detected → generating → uploading → ready → revealed (success)
                  ↓          ↓           ↓          ↓
                  └──────────┴───────────┴──────────┘
                              failed (terminal)
```

---

## API Contracts (Compact Overview)

### Webhook API
- `POST /webhooks/alchemy` - Receive Alchemy webhook (signature validation)
  - Headers: `X-Alchemy-Signature`
  - Response: `200 OK` (success), `202 Accepted` (async), `409 Conflict` (duplicate)

### Health API
- `GET /health` - Overall system health
- `GET /health/blockchain` - Event listener status (`last_processed_block`, `blocks_behind`)
- `GET /health/workers` - Worker status (`pending_jobs`, `active_jobs`)
- `GET /health/metrics` - Metrics (`total_mints`, `total_revealed`, `error_rate_24h`)

### Admin API (CLI access only, no auth)
- `POST /admin/reveal` - Manual reveal for token IDs
- `GET /admin/token/{token_id}` - Token status with processing history
- `GET /admin/tokens?status=X` - List tokens by status (pagination)
- `GET /admin/system/state` - System operational state

---

## Tech Stack

### Core
- **Runtime**: Python 3.14 (standard, GIL-enabled)
- **Framework**: FastAPI (monolithic)
- **Database**: PostgreSQL 14+ with SQLModel (Pydantic + SQLAlchemy)
- **DB Driver**: psycopg (psycopg3 with async support)
- **Migrations**: Alembic
- **Async**: asyncio + psycopg (async) + httpx

### Dependencies
- `web3.py` - Blockchain interaction, gas strategies
- `tenacity` - Transient retry logic (network errors)
- `structlog` - Structured logging
- `pydantic` - Config validation (BaseSettings)

### External Services
- **Blockchain**: Alchemy API (webhooks + RPC on Base L2)
- **IPFS**: Pinata (fixed provider)
- **Image Gen**: Replicate (primary), easy to switch providers

### Deployment
- **Containerization**: Docker (`python:3.14-slim`)
- **Orchestration**: Docker Compose
- **Config**: Single `.env` file at repository root

---

## Key Patterns

### 1. Unit of Work Pattern

```python
# Bootstrap (main.py)
session_factory = setup_db_session(db_connection)
uow_factory = create_uow_factory(session_factory)

# Usage
async with uow_factory() as uow:
    author = await uow.authors.get_by_wallet(wallet)
    token = await uow.tokens.get_by_id(token_id)
    await uow.commit()
```

### 2. Simple Direct Repositories

```python
class TokenRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_pending_for_generation(self, limit: int = 10) -> list[Token]:
        """Get tokens waiting for image generation (FOR UPDATE SKIP LOCKED)"""
        result = await self._session.execute(
            select(Token)
            .where(Token.status == TokenStatus.DETECTED)
            .order_by(Token.mint_timestamp.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return list(result.scalars().all())
```

**No generic base classes** - write specific methods as needed.

### 3. Background Workers (Monolithic)

```python
# app.py - Workers started in FastAPI lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings()
    session_factory = setup_db_session(settings.database_url)
    uow_factory = create_uow_factory(session_factory)

    # Start background workers
    worker_tasks = []
    if settings.enable_image_worker:
        worker_tasks.append(asyncio.create_task(image_worker_loop(uow_factory)))
    if settings.enable_ipfs_worker:
        worker_tasks.append(asyncio.create_task(ipfs_worker_loop(uow_factory)))
    if settings.enable_reveal_worker:
        worker_tasks.append(asyncio.create_task(reveal_worker_loop(uow_factory)))

    app.state.worker_tasks = worker_tasks
    yield

    # Graceful shutdown
    for task in worker_tasks:
        task.cancel()
    await asyncio.gather(*worker_tasks, return_exceptions=True)

# workers/image_worker.py
async def image_worker_loop(uow_factory):
    while True:
        async with await uow_factory() as uow:
            tokens = await uow.tokens.get_pending_for_generation(limit=10)
            for token in tokens:
                # Process token...
                token.mark_uploading()
        await asyncio.sleep(1.0)
```

---

## External Integrations

### Alchemy (Blockchain Events)
- **Webhook**: `POST /webhooks/alchemy` with signature verification
- **Recovery**: `eth_getLogs({fromBlock: last_processed + 1, toBlock: 'latest'})`
- **Network**: Base L2 (BASE_MAINNET or BASE_SEPOLIA)

### Pinata (IPFS)
- **Auth**: API key + secret
- **Upload Image**: `POST /pinning/pinFileToIPFS`
- **Upload Metadata**: `POST /pinning/pinJSONToIPFS`
- **Returns**: IPFS CID (`Qm...` or `bafy...`)

### Replicate (Image Generation)
- **Auth**: API token
- **Primary**: Replicate API (configurable model)
- **Fallback**: Self-hosted (easy to switch providers)
- **Returns**: Image URL (download and cache locally)

---

## Configuration (.env)

### Database
```bash
DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/glisk_s0
```

### Blockchain
```bash
ALCHEMY_API_KEY=your_key
ALCHEMY_WEBHOOK_SECRET=your_secret
GLISK_NFT_CONTRACT_ADDRESS=0x...
KEEPER_PRIVATE_KEY=0x...
NETWORK=BASE_MAINNET  # or BASE_SEPOLIA
```

### IPFS
```bash
PINATA_API_KEY=your_key
PINATA_API_SECRET=your_secret
```

### Image Generation
```bash
REPLICATE_API_TOKEN=your_token
SELFHOSTED_IMAGE_API_URL=http://localhost:8080  # Optional fallback
```

### Workers
```bash
ENABLE_IMAGE_WORKER=true  # Enable image generation worker
ENABLE_IPFS_WORKER=true  # Enable IPFS upload worker
ENABLE_REVEAL_WORKER=true  # Enable reveal worker
WORKER_POLL_INTERVAL=1.0  # seconds (0.1-5.0)
BATCH_REVEAL_WAIT_SECONDS=5  # Wait for more tokens (3-5s)
BATCH_REVEAL_MAX_TOKENS=50  # Max batch size
GAS_STRATEGY=medium  # slow, medium, fast (web3.py)
REVEAL_GAS_BUFFER_MULTIPLIER=1.2  # 20% buffer
```

### Defaults
```bash
DEFAULT_AUTHOR_WALLET=0xglisknftcontract  # For unregistered authors
DEFAULT_PROMPT="A glitchy digital art piece"  # Fallback prompt
```

---

## Project Structure

```
backend/
├── src/glisk/
│   ├── core/
│   │   ├── config.py              # Pydantic BaseSettings
│   │   ├── database.py            # setup_db_session()
│   │   ├── timezone.py            # UTC timezone init
│   │   └── dependencies.py        # FastAPI DI
│   ├── models/                    # SQLModel classes (7 tables)
│   ├── repositories/              # Simple direct repos (no base class)
│   ├── uow.py                     # UoW + create_uow_factory()
│   ├── services/                  # (003b-003e)
│   │   ├── blockchain/            # webhook_handler, event_recovery, keeper
│   │   ├── image_generation/      # replicate_client, generator_service
│   │   ├── ipfs/                  # pinata_client, uploader_service
│   │   └── metadata/              # builder
│   ├── workers/                   # (003c-003e) Background asyncio tasks
│   │   ├── image_worker.py        # Poll detected → generate
│   │   ├── ipfs_worker.py         # Poll uploading → IPFS
│   │   └── reveal_worker.py       # Poll ready → batch reveal
│   ├── api/                       # (003b-003e)
│   │   └── routes/                # health, admin, webhooks
│   ├── cli/                       # (003e)
│   │   └── manual_reveal.py       # Emergency CLI
│   └── app.py                     # FastAPI app with lifespan workers
├── tests/
│   ├── conftest.py                # testcontainers fixtures
│   ├── test_repositories.py
│   ├── test_state_transitions.py
│   └── test_uow.py
├── alembic/                       # Migrations
├── Dockerfile
├── entrypoint.sh
├── pyproject.toml                 # uv project
└── README.md
```

---

## Testing Strategy (Constitution v1.2.0)

**Philosophy**: Focused testing, avoid maintenance burden during rapid iteration

### Mandatory TDD
- **Repository Layer**: Complex logic only (concurrency with `FOR UPDATE SKIP LOCKED`, batch operations, transactions)
- **Financial Operations**: Anything affecting user funds (gas estimation, reveal transactions, payment flows)
- **Critical Paths**: Integration tests for end-to-end flows (event detection → reveal pipeline)

### Skip Testing
- Simple CRUD operations (add, get_by_id, basic updates)
- Battle-tested libraries (web3.py, FastAPI, SQLModel internals)
- Checkbox testing for rapid iteration

### Test Infrastructure
- **Tool**: pytest + testcontainers (PostgreSQL)
- **Fixtures**: Session-scoped containers, AsyncEngine, AsyncSession with table truncation
- **UTC Timezone**: Session-scoped autouse fixture (`os.environ["TZ"] = "UTC"`)

---

## Deployment

### Local Development
```bash
# Start full stack (postgres + backend with 3 workers)
docker compose up --build

# Migrations run automatically via entrypoint.sh

# Add test author
docker compose exec postgres psql -U glisk -d glisk_s0 -c \
  "INSERT INTO authors (wallet_address, prompt_text) VALUES ('0x123...', 'A cool prompt')"
```

### Production (VPS)
- Same `docker-compose.yml`, production `.env`
- Reverse proxy (nginx) for HTTPS
- Alchemy webhook → `POST https://api.glisk.io/webhooks/alchemy`

---

## Key Principles (GLISK Constitution)

1. **Simplicity First**: Direct implementations, avoid premature abstraction
2. **Seasonal MVP**: Ship working code quickly, rebuild > maintain (1-3 months)
3. **Clear Over Clever**: Explicit code, descriptive names, no language tricks
4. **Monorepo Structure**: All backend in `/backend/`, respect domain boundaries
5. **Smart Contract Security**: Backend uses audited contracts, secure Keeper wallet

---

## Version History

- **v1.2** (2025-10-16): Updated to monolithic architecture with background workers
- **v1.1** (2025-10-16): Updated with Strategy 3 implementation approach, psycopg driver
- **v1.0** (2025-10-16): Initial master design document from spec/plan/research/data-model/contracts

---

## Quick Reference Commands

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Manual reveal CLI
python -m src.cli.manual_reveal --token-ids 42 43 44

# Check health
curl http://localhost:8000/health

# View token status
curl http://localhost:8000/admin/token/42
```

---

**Next Steps**: Use this document as reference for creating focused specs (003a, 003b, 003c)
