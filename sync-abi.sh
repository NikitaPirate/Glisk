#!/usr/bin/env bash
#
# Sync contract ABIs from Foundry build output to backend package
#
# This script:
# 1. Rebuilds Solidity contracts using Foundry (forge build)
# 2. Extracts ABI arrays from Foundry JSON output
# 3. Copies ABIs to backend/src/glisk/abi/ for runtime use
#
# Run this script after modifying smart contracts to ensure backend
# has the latest contract interface definitions.
#
# Usage:
#   ./sync-abi.sh

set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔨 Building contracts...${NC}"
cd contracts && forge build

echo -e "${BLUE}📋 Extracting ABI...${NC}"
python3 -c "
import json

# Load Foundry output (contains 'abi' key + bytecode)
with open('out/GliskNFT.sol/GliskNFT.json') as f:
    foundry_data = json.load(f)

# Extract just the ABI array
abi = foundry_data['abi']

# Write to backend package
with open('../backend/src/glisk/abi/GliskNFT.json', 'w') as f:
    json.dump(abi, f, indent=2)

# Write to frontend package (full contract JSON for viem)
with open('../frontend/src/lib/glisk-nft-abi.json', 'w') as f:
    json.dump({'abi': abi}, f, indent=2)

print(f'Extracted {len(abi)} ABI entries')
"

cd ..

echo -e "${GREEN}✅ ABI synced to:${NC}"
echo "  - backend/src/glisk/abi/GliskNFT.json (array format)"
echo "  - frontend/src/lib/glisk-nft-abi.json (object with 'abi' key)"
echo ""
echo "Next steps:"
echo "  - If backend is running in Docker: docker compose restart backend"
echo "  - If frontend dev server is running: it should hot-reload automatically"
echo "  - If running locally: restart your dev servers"
