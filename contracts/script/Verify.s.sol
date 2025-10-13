// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";

/**
 * @title GliskNFT Verification Script
 * @notice Script to verify GliskNFT contract on block explorers
 * @dev Usage:
 *   Base Sepolia: forge verify-contract <address> GliskNFT --chain base-sepolia --constructor-args $(cast abi-encode "constructor(string,string,string,uint256)" "GLISK Season 0" "GLISK0" "ipfs://QmPlaceholder" 1000000000000000)
 *   Base Mainnet: forge verify-contract <address> GliskNFT --chain base --constructor-args $(cast abi-encode "constructor(string,string,string,uint256)" "GLISK Season 0" "GLISK0" "ipfs://QmActualHash" 1000000000000000)
 */
contract VerifyGliskNFT is Script {
    /**
     * @notice Generate constructor arguments for verification
     * @dev Run this to get the encoded constructor arguments
     */
    function getConstructorArgs() external view returns (bytes memory) {
        // Read parameters from environment or use defaults
        string memory name = vm.envOr("NFT_NAME", string("GLISK Season 0"));
        string memory symbol = vm.envOr("NFT_SYMBOL", string("GLISK0"));
        string memory placeholderURI = vm.envOr("PLACEHOLDER_URI", string("ipfs://QmPlaceholder"));
        uint256 initialMintPrice = vm.envOr("INITIAL_MINT_PRICE", uint256(0.001 ether));

        // Encode constructor arguments
        bytes memory constructorArgs = abi.encode(name, symbol, placeholderURI, initialMintPrice);

        console.log("=== Constructor Arguments ===");
        console.log("Name:", name);
        console.log("Symbol:", symbol);
        console.log("Placeholder URI:", placeholderURI);
        console.log("Initial Mint Price:", initialMintPrice);
        console.log("===========================");
        console.logBytes(constructorArgs);

        return constructorArgs;
    }

    /**
     * @notice Verify contract on Basescan
     * @param contractAddress The deployed contract address
     * @dev This function demonstrates verification but requires forge verify-contract CLI
     */
    function verifyOnBasescan(address contractAddress) external {
        string memory name = vm.envOr("NFT_NAME", string("GLISK Season 0"));
        string memory symbol = vm.envOr("NFT_SYMBOL", string("GLISK0"));
        string memory placeholderURI = vm.envOr("PLACEHOLDER_URI", string("ipfs://QmPlaceholder"));
        uint256 initialMintPrice = vm.envOr("INITIAL_MINT_PRICE", uint256(0.001 ether));

        console.log("=== Verification Instructions ===");
        console.log("Contract Address:", contractAddress);
        console.log("Chain ID:", block.chainid);
        console.log("");
        console.log("Run the following command:");
        console.log("");

        // Determine chain name
        string memory chainName;
        if (block.chainid == 8453) {
            chainName = "base";
        } else if (block.chainid == 84532) {
            chainName = "base-sepolia";
        } else {
            chainName = string(abi.encodePacked("chain-", vm.toString(block.chainid)));
        }

        // Print verification command
        console.log(
            string(
                abi.encodePacked(
                    "forge verify-contract ",
                    vm.toString(contractAddress),
                    " GliskNFT --chain ",
                    chainName,
                    " --constructor-args $(cast abi-encode \"constructor(string,string,string,uint256)\" \"",
                    name,
                    "\" \"",
                    symbol,
                    "\" \"",
                    placeholderURI,
                    "\" ",
                    vm.toString(initialMintPrice),
                    ")"
                )
            )
        );
        console.log("");
        console.log("===========================");
    }

    /**
     * @notice Helper to verify contract with retry logic
     * @dev Attempts verification multiple times if it fails
     */
    function verifyWithRetry(address contractAddress, uint256 maxRetries) external {
        console.log("=== Verification with Retry ===");
        console.log("Contract:", contractAddress);
        console.log("Max retries:", maxRetries);
        console.log("");

        for (uint256 i = 0; i < maxRetries; i++) {
            console.log("Attempt", i + 1, "of", maxRetries);

            // In practice, you would call the verification API here
            // For now, just print instructions
            this.verifyOnBasescan(contractAddress);

            console.log("");
            console.log("If verification failed, waiting 30 seconds before retry...");
            console.log("(In production, add actual verification API call here)");
            console.log("");
        }
    }

    /**
     * @notice Check if contract is already verified
     * @param contractAddress The contract address to check
     * @return True if verified, false otherwise
     */
    function isVerified(address contractAddress) external view returns (bool) {
        // Check if contract has code
        bytes memory code = contractAddress.code;
        if (code.length == 0) {
            console.log("Contract has no code at:", contractAddress);
            return false;
        }

        console.log("Contract has code (", code.length, "bytes )");
        console.log("Manual verification required on block explorer");

        // Note: Actual verification status check requires API call to block explorer
        return false;
    }

    /**
     * @notice Print verification instructions for multiple networks
     */
    function printVerificationGuide() external pure {
        console.log("=== GliskNFT Verification Guide ===");
        console.log("");
        console.log("1. BASE SEPOLIA (Testnet)");
        console.log("   Command:");
        console.log("   forge verify-contract <ADDRESS> GliskNFT \\");
        console.log("     --chain base-sepolia \\");
        console.log("     --constructor-args $(cast abi-encode \\");
        console.log("       \"constructor(string,string,string,uint256)\" \\");
        console.log("       \"GLISK Season 0\" \\");
        console.log("       \"GLISK0\" \\");
        console.log("       \"ipfs://QmPlaceholder\" \\");
        console.log("       1000000000000000)");
        console.log("");
        console.log("2. BASE MAINNET");
        console.log("   Command:");
        console.log("   forge verify-contract <ADDRESS> GliskNFT \\");
        console.log("     --chain base \\");
        console.log("     --constructor-args $(cast abi-encode \\");
        console.log("       \"constructor(string,string,string,uint256)\" \\");
        console.log("       \"GLISK Season 0\" \\");
        console.log("       \"GLISK0\" \\");
        console.log("       \"ipfs://QmActualPlaceholderHash\" \\");
        console.log("       1000000000000000)");
        console.log("");
        console.log("3. VERIFY USING ETHERSCAN API");
        console.log("   Set ETHERSCAN_API_KEY in .env");
        console.log("   Then run verification command");
        console.log("");
        console.log("===========================");
    }
}
