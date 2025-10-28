#!/bin/bash
# =============================================================================
# GliskNFT Price Update Script
# =============================================================================
# Convenience wrapper for updating GLISK Season 0 mint price
#
# Usage:
#   ./set-price.sh -t       # Update price on Base Sepolia (testnet)
#   ./set-price.sh -m       # Update price on Base Mainnet
#
# The script reads the mint price from .env (INITIAL_MINT_PRICE) and updates
# the on-chain contract to match.
#
# Requirements:
#   - Foundry (forge) installed
#   - .env file with PRIVATE_KEY and INITIAL_MINT_PRICE configured
#   - Sufficient ETH balance for gas
#   - Contract deployed (reads address from deployments/)
#   - Deployer/Owner access (DEFAULT_ADMIN_ROLE or KEEPER_ROLE)
#
# Environment Variables:
#   DRY_RUN         If set, run without broadcasting (simulation only)
# =============================================================================

set -e  # Exit on error

# =============================================================================
# Configuration
# =============================================================================

SCRIPT_PATH="script/Deploy.s.sol:DeployGliskNFT"

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
    echo -e "${BLUE}  GLISK Season 0 - Mint Price Update Script${NC}"
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
    echo "Usage: $0 -t|-m"
    echo
    echo "Arguments:"
    echo "  -t              Update price on Base Sepolia (testnet)"
    echo "  -m              Update price on Base Mainnet"
    echo
    echo "Examples:"
    echo "  $0 -t           # Update price on testnet"
    echo "  $0 -m           # Update price on mainnet"
    echo
    echo "Environment Variables:"
    echo "  DRY_RUN=1       Simulate without broadcasting"
    echo
    echo "Configuration:"
    echo "  Edit INITIAL_MINT_PRICE in .env to set the new price"
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
        echo "Create .env file with PRIVATE_KEY and INITIAL_MINT_PRICE configuration"
        exit 1
    fi

    # Check if PRIVATE_KEY is set
    if ! grep -q "^PRIVATE_KEY=" .env; then
        print_error "PRIVATE_KEY not found in .env"
        exit 1
    fi

    # Check if INITIAL_MINT_PRICE is set
    if ! grep -q "^INITIAL_MINT_PRICE=" .env; then
        print_error "INITIAL_MINT_PRICE not found in .env"
        echo "Add INITIAL_MINT_PRICE=<wei_amount> to .env"
        exit 1
    fi
}

read_mint_price() {
    local mint_price=$(grep "^INITIAL_MINT_PRICE=" .env | cut -d '=' -f2)

    if [ -z "$mint_price" ]; then
        print_error "Failed to read INITIAL_MINT_PRICE from .env"
        exit 1
    fi

    # Validate that it's a number
    if ! [[ "$mint_price" =~ ^[0-9]+$ ]]; then
        print_error "INITIAL_MINT_PRICE must be a positive integer (wei)"
        exit 1
    fi

    echo "$mint_price"
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

    if [ "$1" = "-t" ]; then
        network="testnet"
    elif [ "$1" = "-m" ]; then
        network="mainnet"
    elif [ "$1" = "-h" ] || [ "$1" = "--help" ] || [ -z "$1" ]; then
        show_usage
    else
        print_error "Invalid network flag: $1"
        show_usage
    fi

    # Validate
    check_requirements

    # Read new mint price from .env
    local new_price=$(read_mint_price)

    # Get network configuration
    local rpc_url=""
    local deployment_file=""
    local network_name=""

    if [ "$network" = "testnet" ]; then
        rpc_url="base_sepolia"
        deployment_file="base-sepolia.json"
        network_name="Base Sepolia"
    else
        rpc_url="base_mainnet"
        deployment_file="base.json"
        network_name="Base Mainnet"
    fi

    # Read contract address from deployment file
    local contract_address=$(get_deployment_address "$deployment_file")

    print_info "Network: $network_name"
    print_info "Contract: $contract_address"
    print_info "New Price: $new_price wei ($(python3 -c "print(f'{$new_price / 1e18:.6f}')") ETH)"

    # Build forge command
    local forge_cmd=(
        forge script "$SCRIPT_PATH"
        --sig "updateMintPrice(address,uint256)"
        "$contract_address"
        "$new_price"
        --rpc-url "$rpc_url"
    )

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

    # Execute price update
    if "${forge_cmd[@]}"; then
        echo
        print_success "Mint price updated successfully!"
        echo
        print_info "Verification:"
        echo "  Check on-chain price:"
        echo "    → cast call $contract_address \"mintPrice()\" --rpc-url $rpc_url"
        echo
        echo "  View transaction on Basescan:"
        if [ "$network" = "testnet" ]; then
            echo "    → https://sepolia.basescan.org/address/$contract_address"
        else
            echo "    → https://basescan.org/address/$contract_address"
        fi
        echo
    else
        echo
        print_error "Price update failed"
        echo "Check the error output above for details"
        exit 1
    fi
}

# =============================================================================
# Entry Point
# =============================================================================

main "$@"
