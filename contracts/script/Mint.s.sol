// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../src/GliskNFT.sol";

/**
 * @title GliskNFT Minting Script
 * @notice Foundry script for minting GLISK Season 0 NFTs on Base Sepolia
 * @dev Usage:
 *   Single mint:
 *     forge script script/Mint.s.sol:MintGliskNFT --sig "mintSingle()" --rpc-url base_sepolia --broadcast
 *
 *   Batch mint:
 *     forge script script/Mint.s.sol:MintGliskNFT --sig "mintBatch(uint256)" 10 --rpc-url base_sepolia --broadcast
 *
 *   Stress test (max batch):
 *     forge script script/Mint.s.sol:MintGliskNFT --sig "mintBatch(uint256)" 50 --rpc-url base_sepolia --broadcast
 */
contract MintGliskNFT is Script {
    // ============================================
    // CONSTANTS
    // ============================================

    /// @notice Deployed GliskNFT contract address on Base Sepolia
    address constant NFT_CONTRACT = 0xb43185E67D4Fb27115AC419C9F8A335cC0B837B9;

    /// @notice Prompt author address for minted tokens
    /// @dev This is the address that will receive 50% of mint proceeds
    address constant PROMPT_AUTHOR = 0x892FEcA04c68B8aa0ab915e77123b08dDfA82d05;

    /// @notice Maximum batch size allowed by contract
    uint256 constant MAX_BATCH_SIZE = 50;

    // ============================================
    // MAIN MINTING FUNCTIONS
    // ============================================

    /**
     * @notice Mint a single NFT for testing
     * @dev Convenience function for quick testing of the pipeline
     */
    function mintSingle() external {
        _mint(1);
    }

    /**
     * @notice Mint multiple NFTs in a single transaction
     * @dev Main function for batch minting to test the pipeline
     * @param quantity Number of NFTs to mint (1 to MAX_BATCH_SIZE)
     */
    function mintBatch(uint256 quantity) external {
        require(quantity > 0, "Quantity must be greater than 0");
        require(quantity <= MAX_BATCH_SIZE, "Quantity exceeds max batch size");

        _mint(quantity);
    }

    // ============================================
    // INTERNAL IMPLEMENTATION
    // ============================================

    /**
     * @notice Internal mint implementation
     * @dev Handles the actual minting logic with proper payment and logging
     * @param quantity Number of NFTs to mint
     */
    function _mint(uint256 quantity) internal {
        // Read private key from environment
        uint256 minterPrivateKey = vm.envUint("PRIVATE_KEY");
        address minterAddress = vm.addr(minterPrivateKey);

        // Get contract instance
        GliskNFT nft = GliskNFT(payable(NFT_CONTRACT));

        // Read current mint price from contract
        uint256 mintPrice = nft.mintPrice();
        uint256 totalCost = mintPrice * quantity;

        // Check minter balance
        uint256 minterBalance = minterAddress.balance;
        require(minterBalance >= totalCost, "Insufficient balance for minting");

        // Log pre-mint information
        console.log("");
        console.log("=== GliskNFT Minting ===");
        console.log("Network:", block.chainid);
        console.log("Contract:", NFT_CONTRACT);
        console.log("Minter:", minterAddress);
        console.log("Minter Balance:", minterBalance);
        console.log("Prompt Author:", PROMPT_AUTHOR);
        console.log("===");
        console.log("Quantity:", quantity);
        console.log("Mint Price (per NFT):", mintPrice);
        console.log("Total Cost:", totalCost);
        console.log("===");

        // Get current token ID before minting
        // Note: _nextTokenId is private, so we need to estimate based on events or use totalSupply
        // For simplicity, we'll log it after minting via events

        // Start broadcasting transactions
        vm.startBroadcast(minterPrivateKey);

        // Execute mint with payment
        uint256 gasBefore = gasleft();
        nft.mint{value: totalCost}(PROMPT_AUTHOR, quantity);
        uint256 gasUsed = gasBefore - gasleft();

        vm.stopBroadcast();

        // Log post-mint information
        console.log("");
        console.log("=== Mint Successful ===");
        console.log("Transaction Hash: (see broadcast logs)");
        console.log("Estimated Gas Used:", gasUsed);
        console.log("Block Number:", block.number);
        console.log("===");
        console.log("");
        console.log("Next Steps:");
        console.log("1. Check backend logs for event detection");
        console.log("2. Monitor image generation worker");
        console.log("3. Verify IPFS upload and reveal");
        console.log("4. Check token metadata on blockchain");
        console.log("");

        // Query contract state after mint
        _logContractState(nft, minterAddress);
    }

    /**
     * @notice Log current contract state for verification
     * @dev Helpful for debugging and monitoring the pipeline
     */
    function _logContractState(GliskNFT nft, address minterAddress) internal view {
        uint256 mintPrice = nft.mintPrice();
        uint256 treasuryBalance = nft.treasuryBalance();
        uint256 authorClaimable = nft.authorClaimable(PROMPT_AUTHOR);
        bool seasonEnded = nft.seasonEnded();

        console.log("=== Contract State ===");
        console.log("Mint Price:", mintPrice);
        console.log("Treasury Balance:", treasuryBalance);
        console.log("Author Claimable:", authorClaimable);
        console.log("Season Ended:", seasonEnded);
        console.log("Minter Balance After:", minterAddress.balance);
        console.log("===");
    }

    // ============================================
    // UTILITY FUNCTIONS
    // ============================================

    /**
     * @notice Check contract state without minting
     * @dev Useful for checking contract state before minting
     */
    function checkState() external view {
        GliskNFT nft = GliskNFT(payable(NFT_CONTRACT));

        console.log("");
        console.log("=== Contract State ===");
        console.log("Contract Address:", NFT_CONTRACT);
        console.log("Chain ID:", block.chainid);
        console.log("Mint Price:", nft.mintPrice());
        console.log("Treasury Balance:", nft.treasuryBalance());
        console.log("Author Claimable (", PROMPT_AUTHOR, "):", nft.authorClaimable(PROMPT_AUTHOR));
        console.log("Season Ended:", nft.seasonEnded());
        console.log("===");
        console.log("");
    }

    /**
     * @notice Estimate cost for minting N tokens
     * @dev Calculate total cost without executing mint
     * @param quantity Number of tokens to estimate
     */
    function estimateCost(uint256 quantity) external view {
        require(quantity > 0 && quantity <= MAX_BATCH_SIZE, "Invalid quantity");

        GliskNFT nft = GliskNFT(payable(NFT_CONTRACT));
        uint256 mintPrice = nft.mintPrice();
        uint256 totalCost = mintPrice * quantity;

        console.log("");
        console.log("=== Mint Cost Estimation ===");
        console.log("Quantity:", quantity);
        console.log("Mint Price (per NFT):", mintPrice);
        console.log("Total Cost:", totalCost);
        console.log("Total Cost (ETH):", totalCost / 1 ether, ".", (totalCost % 1 ether) / 1e14);
        console.log("===");
        console.log("");
    }
}
