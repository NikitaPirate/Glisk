#!/bin/bash
# =============================================================================
# GliskNFT Minting Script
# =============================================================================
# Convenience wrapper for minting GLISK Season 0 NFTs on Base Sepolia
#
# Usage:
#   ./mint.sh <quantity>          # Mint N tokens (1-50)
#   ./mint.sh                     # Mint 1 token (default)
#
# Examples:
#   ./mint.sh 1                   # Quick test (single token)
#   ./mint.sh 10                  # Batch mint (pipeline test)
#   ./mint.sh 50                  # Stress test (max batch size)
#
# Requirements:
#   - Foundry (forge) installed
#   - .env file with PRIVATE_KEY configured
#   - Sufficient ETH balance on Base Sepolia
#
# Environment Variables:
#   QUANTITY        Number of tokens to mint (default: 1)
#   RPC_URL         Base Sepolia RPC URL (default: base_sepolia from foundry.toml)
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
DEFAULT_RPC_URL="base_sepolia"

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
    echo "Usage: $0 [quantity]"
    echo
    echo "Arguments:"
    echo "  quantity        Number of NFTs to mint (1-$MAX_BATCH_SIZE, default: $DEFAULT_QUANTITY)"
    echo
    echo "Examples:"
    echo "  $0              # Mint 1 token (default)"
    echo "  $0 10           # Mint 10 tokens"
    echo "  $0 50           # Mint max batch (50 tokens)"
    echo
    echo "Environment Variables:"
    echo "  DRY_RUN=1       Simulate without broadcasting"
    echo "  RPC_URL=<url>   Override RPC URL"
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
# Main Logic
# =============================================================================

main() {
    print_header

    # Parse arguments
    local quantity="${1:-$DEFAULT_QUANTITY}"

    # Handle help flags
    if [ "$quantity" = "-h" ] || [ "$quantity" = "--help" ]; then
        show_usage
    fi

    # Validate
    check_requirements
    validate_quantity "$quantity"

    # Get RPC URL (from env or default)
    local rpc_url="${RPC_URL:-$DEFAULT_RPC_URL}"

    # Determine function signature
    local function_sig
    if [ "$quantity" -eq 1 ]; then
        function_sig="mintSingle()"
        print_info "Minting 1 token (single mint)"
    else
        function_sig="mintBatch(uint256)"
        print_info "Minting $quantity tokens (batch mint)"
    fi

    # Build forge command
    local forge_cmd=(
        forge script "$SCRIPT_PATH"
        --sig "$function_sig"
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
        print_info "Broadcasting transaction to $rpc_url"
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
