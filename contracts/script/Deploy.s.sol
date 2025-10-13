// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../src/GliskNFT.sol";

/**
 * @title GliskNFT Deployment Script
 * @notice Foundry script for deploying the GLISK Season 0 NFT contract
 * @dev Usage:
 *   Local: forge script script/Deploy.s.sol --rpc-url http://localhost:8545 --broadcast
 *   Testnet: forge script script/Deploy.s.sol --rpc-url base_sepolia --broadcast --verify
 *   Mainnet: forge script script/Deploy.s.sol --rpc-url base_mainnet --broadcast --verify
 */
contract DeployGliskNFT is Script {
    // Default values for local testing (can be overridden by environment variables)
    string constant DEFAULT_NAME = "GLISK Season 0";
    string constant DEFAULT_SYMBOL = "GLISK0";
    string constant DEFAULT_PLACEHOLDER_URI = "ipfs://QmPlaceholder";
    uint256 constant DEFAULT_INITIAL_MINT_PRICE = 0.001 ether;

    function run() external {
        // Read environment variables
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");

        // Read contract parameters with fallbacks to defaults
        string memory placeholderURI = vm.envOr("PLACEHOLDER_URI", DEFAULT_PLACEHOLDER_URI);
        uint256 initialMintPrice = vm.envOr("INITIAL_MINT_PRICE", DEFAULT_INITIAL_MINT_PRICE);
        string memory name = vm.envOr("NFT_NAME", DEFAULT_NAME);
        string memory symbol = vm.envOr("NFT_SYMBOL", DEFAULT_SYMBOL);

        // Log deployment parameters
        console.log("=== GliskNFT Deployment ===");
        console.log("Network:", block.chainid);
        console.log("Deployer:", vm.addr(deployerPrivateKey));
        console.log("Name:", name);
        console.log("Symbol:", symbol);
        console.log("Placeholder URI:", placeholderURI);
        console.log("Initial Mint Price:", initialMintPrice);
        console.log("===========================");

        // Start broadcasting transactions
        vm.startBroadcast(deployerPrivateKey);

        // Deploy GliskNFT contract
        GliskNFT nft = new GliskNFT(name, symbol, placeholderURI, initialMintPrice);

        vm.stopBroadcast();

        // Log deployment info
        console.log("");
        console.log("=== Deployment Successful ===");
        console.log("GliskNFT deployed to:", address(nft));
        console.log("Block number:", block.number);
        console.log("Gas price:", tx.gasprice);
        console.log("===========================");
        console.log("");
        console.log("Next steps:");
        console.log("1. Verify contract on block explorer");
        console.log("2. Grant KEEPER_ROLE to keeper address if needed");
        console.log("3. Update frontend configuration with contract address");
        console.log("4. Test minting functionality");
        console.log("");

        // Save deployment artifacts
        _saveDeploymentInfo(address(nft), name, symbol, placeholderURI, initialMintPrice);
    }

    /**
     * @notice Save deployment information to a JSON file
     * @dev Creates a deployment artifact in the deployments/ directory
     */
    function _saveDeploymentInfo(
        address contractAddress,
        string memory name,
        string memory symbol,
        string memory placeholderURI,
        uint256 initialMintPrice
    ) internal {
        // Build JSON in parts to avoid stack too deep
        string memory part1 = string(
            abi.encodePacked(
                "{\n",
                '  "contractAddress": "',
                vm.toString(contractAddress),
                '",\n',
                '  "chainId": ',
                vm.toString(block.chainid),
                ",\n",
                '  "blockNumber": ',
                vm.toString(block.number),
                ",\n"
            )
        );

        string memory part2 = string(
            abi.encodePacked(
                '  "deployer": "',
                vm.toString(msg.sender),
                '",\n',
                '  "name": "',
                name,
                '",\n',
                '  "symbol": "',
                symbol,
                '",\n'
            )
        );

        string memory part3 = string(
            abi.encodePacked(
                '  "placeholderURI": "',
                placeholderURI,
                '",\n',
                '  "initialMintPrice": "',
                vm.toString(initialMintPrice),
                '",\n',
                '  "timestamp": ',
                vm.toString(block.timestamp),
                "\n",
                "}"
            )
        );

        string memory json = string(abi.encodePacked(part1, part2, part3));

        // Determine filename based on chain ID
        string memory filename;
        if (block.chainid == 1) {
            filename = "deployments/mainnet.json";
        } else if (block.chainid == 8453) {
            filename = "deployments/base.json";
        } else if (block.chainid == 84532) {
            filename = "deployments/base-sepolia.json";
        } else if (block.chainid == 31337) {
            filename = "deployments/localhost.json";
        } else {
            filename = string(abi.encodePacked("deployments/chain-", vm.toString(block.chainid), ".json"));
        }

        // Write JSON to file
        vm.writeFile(filename, json);
        console.log("Deployment info saved to:", filename);
    }

    /**
     * @notice Helper function to grant keeper role (run separately after deployment)
     * @dev Usage: forge script script/Deploy.s.sol --sig "grantKeeperRole(address,address)" <nftAddress> <keeperAddress>
     */
    function grantKeeperRole(address nftAddress, address keeperAddress) external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");

        console.log("Granting KEEPER_ROLE to:", keeperAddress);
        console.log("On contract:", nftAddress);

        vm.startBroadcast(deployerPrivateKey);

        GliskNFT nft = GliskNFT(payable(nftAddress));
        bytes32 keeperRole = nft.KEEPER_ROLE();
        nft.grantRole(keeperRole, keeperAddress);

        vm.stopBroadcast();

        console.log("KEEPER_ROLE granted successfully");
    }

    /**
     * @notice Helper function to update mint price (run separately after deployment)
     * @dev Usage: forge script script/Deploy.s.sol --sig "updateMintPrice(address,uint256)" <nftAddress> <newPrice>
     */
    function updateMintPrice(address nftAddress, uint256 newPrice) external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");

        console.log("Updating mint price to:", newPrice);
        console.log("On contract:", nftAddress);

        vm.startBroadcast(deployerPrivateKey);

        GliskNFT nft = GliskNFT(payable(nftAddress));
        nft.setMintPrice(newPrice);

        vm.stopBroadcast();

        console.log("Mint price updated successfully");
    }
}
