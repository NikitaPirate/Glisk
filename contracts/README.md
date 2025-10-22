# GLISK Season 0 - Smart Contract

A blind box NFT collection with prompt author attribution, dynamic rewards, and comprehensive lifecycle management.

## Overview

The GLISK NFT contract implements a complete NFT ecosystem featuring:

- **Blind Box Minting**: Users mint surprise NFTs with prompt author attribution
- **50/50 Rewards Split**: Minting fees split equally between prompt authors and treasury
- **Progressive Reveal**: NFTs start with placeholder metadata, revealed permanently post-generation
- **Role-Based Access Control**: Owner (full control) and Keeper (limited operations) roles
- **Dynamic Pricing**: Adjustable mint price to maintain stable USD value
- **Season Lifecycle**: End season mechanism with 2-week author claim protection
- **ERC-2981 Royalties**: 2.5% marketplace royalties to treasury

## Tech Stack

- **Solidity**: 0.8.20
- **Framework**: Foundry (forge, anvil, cast)
- **OpenZeppelin Contracts**: v5.x
  - ERC721 (NFT standard)
  - ERC721Enumerable (token enumeration)
  - AccessControl (role management)
  - ReentrancyGuard (reentrancy protection)
  - ERC2981 (royalty standard)
- **Network**: Base (L2 Ethereum)

## Quick Start

### Prerequisites

```bash
# Install Foundry
curl -L https://foundry.paradigm.xyz | bash
foundryup

# Verify installation
forge --version
```

### Installation

```bash
# Clone the repository
cd contracts

# Install dependencies
forge install

# Build contracts
forge build

# Run tests
forge test

# Run tests with gas report
forge test --gas-report

# Run tests with coverage
forge coverage
```

### Configuration

1. Copy environment template:
```bash
cp .env.example .env
```

2. Configure `.env` with your values:
```env
# Network RPC URLs
BASE_MAINNET_RPC_URL=https://base-mainnet.g.alchemy.com/v2/YOUR_API_KEY
BASE_SEPOLIA_RPC_URL=https://base-sepolia.g.alchemy.com/v2/YOUR_API_KEY

# Deployment account (NEVER commit actual keys!)
PRIVATE_KEY=0x...

# Contract configuration
NFT_NAME="GLISK Season 0"
NFT_SYMBOL="GLISK0"
PLACEHOLDER_URI=ipfs://QmPlaceholder
INITIAL_MINT_PRICE=1000000000000000  # 0.001 ETH

# Block explorer API key (for verification)
BASESCAN_API_KEY=YOUR_BASESCAN_API_KEY
```

## Current Deployment

**Base Sepolia Testnet**:
- Contract: `0x569d456c584Ac2bb2d66b075a31278630E7d43a0`
- Explorer: https://sepolia.basescan.org/address/0x569d456c584ac2bb2d66b075a31278630e7d43a0
- Deployed: October 2025

## Deployment

### Local Development (Anvil)

```bash
# Start local chain
anvil

# Deploy to local chain
forge script script/Deploy.s.sol --rpc-url http://localhost:8545 --broadcast

# Deployed contract address will be logged and saved to deployments/localhost.json
```

### Base Sepolia Testnet

```bash
# Deploy to testnet
forge script script/Deploy.s.sol --rpc-url base_sepolia --broadcast --verify

# Contract will be automatically verified on Basescan
```

### Base Mainnet

```bash
# Deploy to mainnet (requires mainnet funds)
forge script script/Deploy.s.sol --rpc-url base_mainnet --broadcast --verify

# IMPORTANT: Test thoroughly on Sepolia first!
```

## Contract Architecture

### Core Features

#### 1. Minting (User Story 1)
```solidity
// Mint NFTs with prompt author attribution
function mint(address promptAuthor, uint256 quantity) external payable
```

- Batch minting (1-50 NFTs per tx)
- 50/50 payment split (author rewards / treasury)
- Overpayment goes entirely to treasury
- Reentrancy protected

#### 2. Author Rewards (User Story 2)
```solidity
// Authors claim their accumulated rewards
function claimAuthorRewards() external

// View claimable balance
function authorClaimable(address author) external view returns (uint256)
```

- Pull payment pattern for security
- No revert on zero balance
- Reentrancy protected

#### 3. NFT Reveal (User Story 8)
```solidity
// Reveal tokens with permanent URIs
function revealTokens(uint256[] calldata tokenIds, string[] calldata uris) external

// Update placeholder for unrevealed tokens
function setPlaceholderURI(string memory newURI) external

// Check if token is revealed
function isRevealed(uint256 tokenId) external view returns (bool)
```

- Placeholder URI for unrevealed tokens (updateable)
- Batch reveal operation
- Immutable after reveal
- Owner or Keeper can reveal

#### 4. Treasury Management (User Story 5)
```solidity
// Withdraw all treasury funds
function withdrawTreasury() external

// View treasury balance
function treasuryBalance() external view returns (uint256)

// Contract accepts direct ETH payments
receive() external payable
```

