// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../../src/GliskNFT.sol";

/**
 * @title GliskNFT Pricing Tests
 * @notice Unit tests for User Story 3: Dynamic Pricing Management
 * @dev Tests Owner and Keeper ability to update mint prices
 */
contract GliskNFTPricingTest is Test {
    GliskNFT public gliskNFT;

    address owner = address(1);
    address keeper = address(2);
    address user = address(3);
    address promptAuthor = address(4);

    string constant PLACEHOLDER_URI = "ipfs://placeholder";
    uint256 constant INITIAL_MINT_PRICE = 0.01 ether;

    event MintPriceUpdated(uint256 oldPrice, uint256 newPrice);

    function setUp() public {
        // Deploy contract as owner
        vm.startPrank(owner);
        gliskNFT = new GliskNFT("GLISK", "GLK", PLACEHOLDER_URI, INITIAL_MINT_PRICE);

        // Grant keeper role
        gliskNFT.grantRole(gliskNFT.KEEPER_ROLE(), keeper);
        vm.stopPrank();

        // Fund test accounts
        vm.deal(user, 10 ether);
    }

    /**
     * @notice T065: Owner updates price, subsequent mints use new price
     */
    function testOwnerUpdatesMintPrice() public {
        uint256 newPrice = 0.02 ether;

        // Owner updates mint price
        vm.prank(owner);
        vm.expectEmit(true, true, true, true);
        emit MintPriceUpdated(INITIAL_MINT_PRICE, newPrice);
        gliskNFT.setMintPrice(newPrice);

        // Verify price is updated
        assertEq(gliskNFT.mintPrice(), newPrice, "Mint price should be updated");

        // Subsequent mint uses new price
        vm.prank(user);
        gliskNFT.mint{value: newPrice}(promptAuthor, 1);

        // Verify mint succeeded
        assertEq(gliskNFT.ownerOf(1), user, "User should own token 1");
        assertEq(gliskNFT.balanceOf(user), 1, "User should have 1 token");
    }

    /**
     * @notice T066: Keeper updates price successfully
     */
    function testKeeperUpdatesMintPrice() public {
        uint256 newPrice = 0.03 ether;

        // Keeper updates mint price
        vm.prank(keeper);
        vm.expectEmit(true, true, true, true);
        emit MintPriceUpdated(INITIAL_MINT_PRICE, newPrice);
        gliskNFT.setMintPrice(newPrice);

        // Verify price is updated
        assertEq(gliskNFT.mintPrice(), newPrice, "Mint price should be updated by keeper");

        // Subsequent mint uses new price
        vm.prank(user);
        gliskNFT.mint{value: newPrice}(promptAuthor, 1);

        // Verify mint succeeded
        assertEq(gliskNFT.ownerOf(1), user, "User should own token 1");
    }

    /**
     * @notice T067: Non-owner/keeper cannot update price
     */
    function testUnauthorizedCannotUpdatePrice() public {
        uint256 newPrice = 0.05 ether;

        // Unauthorized user tries to update price
        vm.prank(user);
        vm.expectRevert();
        gliskNFT.setMintPrice(newPrice);

        // Verify price remains unchanged
        assertEq(gliskNFT.mintPrice(), INITIAL_MINT_PRICE, "Price should not change");
    }

    /**
     * @notice T068: Price update does not affect past mints
     */
    function testPriceUpdateDoesNotAffectPastMints() public {
        // User mints at initial price
        vm.prank(user);
        gliskNFT.mint{value: INITIAL_MINT_PRICE}(promptAuthor, 1);

        uint256 authorBalanceBefore = gliskNFT.authorClaimable(promptAuthor);
        uint256 treasuryBalanceBefore = gliskNFT.treasuryBalance();

        // Update price
        uint256 newPrice = 0.1 ether;
        vm.prank(owner);
        gliskNFT.setMintPrice(newPrice);

        // Verify old mint balances remain unchanged
        assertEq(
            gliskNFT.authorClaimable(promptAuthor),
            authorBalanceBefore,
            "Author balance from old mint should not change"
        );
        assertEq(gliskNFT.treasuryBalance(), treasuryBalanceBefore, "Treasury balance from old mint should not change");

        // New mint uses new price
        vm.deal(user, 10 ether);
        vm.prank(user);
        gliskNFT.mint{value: newPrice}(promptAuthor, 1);

        // Verify new mint split is based on new price
        uint256 expectedAuthorShare = newPrice / 2;
        uint256 expectedTreasuryShare = newPrice - expectedAuthorShare;

        assertEq(
            gliskNFT.authorClaimable(promptAuthor),
            authorBalanceBefore + expectedAuthorShare,
            "Author should receive 50% of new price"
        );
        assertEq(
            gliskNFT.treasuryBalance(),
            treasuryBalanceBefore + expectedTreasuryShare,
            "Treasury should receive 50% of new price"
        );
    }

    /**
     * @notice Additional test: Multiple price updates in sequence
     */
    function testMultiplePriceUpdates() public {
        uint256[] memory prices = new uint256[](3);
        prices[0] = 0.02 ether;
        prices[1] = 0.05 ether;
        prices[2] = 0.01 ether;

        for (uint256 i = 0; i < prices.length; i++) {
            uint256 oldPrice = gliskNFT.mintPrice();

            vm.prank(owner);
            vm.expectEmit(true, true, true, true);
            emit MintPriceUpdated(oldPrice, prices[i]);
            gliskNFT.setMintPrice(prices[i]);

            assertEq(gliskNFT.mintPrice(), prices[i], "Price should update correctly");
        }
    }

    /**
     * @notice Additional test: Zero price update (edge case)
     */
    function testZeroPriceUpdate() public {
        // Owner can set price to zero (free mints)
        vm.prank(owner);
        gliskNFT.setMintPrice(0);

        assertEq(gliskNFT.mintPrice(), 0, "Price should be zero");

        // User can mint for free
        vm.prank(user);
        gliskNFT.mint{value: 0}(promptAuthor, 1);

        assertEq(gliskNFT.ownerOf(1), user, "User should own token 1");
    }
}
