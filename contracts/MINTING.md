# GliskNFT Minting Scripts

Convenience scripts for minting GLISK Season 0 NFTs on Base Sepolia to test the complete pipeline:
- Event Detection (webhook + recovery)
- Image Generation (Replicate API)
- IPFS Upload (Pinata)
- Batch Reveal (on-chain)

## Prerequisites

- Foundry installed (`curl -L https://foundry.paradigm.xyz | bash && foundryup`)
- `.env` file with `PRIVATE_KEY` configured
- Sufficient ETH balance on Base Sepolia for gas + mint cost

## Contract Details

- **Contract Address**: `0xb43185E67D4Fb27115AC419C9F8A335cC0B837B9`
- **Network**: Base Sepolia (Chain ID: 84532)
- **Prompt Author**: `0x892FEcA04c68B8aa0ab915e77123b08dDfA82d05`
- **Max Batch Size**: 50 tokens

## Quick Start

### Option 1: Bash Wrapper (Recommended)

```bash
cd contracts

# Mint 1 token (quick test)
./mint.sh 1

# Mint 10 tokens (pipeline test)
./mint.sh 10

# Mint 50 tokens (stress test)
./mint.sh 50

# Dry run (simulation only, no broadcast)
DRY_RUN=1 ./mint.sh 5
```

### Option 2: Direct Foundry Commands

```bash
cd contracts

# Mint 1 token
forge script script/Mint.s.sol:MintGliskNFT \
  --sig "mintSingle()" \
  --rpc-url base_sepolia \
  --broadcast

# Mint N tokens (batch)
forge script script/Mint.s.sol:MintGliskNFT \
  --sig "mintBatch(uint256)" 10 \
  --rpc-url base_sepolia \
  --broadcast

# Check contract state (no transaction)
forge script script/Mint.s.sol:MintGliskNFT \
  --sig "checkState()" \
  --rpc-url base_sepolia

# Estimate cost for N tokens
forge script script/Mint.s.sol:MintGliskNFT \
  --sig "estimateCost(uint256)" 10 \
  --rpc-url base_sepolia
```

## Available Functions

### Main Functions

- **`mintSingle()`** - Mint 1 token (convenience function)
- **`mintBatch(uint256 quantity)`** - Mint N tokens (1-50)

### Utility Functions

- **`checkState()`** - View contract state without minting
- **`estimateCost(uint256 quantity)`** - Calculate mint cost for N tokens

## Monitoring the Pipeline

After minting, monitor the full pipeline:

### 1. Event Detection

Check backend logs for webhook events:

```bash
cd backend
docker compose logs -f backend | grep "webhook"
```

### 2. Database Status

Query token status in database:

```bash
docker exec backend-postgres-1 psql -U glisk -d glisk -c \
  "SELECT token_id, status, generation_attempts FROM tokens_s0 ORDER BY token_id DESC LIMIT 10"
```

Token status progression:
- `detected` → `generating` → `uploading` → `ready` → `revealed`

### 3. Image Generation Worker

Monitor image generation:

```bash
tail -f backend/logs/glisk.log | grep "token.generation"
```

### 4. IPFS Upload Worker

Monitor IPFS uploads:

```bash
tail -f backend/logs/glisk.log | grep "ipfs"
```

### 5. Reveal Worker

Monitor batch reveals:

```bash
tail -f backend/logs/glisk.log | grep "reveal"
```

### 6. Blockchain Verification

Check revealed tokens on Basescan:

```
https://sepolia.basescan.org/address/0xb43185E67D4Fb27115AC419C9F8A335cC0B837B9
```

## Troubleshooting

### "Insufficient balance for minting"

Check minter wallet balance:

```bash
cast balance 0x892FEcA04c68B8aa0ab915e77123b08dDfA82d05 --rpc-url base_sepolia
```

Fund wallet if needed:
- Get testnet ETH from Base Sepolia faucet: https://www.coinbase.com/faucets/base-ethereum-sepolia-faucet

### "PRIVATE_KEY not found in .env"

Ensure `.env` file exists and contains:

```bash
PRIVATE_KEY=0xYourPrivateKeyHere...
```

### "Season has ended" / "MintingDisabled"

The season has been ended on-chain. Check contract state:

```bash
forge script script/Mint.s.sol:MintGliskNFT --sig "checkState()" --rpc-url base_sepolia
```

### Simulation works but broadcast fails

Common causes:
- Insufficient gas (increase gas price)
- Contract state changed (another transaction minted tokens)
- Network congestion (wait and retry)

Add verbosity for debugging:

```bash
forge script script/Mint.s.sol:MintGliskNFT \
  --sig "mintBatch(uint256)" 10 \
  --rpc-url base_sepolia \
  --broadcast \
  -vvvv
```

## Cost Examples

Based on current mint price (`0.0000444 ETH` per token):

| Quantity | Mint Cost | Estimated Gas | Total Cost (approx) |
|----------|-----------|---------------|---------------------|
| 1        | 0.0000444 ETH | ~0.0003 ETH | ~0.0003444 ETH |
| 10       | 0.000444 ETH | ~0.0004 ETH | ~0.0008444 ETH |
| 50       | 0.00222 ETH | ~0.001 ETH | ~0.00322 ETH |

Note: Gas costs vary based on network congestion.

## Script Architecture

### Mint.s.sol

- **Language**: Solidity ^0.8.20
- **Framework**: Foundry Script
- **Features**:
  - Automatic cost calculation from on-chain mint price
  - Detailed logging (pre/post mint state)
  - Built-in validation (quantity, balance)
  - Utility functions (checkState, estimateCost)

### mint.sh

- **Language**: Bash
- **Features**:
  - Color-coded output
  - Input validation
  - DRY_RUN mode
  - Help documentation
  - Post-mint monitoring instructions

## Next Steps

After successful minting:

1. **Verify event detection** - Check `mint_events` table for BatchMinted events
2. **Monitor workers** - Watch logs for image generation, IPFS upload, reveal
3. **Check token metadata** - Query tokenURI on-chain after reveal
4. **View images** - Access IPFS URLs via Pinata gateway

## Related Documentation

- Backend Event Detection: `specs/003-003b-event-detection/quickstart.md`
- Image Generation: `specs/003-003c-image-generation/quickstart.md`
- IPFS Upload & Reveal: `specs/003-003d-ipfs-reveal/quickstart.md`
- Smart Contract: `contracts/src/GliskNFT.sol`