- Accumulates 50% of mints + overpayments + direct payments
- Owner-only withdrawal
- Reentrancy protected

#### 5. Dynamic Pricing (User Story 3)
```solidity
// Update mint price
function setMintPrice(uint256 newPrice) external
```

- Owner or Keeper can update
- Maintains ~$0.05 USD target by adjusting for ETH volatility
- Does not affect past mints

#### 6. Role Management (User Story 6)
```solidity
// Owner operations (DEFAULT_ADMIN_ROLE):
- Grant/revoke roles
- End season
- Withdraw treasury
- Update placeholder URI
- Update royalties
- All Keeper operations

// Keeper operations (KEEPER_ROLE):
- Reveal tokens
- Update mint price
```

#### 7. Season Lifecycle (User Story 4)
```solidity
// End season (stops minting)
function endSeason() external

// Sweep unclaimed rewards after 14 days
function sweepUnclaimedRewards(address[] calldata authors) external
```

- Permanent season end
- 2-week protection period for author claims
- Batch sweep operation

#### 8. Royalties (User Story 7)
```solidity
// Update royalty configuration
function setDefaultRoyalty(address receiver, uint96 feeNumerator) external
```

- ERC-2981 compliant
- Default: 2.5% to treasury
- Owner can update percentage and receiver

#### 9. Enumeration Functions
```solidity
// Get total minted tokens
function totalSupply() external view returns (uint256)

// Enumerate all tokens by index (0 to totalSupply-1)
function tokenByIndex(uint256 index) external view returns (uint256)

// Enumerate owner's tokens by index (0 to balanceOf-1)
function tokenOfOwnerByIndex(address owner, uint256 index) external view returns (uint256)
```

- Standard ERC721Enumerable interface
- ~80-100% gas increase for better marketplace compatibility
- Enables token discovery and pagination

## Testing

### Test Coverage

**Total: 109 tests passing**

- **Unit Tests**: 81 tests
  - Minting: 8 tests
  - Rewards: 7 tests
  - Reveal: 15 tests
  - Treasury: 11 tests
  - Pricing: 6 tests
  - Access Control: 11 tests
  - Season Lifecycle: 12 tests
  - Royalties: 9 tests

- **Integration Tests**: 8 tests
  - Complete user journeys
  - Multi-user concurrent scenarios
  - Season lifecycle workflows

- **Fuzz Tests**: 11 tests (5000 runs each)
  - Property-based testing with randomized inputs
  - Payment distribution verification
  - Edge case discovery

- **Invariant Tests**: 9 tests (256 runs, 128K calls each)
  - Balance conservation
  - Token ID uniqueness
  - Reveal immutability
  - Value conservation
  - Season permanence

**Coverage**: **100% on GliskNFT.sol** (lines, statements, branches, functions)

### Running Tests

```bash
# Run all tests
forge test

# Run specific test file
forge test --match-path test/unit/GliskNFT.Minting.t.sol

# Run with verbosity
forge test -vvv

# Run with gas report
forge test --gas-report

# Run fuzz tests with more runs
forge test --fuzz-runs 10000

# Generate coverage report
forge coverage

# Generate detailed coverage
forge coverage --report lcov
```

## Gas Costs

Key operations (average gas costs with ERC721Enumerable):

| Operation | Gas Cost |
|-----------|----------|
| Mint (single) | ~220,000 |
| Mint (batch 5) | ~772,000 (~154k per token) |
| Claim rewards | ~67,000 |
| Reveal (single) | ~206,000 |
| Reveal (batch 10) | ~540,000 |
| Update mint price | ~29,000 |
| Withdraw treasury | ~69,000 |
| End season | ~66,000 |

**Note**: ERC721Enumerable adds ~80-100% gas overhead to minting compared to base ERC721, but provides standard enumeration functions for marketplace compatibility.

**Deployment Cost**: ~2,600,000 gas (~$6-12 on Base at typical gas prices)

## Security

### Security Features

- **Reentrancy Protection**: All external value transfers use `nonReentrant` modifier
- **Access Control**: OpenZeppelin role-based permissions
- **Pull Payment Pattern**: Authors and treasury pull funds rather than push
- **Checks-Effects-Interactions**: State updated before external calls
- **Integer Safety**: Solidity 0.8.20 built-in overflow protection
- **Input Validation**: All inputs validated with custom errors

### Audit Checklist

- [X] Run Slither static analysis ✅ **PASSED** (0 actionable issues - see SLITHER-ANALYSIS.md)
- [X] Review all external calls ✅ (All use proper checks-effects-interactions pattern)
- [X] Verify role permissions ✅ (100% test coverage on access control)
- [X] Test season lifecycle edge cases ✅ (12 dedicated season tests + integration tests)
- [X] Verify payment distributions ✅ (Fuzz tests verify 50/50 split)
- [X] Test reentrancy scenarios ✅ (Dedicated reentrancy attack tests)
- [X] Review gas optimization opportunities ✅ (Gas costs documented and acceptable)
- [ ] Third-party security audit (recommended for mainnet)

