#!/bin/bash
# =============================================================================
# GliskNFT Minting Script
# =============================================================================
# Convenience wrapper for minting GLISK Season 0 NFTs
#
# Usage:
#   ./mint.sh -t [quantity]       # Mint on Base Sepolia (testnet)
#   ./mint.sh -m [quantity]       # Mint on Base Mainnet
#
# Examples:
#   ./mint.sh -t                  # Mint 1 token on testnet
#   ./mint.sh -t 10               # Mint 10 tokens on testnet
#   ./mint.sh -m 1                # Mint 1 token on mainnet
#
# Requirements:
#   - Foundry (forge) installed
#   - .env file with PRIVATE_KEY configured
#   - Sufficient ETH balance on target network
#   - Contract deployed (reads address from deployments/)
#
# Environment Variables:
#   DRY_RUN         If set, run without broadcasting (simulation only)
# =============================================================================

set -e  # Exit on error

# =============================================================================
# Configuration
# =============================================================================

# Default values
DEFAULT_QUANTITY=1
MAX_BATCH_SIZE=50
SCRIPT_PATH="script/Mint.s.sol:MintGliskNFT"

# Network configurations (no associative arrays for macOS bash 3.2 compatibility)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# =============================================================================
# Helper Functions
# =============================================================================

print_header() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  GLISK Season 0 - NFT Minting Script${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo
}

print_error() {
    echo -e "${RED}ERROR: $1${NC}" >&2
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

show_usage() {
    echo "Usage: $0 -t|-m [quantity]"
    echo
    echo "Arguments:"
    echo "  -t              Mint on Base Sepolia (testnet)"
    echo "  -m              Mint on Base Mainnet"
    echo "  quantity        Number of NFTs to mint (1-$MAX_BATCH_SIZE, default: $DEFAULT_QUANTITY)"
    echo
    echo "Examples:"
    echo "  $0 -t           # Mint 1 token on testnet"
    echo "  $0 -t 10        # Mint 10 tokens on testnet"
    echo "  $0 -m 1         # Mint 1 token on mainnet"
    echo
    echo "Environment Variables:"
    echo "  DRY_RUN=1       Simulate without broadcasting"
    echo
    exit 1
}

# =============================================================================
# Validation
# =============================================================================

check_requirements() {
    # Check if forge is installed
    if ! command -v forge &> /dev/null; then
        print_error "Foundry (forge) is not installed"
        echo "Install from: https://getfoundry.sh"
        exit 1
    fi

    # Check if .env exists
    if [ ! -f .env ]; then
        print_error ".env file not found"
        echo "Create .env file with PRIVATE_KEY configuration"
        exit 1
    fi

    # Check if PRIVATE_KEY is set
    if ! grep -q "^PRIVATE_KEY=" .env; then
        print_error "PRIVATE_KEY not found in .env"
        exit 1
    fi
}

validate_quantity() {
    local quantity=$1

    # Check if quantity is a number
    if ! [[ "$quantity" =~ ^[0-9]+$ ]]; then
        print_error "Quantity must be a positive integer"
        show_usage
    fi

    # Check range
    if [ "$quantity" -lt 1 ] || [ "$quantity" -gt "$MAX_BATCH_SIZE" ]; then
        print_error "Quantity must be between 1 and $MAX_BATCH_SIZE"
        show_usage
    fi
}

# =============================================================================
# Network Configuration
# =============================================================================

get_deployment_address() {
    local deployment_file="$1"
    local deployment_path="deployments/$deployment_file"

    if [ ! -f "$deployment_path" ]; then
        print_error "Deployment file not found: $deployment_path"
        echo "Deploy the contract first or check the file path"
        exit 1
    fi

    # Extract contract address from deployment JSON
    local contract_address=$(python3 -c "
import json
with open('$deployment_path') as f:
    data = json.load(f)
    print(data['contractAddress'])
" 2>/dev/null)

    if [ -z "$contract_address" ]; then
        print_error "Failed to read contract address from $deployment_path"
        exit 1
    fi

    echo "$contract_address"
}

# =============================================================================
# Main Logic
# =============================================================================

main() {
    print_header

    # Parse network flag (required)
    local network=""
    local quantity=""

    if [ "$1" = "-t" ]; then
        network="testnet"
        quantity="${2:-$DEFAULT_QUANTITY}"
    elif [ "$1" = "-m" ]; then
        network="mainnet"
        quantity="${2:-$DEFAULT_QUANTITY}"
    elif [ "$1" = "-h" ] || [ "$1" = "--help" ] || [ -z "$1" ]; then
        show_usage
    else
        print_error "Invalid network flag: $1"
        show_usage
    fi

    # Validate
    check_requirements
    validate_quantity "$quantity"

    # Get network configuration (simple if/else instead of associative arrays)
    local rpc_url=""
    local deployment_file=""
    local network_name=""

    if [ "$network" = "testnet" ]; then
        rpc_url="base_sepolia"
        deployment_file="base-sepolia.json"
        network_name="Base Sepolia"
    else
        rpc_url="base"
        deployment_file="base-mainnet.json"
        network_name="Base Mainnet"
    fi

    # Read contract address from deployment file
    local contract_address=$(get_deployment_address "$deployment_file")

    print_info "Network: $network_name"
    print_info "Contract: $contract_address"

    # Determine function signature
    local function_sig
    if [ "$quantity" -eq 1 ]; then
        function_sig="mintSingle(address)"
        print_info "Minting 1 token (single mint)"
    else
        function_sig="mintBatch(address,uint256)"
        print_info "Minting $quantity tokens (batch mint)"
    fi

    # Build forge command
    local forge_cmd=(
        forge script "$SCRIPT_PATH"
        --sig "$function_sig"
        "$contract_address"
    )

    # Add quantity argument for batch mint
    if [ "$quantity" -ne 1 ]; then
        forge_cmd+=("$quantity")
    fi

    # Add RPC URL
    forge_cmd+=(--rpc-url "$rpc_url")

    # Add broadcast flag unless DRY_RUN is set
    if [ -z "$DRY_RUN" ]; then
        forge_cmd+=(--broadcast)
        print_info "Broadcasting transaction to $network_name"
    else
        print_warning "DRY RUN mode - transaction will NOT be broadcast"
    fi

    # Display command
    echo
    print_info "Executing: ${forge_cmd[*]}"
    echo

    # Execute minting
    if "${forge_cmd[@]}"; then
        echo
        print_success "Minting completed successfully!"
        echo
        print_info "Next steps:"
        echo "  1. Check backend logs for event detection"
        echo "     → cd backend && docker compose logs -f backend"
        echo "  2. Monitor token status in database"
        echo "     → docker exec backend-postgres-1 psql -U glisk -d glisk -c \"SELECT * FROM tokens_s0 ORDER BY token_id DESC LIMIT $quantity\""
        echo "  3. Watch image generation worker"
        echo "     → tail -f backend/logs/glisk.log | grep 'token.generation'"
        echo
    else
        echo
        print_error "Minting failed"
        echo "Check the error output above for details"
        exit 1
    fi
}

# =============================================================================
# Entry Point
# =============================================================================

main "$@"
