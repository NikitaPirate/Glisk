// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../../src/GliskNFT.sol";

/**
 * @title GliskNFT Royalty Tests
 * @notice Unit tests for User Story 7: Secondary Sales Royalties
 * @dev Tests ERC-2981 royalty configuration and queries
 */
contract GliskNFTRoyaltyTest is Test {
    GliskNFT public gliskNFT;

    address owner = address(1);
    address treasury = address(2);
    address user = address(3);
    address promptAuthor = address(4);

    string constant PLACEHOLDER_URI = "ipfs://placeholder";
    uint256 constant INITIAL_MINT_PRICE = 0.01 ether;
    uint96 constant DEFAULT_ROYALTY_BPS = 250; // 2.5% in basis points

    event RoyaltyUpdated(address receiver, uint96 feeNumerator);

    function setUp() public {
        // Deploy contract as owner
        vm.startPrank(owner);
        gliskNFT = new GliskNFT("GLISK", "GLK", PLACEHOLDER_URI, INITIAL_MINT_PRICE);
        vm.stopPrank();

        // Fund test accounts
        vm.deal(user, 10 ether);
    }

    /**
     * @notice T102: Query royaltyInfo() returns 2.5% and treasury address
     */
    function testDefaultRoyaltyInfo() public {
        // Mint a token
        vm.prank(user);
        gliskNFT.mint{value: INITIAL_MINT_PRICE}(promptAuthor, 1);

        // Query royalty info for various sale prices
        uint256 salePrice = 1 ether;
        (address receiver, uint256 royaltyAmount) = gliskNFT.royaltyInfo(1, salePrice);

        // Verify receiver is owner (set in constructor)
        assertEq(receiver, owner, "Royalty receiver should be deployer/owner");

        // Verify royalty amount is 2.5% (250 basis points)
        uint256 expectedRoyalty = (salePrice * DEFAULT_ROYALTY_BPS) / 10000;
        assertEq(royaltyAmount, expectedRoyalty, "Royalty should be 2.5% of sale price");
    }

    /**
     * @notice T103: Owner updates royalty percentage and receiver
     */
    function testOwnerUpdatesRoyalty() public {
        address newReceiver = treasury;
        uint96 newRoyaltyBPS = 500; // 5%

        // Owner updates royalty
        vm.prank(owner);
        vm.expectEmit(false, false, false, true);
        emit RoyaltyUpdated(newReceiver, newRoyaltyBPS);
        gliskNFT.setDefaultRoyalty(newReceiver, newRoyaltyBPS);

        // Mint a token
        vm.prank(user);
        gliskNFT.mint{value: INITIAL_MINT_PRICE}(promptAuthor, 1);

        // Query royalty info
        uint256 salePrice = 1 ether;
        (address receiver, uint256 royaltyAmount) = gliskNFT.royaltyInfo(1, salePrice);

        // Verify updated values
        assertEq(receiver, newReceiver, "Royalty receiver should be updated to treasury");
        uint256 expectedRoyalty = (salePrice * newRoyaltyBPS) / 10000;
        assertEq(royaltyAmount, expectedRoyalty, "Royalty should be 5% of sale price");
    }

    /**
     * @notice T104: Contract supports ERC2981 interface
     */
    function testSupportsERC2981Interface() public {
        // ERC2981 interface ID: 0x2a55205a
        bytes4 erc2981InterfaceId = 0x2a55205a;

        assertTrue(gliskNFT.supportsInterface(erc2981InterfaceId), "Contract should support ERC2981");
    }

    /**
     * @notice T105: Verify royalty amount calculation for various sale prices
     */
    function testRoyaltyCalculation() public {
        // Mint a token
        vm.prank(user);
        gliskNFT.mint{value: INITIAL_MINT_PRICE}(promptAuthor, 1);

        // Test various sale prices
        uint256[] memory salePrices = new uint256[](5);
        salePrices[0] = 0.1 ether;
        salePrices[1] = 1 ether;
        salePrices[2] = 10 ether;
        salePrices[3] = 100 ether;
        salePrices[4] = 0.0123 ether;

        for (uint256 i = 0; i < salePrices.length; i++) {
            uint256 salePrice = salePrices[i];
            (, uint256 royaltyAmount) = gliskNFT.royaltyInfo(1, salePrice);

            uint256 expectedRoyalty = (salePrice * DEFAULT_ROYALTY_BPS) / 10000;
            assertEq(
                royaltyAmount,
                expectedRoyalty,
                string(abi.encodePacked("Royalty calculation incorrect for sale price: ", vm.toString(salePrice)))
            );
        }
    }

    /**
     * @notice Additional test: Non-owner cannot update royalty
     */
    function testNonOwnerCannotUpdateRoyalty() public {
        address newReceiver = treasury;
        uint96 newRoyaltyBPS = 500;

        // User tries to update royalty
        vm.prank(user);
        vm.expectRevert();
        gliskNFT.setDefaultRoyalty(newReceiver, newRoyaltyBPS);
    }

    /**
     * @notice Additional test: Zero sale price returns zero royalty
     */
    function testZeroSalePriceReturnsZeroRoyalty() public {
        // Mint a token
        vm.prank(user);
        gliskNFT.mint{value: INITIAL_MINT_PRICE}(promptAuthor, 1);

        // Query royalty for zero sale price
        (, uint256 royaltyAmount) = gliskNFT.royaltyInfo(1, 0);

        assertEq(royaltyAmount, 0, "Royalty for zero sale price should be zero");
    }

    /**
     * @notice Additional test: Royalty works for non-existent tokens (ERC2981 behavior)
     */
    function testRoyaltyForNonExistentToken() public {
        // Query royalty for non-existent token
        uint256 salePrice = 1 ether;
        (address receiver, uint256 royaltyAmount) = gliskNFT.royaltyInfo(999, salePrice);

        // Should return default royalty even for non-existent token
        assertEq(receiver, owner, "Should return default receiver");
        uint256 expectedRoyalty = (salePrice * DEFAULT_ROYALTY_BPS) / 10000;
        assertEq(royaltyAmount, expectedRoyalty, "Should return default royalty amount");
    }

    /**
     * @notice Additional test: Update royalty to zero (disable royalties)
     */
    function testDisableRoyalties() public {
        // Owner sets royalty to zero
        vm.prank(owner);
        gliskNFT.setDefaultRoyalty(owner, 0);

        // Mint a token
        vm.prank(user);
        gliskNFT.mint{value: INITIAL_MINT_PRICE}(promptAuthor, 1);

        // Query royalty info
        uint256 salePrice = 1 ether;
        (, uint256 royaltyAmount) = gliskNFT.royaltyInfo(1, salePrice);

        assertEq(royaltyAmount, 0, "Royalty should be zero when disabled");
    }

    /**
     * @notice Additional test: Maximum royalty (100%)
     */
    function testMaximumRoyalty() public {
        // Owner sets royalty to 100% (10000 basis points)
        vm.prank(owner);
        gliskNFT.setDefaultRoyalty(owner, 10000);

        // Mint a token
        vm.prank(user);
        gliskNFT.mint{value: INITIAL_MINT_PRICE}(promptAuthor, 1);

        // Query royalty info
        uint256 salePrice = 1 ether;
        (, uint256 royaltyAmount) = gliskNFT.royaltyInfo(1, salePrice);

        assertEq(royaltyAmount, salePrice, "Royalty should be 100% of sale price");
    }
}