### Static Analysis Results

**Status**: ✅ **PASSED** - No security vulnerabilities found

```bash
# Run Slither analysis using uvx (2025 best practice)
uvx --from slither-analyzer slither src/GliskNFT.sol

# Alternative: Install globally
pip3 install slither-analyzer
slither src/GliskNFT.sol
```

**Summary**: 33 findings analyzed, 0 actionable security issues
- All findings are false positives, expected behavior, or OpenZeppelin library code
- Detailed analysis available in `SLITHER-ANALYSIS.md`
- Contract follows all modern Solidity security best practices

## Project Structure

```
contracts/
├── src/
│   └── GliskNFT.sol              # Main contract
├── script/
│   ├── Deploy.s.sol              # Deployment script
│   └── Verify.s.sol              # Verification helper
├── test/
│   ├── unit/                     # Unit tests by feature
│   │   ├── GliskNFT.Minting.t.sol
│   │   ├── GliskNFT.Rewards.t.sol
│   │   ├── GliskNFT.Reveal.t.sol
│   │   ├── GliskNFT.Treasury.t.sol
│   │   ├── GliskNFT.Pricing.t.sol
│   │   ├── GliskNFT.Access.t.sol
│   │   ├── GliskNFT.Season.t.sol
│   │   └── GliskNFT.Royalty.t.sol
│   ├── integration/              # End-to-end tests
│   │   └── GliskNFT.integration.t.sol
│   ├── fuzz/                     # Fuzz tests
│   │   └── GliskNFT.fuzz.t.sol
│   └── invariant/                # Invariant tests
│       └── GliskNFT.invariant.t.sol
├── abi/
│   └── GliskNFT.json             # Contract ABI export
├── deployments/                  # Deployment artifacts
│   ├── localhost.json
│   ├── base-sepolia.json
│   └── base.json
├── foundry.toml                  # Foundry configuration
├── .env.example                  # Environment template
└── README.md                     # This file
```

## Post-Deployment Operations

### Grant Keeper Role

```bash
# Grant KEEPER_ROLE to operational address
forge script script/Deploy.s.sol --sig "grantKeeperRole(address,address)" \
  <CONTRACT_ADDRESS> <KEEPER_ADDRESS> \
  --rpc-url base_sepolia --broadcast
```

### Update Mint Price

```bash
# Update price (example: 0.002 ETH = 2000000000000000 wei)
forge script script/Deploy.s.sol --sig "updateMintPrice(address,uint256)" \
  <CONTRACT_ADDRESS> 2000000000000000 \
  --rpc-url base_sepolia --broadcast
```

### Verify Contract

```bash
# Generate verification command
forge script script/Verify.s.sol --sig "verifyOnBasescan(address)" \
  <CONTRACT_ADDRESS>

# Or verify directly
forge verify-contract <CONTRACT_ADDRESS> GliskNFT \
  --chain base-sepolia \
  --constructor-args $(cast abi-encode \
    "constructor(string,string,string,uint256)" \
    "GLISK Season 0" "GLISK0" "ipfs://QmPlaceholder" 1000000000000000)
```

## Integration with Frontend

### ABI Location

Contract ABI is exported to: `abi/GliskNFT.json`

### Key Integration Points

```typescript
// Mint NFTs
await contract.mint(
  promptAuthorAddress,
  quantity,
  { value: mintPrice * quantity }
);

// Check author rewards
const claimable = await contract.authorClaimable(authorAddress);

// Claim rewards
await contract.claimAuthorRewards();

// Check token metadata
const uri = await contract.tokenURI(tokenId);
const isRevealed = await contract.isRevealed(tokenId);
const author = await contract.tokenPromptAuthor(tokenId);

// Query mint price
const currentPrice = await contract.mintPrice();

// Check season status
const ended = await contract.seasonEnded();
```

## License

MIT

## Support

For questions or issues:
- Review [quickstart.md](../specs/001-full-smart-contract/quickstart.md) for detailed scenarios
- Check [spec.md](../specs/001-full-smart-contract/spec.md) for requirements
- Consult [plan.md](../specs/001-full-smart-contract/plan.md) for architecture

## Deployment Checklist

Before mainnet deployment:

- [ ] All 109 tests passing
- [ ] Coverage report shows 100% on GliskNFT.sol
- [ ] Static analysis (Slither) reviewed
- [ ] Testnet deployment successful
- [ ] Testnet integration testing complete
- [ ] Security audit completed (recommended)
- [ ] Deployment artifacts backed up
- [ ] Multi-sig wallet setup for Owner role
- [ ] Keeper addresses configured
- [ ] Frontend integration tested
- [ ] Metadata URIs prepared and uploaded to IPFS
- [ ] Gas costs reviewed and acceptable
- [ ] Emergency procedures documented

## Version

**Contract Version**: 1.0.0
**Solidity**: 0.8.20
**OpenZeppelin**: 5.x
**Last Updated**: 2025-10-12
