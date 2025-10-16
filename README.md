# GLISK

NFT project built with AI-driven development methodology.

## Overview

GLISK is a monorepo for an NFT platform developed using GitHub Spec Kit methodology with AI assistance. The project follows a seasonal MVP approach, focusing on simplicity and rapid iteration.

The repository is organized into three main domains:
- `/contracts/` - Solidity smart contracts
- `/backend/` - Off-chain services (planned)
- `/frontend/` - Web application (planned)

## Current Status

- ✅ **Contracts**: Complete NFT smart contract system with full test coverage
- ✅ **Audit**: Automated security audit process via `/audit` command
- 🚧 **Backend**: Event listening and image generation services
- 🚧 **Frontend**: User interface for minting and collection management

## Development Workflow

I follow GitHub Spec Kit methodology for specification-driven development. Learn more at: https://github.com/github/spec-kit

## Technical Stack

- **Smart Contracts**: Solidity ^0.8.20, OpenZeppelin Contracts v5
- **Framework**: Foundry (forge, anvil, cast)
- **Network**: Base (Ethereum L2)
- **Development**: GitHub Spec Kit + AI assistance
- **Testing**: Foundry test framework with 100% coverage

## Documentation

- **[Contracts](contracts/README.md)** - Smart contract implementation details
- **[Specifications](specs/001-full-smart-contract/spec.md)** - Technical requirements
- **[Constitution](.specify/memory/constitution.md)** - Development principles

## License

MIT
