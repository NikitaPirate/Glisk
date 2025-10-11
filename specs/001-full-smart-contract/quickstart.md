# Quickstart Guide: GLISK Smart Contract

**Feature**: 001-full-smart-contract
**Date**: 2025-10-10
**Purpose**: Setup, deployment, and usage guide for GLISK Season 0 NFT contract

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Project Setup](#project-setup)
3. [Local Development](#local-development)
4. [Testing](#testing)
5. [Deployment](#deployment)
6. [Contract Interaction](#contract-interaction)
7. [Common Operations](#common-operations)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Tools

- **Foundry**: Solidity development toolkit
  ```bash
  # Install Foundry
  curl -L https://foundry.paradigm.xyz | bash
  foundryup
  ```

- **Git**: Version control
  ```bash
  git --version  # Should be 2.0+
  ```

- **Base RPC Access**: Get API key from:
  - [Alchemy](https://www.alchemy.com/) (recommended)
  - [QuickNode](https://www.quicknode.com/)
  - [Infura](https://www.infura.io/)

- **Basescan API Key**: For contract verification
  - Sign up at [Basescan](https://basescan.org/apis)

### Recommended Tools

- **jq**: JSON processing for scripts
  ```bash
  # macOS
  brew install jq

  # Linux
  sudo apt-get install jq
  ```

- **cast**: CLI tool (included with Foundry)
  ```bash
  cast --version
  ```

---

## Project Setup

### 1. Clone Repository

```bash
# Clone the GLISK monorepo
git clone https://github.com/your-org/glisk.git
cd glisk

# Navigate to contracts directory
cd contracts
```

### 2. Install Dependencies

```bash
# Install OpenZeppelin contracts and dependencies
forge install OpenZeppelin/openzeppelin-contracts@v5.0.0

# Update dependencies
forge update
```

### 3. Configure Environment

Create `.env` file in `contracts/` directory:

```bash
# Copy example environment file
cp .env.example .env
```

Edit `.env` with your values:

```bash
# Network RPCs
BASE_MAINNET_RPC_URL=https://base-mainnet.g.alchemy.com/v2/YOUR_API_KEY
BASE_SEPOLIA_RPC_URL=https://base-sepolia.g.alchemy.com/v2/YOUR_API_KEY

# Deployment account (NEVER commit this!)
PRIVATE_KEY=0x1234567890abcdef...  # Your deployer private key

# Contract configuration
PLACEHOLDER_URI=ipfs://QmXXXXXXXXXXXXXXXXXXXXXXXXXXXX/placeholder.json
INITIAL_MINT_PRICE=15000000000000  # 0.000015 ETH (~$0.05 USD, adjust based on ETH price)

# Verification
BASESCAN_API_KEY=YOUR_BASESCAN_API_KEY

# Optional: Etherscan for Ethereum mainnet
ETHERSCAN_API_KEY=YOUR_ETHERSCAN_API_KEY
```

### 4. Verify Setup

```bash
# Check Foundry installation
forge --version
# Expected: forge 0.2.0 (or newer)

# Compile contracts (should pass)
forge build

# Run tests (should pass)
forge test

# Check dependencies
forge tree
```

---

## Local Development

### Start Local Chain

```bash
# Start Anvil (local Ethereum node)
anvil

# In another terminal, deploy to local chain
forge script script/Deploy.s.sol --rpc-url http://localhost:8545 --broadcast
```

### Development Workflow

1. **Write Code**: Edit `contracts/src/GliskNFT.sol`
2. **Compile**: `forge build`
3. **Test**: `forge test`
4. **Format**: `forge fmt`
5. **Lint**: `forge lint` (if configured)

### Hot Reload

```bash
# Watch for changes and recompile
forge build --watch
```

---

## Testing

### Run All Tests

```bash
# Run all tests
forge test

# Run with gas report
forge test --gas-report

# Run with detailed traces
forge test -vvv

# Run specific test file
forge test --match-path test/unit/GliskNFT.Minting.t.sol

# Run specific test function
forge test --match-test testBatchMint
```

### Coverage

```bash
# Generate coverage report
forge coverage

# Generate detailed coverage (requires lcov)
forge coverage --report lcov
genhtml -o coverage lcov.info
open coverage/index.html
```

### Fuzzing

```bash
# Run fuzz tests (automatically runs with forge test)
forge test

# Increase fuzz runs for thorough testing
forge test --fuzz-runs 10000
```

### Invariant Testing

```bash
# Run invariant tests
forge test --match-contract Invariant
```

---

## Deployment

### Testnet Deployment (Base Sepolia)

```bash
# 1. Ensure .env is configured with Base Sepolia RPC and private key

# 2. Check deployer balance
cast balance $DEPLOYER_ADDRESS --rpc-url $BASE_SEPOLIA_RPC_URL

# 3. Get testnet ETH from faucet if needed
# Visit: https://www.coinbase.com/faucets/base-ethereum-sepolia-faucet

# 4. Deploy contract
forge script script/Deploy.s.sol \
  --rpc-url base_sepolia \
  --broadcast \
  --verify \
  -vvvv

# 5. Save deployed address from output
# Example: Contract deployed to: 0x1234567890abcdef...
```

### Mainnet Deployment (Base)

**WARNING**: Double-check all parameters before mainnet deployment. Contracts are immutable.

```bash
# 1. Verify all configuration
echo "Placeholder URI: $PLACEHOLDER_URI"
echo "Initial Mint Price: $INITIAL_MINT_PRICE"
echo "Deployer: $(cast wallet address --private-key $PRIVATE_KEY)"

# 2. Simulate deployment (dry run)
forge script script/Deploy.s.sol \
  --rpc-url base_mainnet \
  -vvvv

# 3. Review simulation output carefully

# 4. Deploy to mainnet
forge script script/Deploy.s.sol \
  --rpc-url base_mainnet \
  --broadcast \
  --verify \
  -vvvv

# 5. Save deployment artifacts
# Artifacts saved in: broadcast/Deploy.s.sol/8453/run-latest.json
```

### Post-Deployment Checklist

- [ ] Contract verified on Basescan
- [ ] Test mint transaction on deployed contract
- [ ] Grant KEEPER_ROLE to backend service address
- [ ] Update frontend with contract address
- [ ] Test author claim flow
- [ ] Test treasury withdrawal
- [ ] Monitor initial transactions

---

## Contract Interaction

### Using Cast CLI

#### Read Operations

```bash
# Set contract address
export CONTRACT=0x1234567890abcdef...

# Get mint price
cast call $CONTRACT "mintPrice()(uint256)" --rpc-url base_mainnet

# Get treasury balance
cast call $CONTRACT "treasuryBalance()(uint256)" --rpc-url base_mainnet

# Get author claimable balance
cast call $CONTRACT "authorClaimable(address)(uint256)" 0xAUTHOR_ADDRESS --rpc-url base_mainnet

# Check if season ended
cast call $CONTRACT "seasonEnded()(bool)" --rpc-url base_mainnet

# Get token URI
cast call $CONTRACT "tokenURI(uint256)(string)" 1 --rpc-url base_mainnet

# Check if token is revealed
cast call $CONTRACT "isRevealed(uint256)(bool)" 1 --rpc-url base_mainnet

# Get prompt author for token
cast call $CONTRACT "tokenPromptAuthor(uint256)(address)" 1 --rpc-url base_mainnet
```

#### Write Operations

```bash
# Set private key
export PRIVATE_KEY=0x...

# Mint 1 NFT (send 0.000015 ETH)
cast send $CONTRACT \
  "mint(address,uint256)" \
  0xPROMPT_AUTHOR_ADDRESS \
  1 \
  --value 0.000015ether \
  --private-key $PRIVATE_KEY \
  --rpc-url base_mainnet

# Mint 5 NFTs (batch)
cast send $CONTRACT \
  "mint(address,uint256)" \
  0xPROMPT_AUTHOR_ADDRESS \
  5 \
  --value 0.000075ether \
  --private-key $PRIVATE_KEY \
  --rpc-url base_mainnet

# Claim author rewards
cast send $CONTRACT \
  "claimAuthorRewards()" \
  --private-key $PRIVATE_KEY \
  --rpc-url base_mainnet

# Owner: Withdraw treasury
cast send $CONTRACT \
  "withdrawTreasury()" \
  --private-key $OWNER_PRIVATE_KEY \
  --rpc-url base_mainnet

# Owner/Keeper: Update mint price
cast send $CONTRACT \
  "setMintPrice(uint256)" \
  20000000000000 \
  --private-key $PRIVATE_KEY \
  --rpc-url base_mainnet

# Owner/Keeper: Reveal tokens (example for 2 tokens)
cast send $CONTRACT \
  "revealTokens(uint256[],string[])" \
  "[1,2]" \
  "[\"ipfs://Qm.../1.json\",\"ipfs://Qm.../2.json\"]" \
  --private-key $PRIVATE_KEY \
  --rpc-url base_mainnet

# Owner: End season
cast send $CONTRACT \
  "endSeason()" \
  --private-key $OWNER_PRIVATE_KEY \
  --rpc-url base_mainnet

# Owner: Sweep unclaimed rewards (after 2 weeks)
cast send $CONTRACT \
  "sweepUnclaimedRewards(address[])" \
  "[0xAUTHOR1,0xAUTHOR2,0xAUTHOR3]" \
  --private-key $OWNER_PRIVATE_KEY \
  --rpc-url base_mainnet
```

### Using Ethers.js / Web3.js

```javascript
// Example with ethers.js
import { ethers } from 'ethers';
import GliskNFTABI from './abi/GliskNFT.json';

const provider = new ethers.JsonRpcProvider(process.env.BASE_MAINNET_RPC_URL);
const wallet = new ethers.Wallet(process.env.PRIVATE_KEY, provider);
const contract = new ethers.Contract(CONTRACT_ADDRESS, GliskNFTABI, wallet);

// Mint 1 NFT
const tx = await contract.mint(
  promptAuthorAddress,
  1,
  { value: ethers.parseEther("0.000015") }
);
await tx.wait();

// Claim rewards
const claimTx = await contract.claimAuthorRewards();
await claimTx.wait();

// Listen for events
contract.on("BatchMinted", (minter, promptAuthor, startTokenId, quantity, totalPaid) => {
  console.log(`Minted ${quantity} NFTs starting at ID ${startTokenId}`);
});
```

---

## Common Operations

### Minting NFTs

**User Flow:**
1. User selects prompt author
2. User specifies quantity (1-50)
3. User sends transaction with payment (price × quantity)
4. System mints NFTs and splits payment

**Example:**
```bash
# Mint 10 NFTs for prompt author 0xABC...
cast send $CONTRACT \
  "mint(address,uint256)" \
  0xABC... \
  10 \
  --value 0.00015ether \
  --rpc-url base_mainnet
```

### Revealing NFTs

**Backend Service Flow:**
1. Listen for `BatchMinted` events
2. Generate images off-chain
3. Upload to IPFS
4. Call `revealTokens()` with token IDs and URIs

**Example Script:**
```bash
# Reveal tokens 1-5
TOKEN_IDS="[1,2,3,4,5]"
URIS='["ipfs://Qm.../1.json","ipfs://Qm.../2.json","ipfs://Qm.../3.json","ipfs://Qm.../4.json","ipfs://Qm.../5.json"]'

cast send $CONTRACT \
  "revealTokens(uint256[],string[])" \
  "$TOKEN_IDS" \
  "$URIS" \
  --private-key $KEEPER_PRIVATE_KEY \
  --rpc-url base_mainnet
```

### Claiming Rewards

**Prompt Author Flow:**
1. Check claimable balance
2. Call `claimAuthorRewards()`
3. Receive ETH to wallet

**Example:**
```bash
# Check balance
BALANCE=$(cast call $CONTRACT "authorClaimable(address)(uint256)" $AUTHOR_ADDRESS --rpc-url base_mainnet)
echo "Claimable: $BALANCE wei"

# Claim
cast send $CONTRACT \
  "claimAuthorRewards()" \
  --private-key $AUTHOR_PRIVATE_KEY \
  --rpc-url base_mainnet
```

### Updating Mint Price

**Owner/Keeper Flow:**
1. Calculate new price based on ETH/USD rate
2. Call `setMintPrice(newPrice)`

**Example:**
```bash
# Update to 0.00002 ETH
NEW_PRICE=20000000000000  # 0.00002 ETH in wei

cast send $CONTRACT \
  "setMintPrice(uint256)" \
  $NEW_PRICE \
  --private-key $KEEPER_PRIVATE_KEY \
  --rpc-url base_mainnet
```

### Ending Season

**Owner Flow:**
1. Call `endSeason()` to stop minting and start countdown
2. Wait 14 days
3. Gather unclaimed author addresses (from off-chain indexer)
4. Call `sweepUnclaimedRewards(authors)` to sweep funds to treasury

**Example:**
```bash
# Step 1: End season
cast send $CONTRACT "endSeason()" --private-key $OWNER_PRIVATE_KEY --rpc-url base_mainnet

# Step 2: Wait 14 days

# Step 3: Check if claim period expired
SEASON_END=$(cast call $CONTRACT "seasonEndTime()(uint256)" --rpc-url base_mainnet)
CLAIM_PERIOD=$(cast call $CONTRACT "CLAIM_PERIOD()(uint256)" --rpc-url base_mainnet)
SWEEP_TIME=$((SEASON_END + CLAIM_PERIOD))
CURRENT_TIME=$(date +%s)

if [ $CURRENT_TIME -ge $SWEEP_TIME ]; then
  echo "Claim period expired, can sweep"
else
  echo "Claim period active, must wait"
fi

# Step 4: Sweep unclaimed rewards
AUTHORS='[0xAUTHOR1,0xAUTHOR2,...]'  # From off-chain indexer

cast send $CONTRACT \
  "sweepUnclaimedRewards(address[])" \
  "$AUTHORS" \
  --private-key $OWNER_PRIVATE_KEY \
  --rpc-url base_mainnet
```

---

## Troubleshooting

### Common Issues

#### Issue: "Insufficient Payment" Error

**Cause**: Sent value is less than `mintPrice * quantity`

**Solution**:
```bash
# Check current mint price
PRICE=$(cast call $CONTRACT "mintPrice()(uint256)" --rpc-url base_mainnet)
echo "Mint price: $PRICE wei"

# Calculate total for quantity
QUANTITY=5
TOTAL=$((PRICE * QUANTITY))
echo "Total required: $TOTAL wei"

# Send correct amount
cast send $CONTRACT "mint(address,uint256)" 0xAUTHOR $QUANTITY --value ${TOTAL}wei --rpc-url base_mainnet
```

#### Issue: "Season Ended" Error

**Cause**: Attempting to mint after `endSeason()` was called

**Solution**: Season end is permanent. Cannot resume minting. New season requires new contract deployment.

```bash
# Check if season ended
cast call $CONTRACT "seasonEnded()(bool)" --rpc-url base_mainnet
```

#### Issue: "Already Revealed" Error

**Cause**: Attempting to reveal a token that's already revealed

**Solution**: Check reveal status before revealing

```bash
# Check if token is revealed
cast call $CONTRACT "isRevealed(uint256)(bool)" 1 --rpc-url base_mainnet
```

#### Issue: Contract Verification Failed

**Cause**: Constructor arguments mismatch or compiler settings incorrect

**Solution**: Manually verify with constructor args

```bash
# Get constructor arguments from deployment
# From broadcast/Deploy.s.sol/8453/run-latest.json

# Manually verify
forge verify-contract \
  $CONTRACT_ADDRESS \
  src/GliskNFT.sol:GliskNFT \
  --chain base \
  --compiler-version 0.8.20 \
  --constructor-args $(cast abi-encode "constructor(string,string,string,uint256)" "GLISK Season 0" "GLISK0" "$PLACEHOLDER_URI" "$INITIAL_MINT_PRICE")
```

#### Issue: Gas Estimation Failed

**Cause**: Transaction will revert, or batch size too large

**Solution**:
```bash
# For batch mints, reduce quantity
# Check MAX_BATCH_SIZE
cast call $CONTRACT "MAX_BATCH_SIZE()(uint256)" --rpc-url base_mainnet

# For reverts, simulate transaction to see error
cast call $CONTRACT "mint(address,uint256)" 0xAUTHOR 1 --value 0.000015ether --rpc-url base_mainnet
```

### Debug Commands

```bash
# Check contract bytecode
cast code $CONTRACT --rpc-url base_mainnet

# Get transaction receipt
cast receipt 0xTRANSACTION_HASH --rpc-url base_mainnet

# Get transaction details
cast tx 0xTRANSACTION_HASH --rpc-url base_mainnet

# Decode calldata
cast 4byte-decode 0xCALLDATA

# Estimate gas
cast estimate $CONTRACT "mint(address,uint256)" 0xAUTHOR 1 --value 0.000015ether --rpc-url base_mainnet
```

### Getting Help

- **Foundry Docs**: https://book.getfoundry.sh/
- **OpenZeppelin Docs**: https://docs.openzeppelin.com/
- **Base Docs**: https://docs.base.org/
- **GitHub Issues**: [Your repo issues]
- **Discord**: [Your community Discord]

---

## Additional Resources

### ABI Export

```bash
# Export ABI for frontend integration
forge inspect GliskNFT abi > abi/GliskNFT.json
```

### Gas Optimization

```bash
# Profile gas usage
forge test --gas-report

# Optimize specific functions
forge test --match-test testBatchMint --gas-report
```

### Security Analysis

```bash
# Install Slither
pip install slither-analyzer

# Run static analysis
slither contracts/src/GliskNFT.sol
```

### Event Monitoring

```bash
# Listen for BatchMinted events
cast logs \
  --from-block latest \
  --address $CONTRACT \
  --signature "BatchMinted(address indexed,address indexed,uint256 indexed,uint256,uint256)" \
  --rpc-url base_mainnet
```

---

## Summary

This quickstart guide covers:
- ✅ Prerequisites and setup
- ✅ Local development workflow
- ✅ Comprehensive testing strategies
- ✅ Testnet and mainnet deployment
- ✅ Contract interaction via CLI and code
- ✅ Common operations (mint, reveal, claim, etc.)
- ✅ Troubleshooting and debugging

For implementation details, see:
- **research.md**: Technical decisions and patterns
- **data-model.md**: Contract state and entities
- **contracts/IGliskNFT.sol**: Complete interface specification

**Next Step**: Run `/speckit.tasks` to generate the implementation task list.
