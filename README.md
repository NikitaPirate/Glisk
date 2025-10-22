# GLISK

NFT project built with AI-driven development methodology.

## Overview

GLISK is a monorepo for an NFT platform developed using GitHub Spec Kit methodology with AI assistance. The project follows a seasonal MVP approach, focusing on simplicity and rapid iteration.

The repository is organized into three main domains:
- `/contracts/` - Solidity smart contracts (ERC721Enumerable, batch minting, royalties)
- `/backend/` - Off-chain services (webhooks, workers, recovery)
- `/frontend/` - Web application (planned)

## Current Status

- ✅ **Contracts**: Complete NFT smart contract system with full test coverage
- ✅ **Audit**: Automated security audit process via `/audit` command
- ✅ **Backend**: Complete NFT lifecycle pipeline
  - Webhook event detection (Alchemy)
  - AI image generation (Replicate)
  - IPFS upload and metadata (Pinata)
  - Batch reveal automation (Keeper)
  - Token recovery from blockchain state
- 🚧 **Frontend**: User interface for minting and collection management

## Pipeline

```
Mint Event → Detection → Image Generation → IPFS Upload → Batch Reveal
            (webhook)   (Replicate AI)    (Pinata)     (on-chain)
```

**How it works:**
1. User mints NFT with text prompt via smart contract
2. Alchemy webhook triggers event detection (POST /webhooks/alchemy)
3. Image generation worker creates AI art from prompt (Replicate API)
4. IPFS upload worker stores image + metadata (Pinata)
5. Reveal worker batch-reveals tokens on-chain (gas optimized)

## Development Workflow

I follow GitHub Spec Kit methodology for specification-driven development. Learn more at: https://github.com/github/spec-kit

## Technical Stack

**Smart Contracts:**
- Solidity ^0.8.20, OpenZeppelin Contracts v5
- Foundry (forge, anvil, cast)
- Base Sepolia / Base Mainnet (Ethereum L2)

**Backend:**
- Python 3.13, FastAPI, SQLModel
- PostgreSQL 17 (async via psycopg3)
- Alembic migrations, structlog logging
- Replicate API (AI image generation)
- Pinata (IPFS storage)
- Alchemy (webhooks, RPC)
- web3.py (blockchain interaction)

**Development:**
- GitHub Spec Kit + AI assistance
- Foundry test framework with 100% coverage
- pytest + testcontainers

## Documentation

- **[Contracts](contracts/README.md)** - Smart contract implementation details
- **[Backend](backend/README.md)** - API, database, architecture
- **[Workers](backend/src/glisk/workers/README.md)** - Background workers (image generation, IPFS, reveal)
- **[Token Recovery](backend/src/glisk/cli/README.md)** - CLI for recovering missing tokens
- **[Specifications](specs/)** - Feature specs and implementation plans
- **[Constitution](.specify/memory/constitution.md)** - Development principles

## License

MIT
