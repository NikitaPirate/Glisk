// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../../src/GliskNFT.sol";

/**
 * @title GliskNFT Minting Tests
 * @notice Unit tests for batch minting functionality (User Story 1)
 * @dev Tests mint function with various scenarios including payment distribution
 */
contract GliskNFTMintingTest is Test {
    GliskNFT public nft;

    address public owner;
    address public user1;
    address public user2;
    address public promptAuthor1;
    address public promptAuthor2;

    string constant NAME = "GLISK Season 0";
    string constant SYMBOL = "GLISK0";
    string constant PLACEHOLDER_URI = "ipfs://placeholder";
    uint256 constant INITIAL_MINT_PRICE = 0.00001 ether;

    event BatchMinted(
        address indexed minter,
        address indexed promptAuthor,
        uint256 indexed startTokenId,
        uint256 quantity,
        uint256 totalPaid
    );

    function setUp() public {
        owner = address(this);
        user1 = makeAddr("user1");
        user2 = makeAddr("user2");
        promptAuthor1 = makeAddr("promptAuthor1");
        promptAuthor2 = makeAddr("promptAuthor2");

        // Deploy contract
        nft = new GliskNFT(NAME, SYMBOL, PLACEHOLDER_URI, INITIAL_MINT_PRICE);

        // Fund test users
        vm.deal(user1, 10 ether);
        vm.deal(user2, 10 ether);
    }

    /// @notice Test: Mint 1 NFT with exact payment, verify token ownership, author balance, treasury balance
    function testMintSingleNFT() public {
        uint256 quantity = 1;
        uint256 payment = INITIAL_MINT_PRICE * quantity;

        // Record balances before mint
        uint256 authorBalanceBefore = nft.authorClaimable(promptAuthor1);
        uint256 treasuryBalanceBefore = nft.treasuryBalance();
        uint256 totalSupplyBefore = nft.totalSupply();

        // Expect BatchMinted event
        vm.expectEmit(true, true, true, true);
        emit BatchMinted(user1, promptAuthor1, 1, quantity, payment);

        // User1 mints 1 NFT
        vm.prank(user1);
        nft.mint{value: payment}(promptAuthor1, quantity);

        // Verify token ownership
        assertEq(nft.ownerOf(1), user1, "User1 should own token 1");
        assertEq(nft.balanceOf(user1), 1, "User1 should have 1 token");

        // Verify total supply increased
        assertEq(nft.totalSupply(), totalSupplyBefore + quantity, "Total supply should increase by quantity");

        // Verify payment distribution (50/50 split)
        uint256 expectedAuthorShare = payment / 2;
        uint256 expectedTreasuryShare = payment - expectedAuthorShare;

        assertEq(
            nft.authorClaimable(promptAuthor1),
            authorBalanceBefore + expectedAuthorShare,
            "Author should receive 50% of payment"
        );
        assertEq(
            nft.treasuryBalance(),
            treasuryBalanceBefore + expectedTreasuryShare,
            "Treasury should receive 50% of payment"
        );

        // Verify prompt author association
        assertEq(nft.tokenPromptAuthor(1), promptAuthor1, "Token should be associated with promptAuthor1");
    }

    /// @notice Test: Mint 5 NFTs in batch, verify sequential token IDs, payment split
    function testMintBatchNFTs() public {
        uint256 quantity = 5;
        uint256 payment = INITIAL_MINT_PRICE * quantity;

        // Record balances before mint
        uint256 authorBalanceBefore = nft.authorClaimable(promptAuthor1);
        uint256 treasuryBalanceBefore = nft.treasuryBalance();
        uint256 totalSupplyBefore = nft.totalSupply();

        // Expect BatchMinted event with startTokenId = 1
        vm.expectEmit(true, true, true, true);
        emit BatchMinted(user1, promptAuthor1, 1, quantity, payment);

        // User1 mints 5 NFTs
        vm.prank(user1);
        nft.mint{value: payment}(promptAuthor1, quantity);

        // Verify sequential token IDs (1, 2, 3, 4, 5)
        for (uint256 i = 1; i <= quantity; i++) {
            assertEq(nft.ownerOf(i), user1, string.concat("User1 should own token ", vm.toString(i)));
            assertEq(nft.tokenPromptAuthor(i), promptAuthor1, "All tokens should be associated with promptAuthor1");
        }

        assertEq(nft.balanceOf(user1), quantity, "User1 should have 5 tokens");

        // Verify total supply increased
        assertEq(nft.totalSupply(), totalSupplyBefore + quantity, "Total supply should increase by quantity");

        // Verify payment distribution
        uint256 expectedAuthorShare = payment / 2;
        uint256 expectedTreasuryShare = payment - expectedAuthorShare;

        assertEq(
            nft.authorClaimable(promptAuthor1),
            authorBalanceBefore + expectedAuthorShare,
            "Author should receive 50% of payment"
        );
        assertEq(
            nft.treasuryBalance(),
            treasuryBalanceBefore + expectedTreasuryShare,
            "Treasury should receive 50% of payment"
        );
    }

    /// @notice Test: Mint with excess ETH, verify overpayment goes to treasury
    function testMintWithOverpayment() public {
        uint256 quantity = 1;
        uint256 requiredPayment = INITIAL_MINT_PRICE * quantity;
        uint256 overpayment = 0.001 ether;
        uint256 totalPayment = requiredPayment + overpayment;

        // Record balances before mint
        uint256 authorBalanceBefore = nft.authorClaimable(promptAuthor1);
        uint256 treasuryBalanceBefore = nft.treasuryBalance();

        // User1 mints with overpayment
        vm.prank(user1);
        nft.mint{value: totalPayment}(promptAuthor1, quantity);

        // Verify payment distribution
        // Author gets 50% of base price
        uint256 expectedAuthorShare = requiredPayment / 2;
        // Treasury gets remaining 50% of base price + all overpayment
        uint256 expectedTreasuryShare = (requiredPayment - expectedAuthorShare) + overpayment;

        assertEq(
            nft.authorClaimable(promptAuthor1),
            authorBalanceBefore + expectedAuthorShare,
            "Author should receive 50% of base payment only"
        );
        assertEq(
            nft.treasuryBalance(),
            treasuryBalanceBefore + expectedTreasuryShare,
            "Treasury should receive 50% of base + all overpayment"
        );
    }

    /// @notice Test: Mint with underpayment reverts
    function testMintRevertsInsufficientPayment() public {
        uint256 quantity = 1;
        uint256 requiredPayment = INITIAL_MINT_PRICE * quantity;
        uint256 insufficientPayment = requiredPayment - 1 wei;

        // Expect revert with InsufficientPayment error
        vm.expectRevert(GliskNFT.InsufficientPayment.selector);

        vm.prank(user1);
        nft.mint{value: insufficientPayment}(promptAuthor1, quantity);
    }

    /// @notice Test: Mint with quantity 0 reverts
    function testMintRevertsZeroQuantity() public {
        uint256 quantity = 0;

        // Expect revert with InvalidQuantity error
        vm.expectRevert(GliskNFT.InvalidQuantity.selector);

        vm.prank(user1);
        nft.mint{value: 0}(promptAuthor1, quantity);
    }

    /// @notice Test: Mint with quantity 51 reverts (exceeds MAX_BATCH_SIZE)
    function testMintRevertsExceedsMaxBatch() public {
        uint256 quantity = 51; // MAX_BATCH_SIZE is 50
        uint256 payment = INITIAL_MINT_PRICE * quantity;

        // Expect revert with ExceedsMaxBatchSize error
        vm.expectRevert(GliskNFT.ExceedsMaxBatchSize.selector);

        vm.prank(user1);
        nft.mint{value: payment}(promptAuthor1, quantity);
    }

    /// @notice Test: Multiple users mint simultaneously, verify no token ID collisions
    function testConcurrentMintsUniqueTokenIDs() public {
        uint256 quantity1 = 3;
        uint256 quantity2 = 2;
        uint256 payment1 = INITIAL_MINT_PRICE * quantity1;
        uint256 payment2 = INITIAL_MINT_PRICE * quantity2;

        // User1 mints 3 tokens (should get IDs 1, 2, 3)
        vm.prank(user1);
        nft.mint{value: payment1}(promptAuthor1, quantity1);

        // User2 mints 2 tokens (should get IDs 4, 5)
        vm.prank(user2);
        nft.mint{value: payment2}(promptAuthor2, quantity2);

        // Verify User1 owns tokens 1-3
        assertEq(nft.ownerOf(1), user1, "User1 should own token 1");
        assertEq(nft.ownerOf(2), user1, "User1 should own token 2");
        assertEq(nft.ownerOf(3), user1, "User1 should own token 3");
        assertEq(nft.balanceOf(user1), quantity1, "User1 should have 3 tokens");

        // Verify User2 owns tokens 4-5
        assertEq(nft.ownerOf(4), user2, "User2 should own token 4");
        assertEq(nft.ownerOf(5), user2, "User2 should own token 5");
        assertEq(nft.balanceOf(user2), quantity2, "User2 should have 2 tokens");

        // Verify no collisions - total 5 unique tokens
        uint256 totalSupply = nft.balanceOf(user1) + nft.balanceOf(user2);
        assertEq(totalSupply, quantity1 + quantity2, "Total supply should be 5");
    }

    /// @notice Test: Verify prompt author address is stored correctly for each token in batch
    function testPromptAuthorAssociation() public {
        uint256 quantity1 = 3;
        uint256 quantity2 = 2;
        uint256 payment1 = INITIAL_MINT_PRICE * quantity1;
        uint256 payment2 = INITIAL_MINT_PRICE * quantity2;

        // User1 mints 3 tokens with promptAuthor1
        vm.prank(user1);
        nft.mint{value: payment1}(promptAuthor1, quantity1);

        // User2 mints 2 tokens with promptAuthor2
        vm.prank(user2);
        nft.mint{value: payment2}(promptAuthor2, quantity2);

        // Verify all tokens from first batch have promptAuthor1
        for (uint256 i = 1; i <= quantity1; i++) {
            assertEq(
                nft.tokenPromptAuthor(i),
                promptAuthor1,
                string.concat("Token ", vm.toString(i), " should have promptAuthor1")
            );
        }

        // Verify all tokens from second batch have promptAuthor2
        for (uint256 i = quantity1 + 1; i <= quantity1 + quantity2; i++) {
            assertEq(
                nft.tokenPromptAuthor(i),
                promptAuthor2,
                string.concat("Token ", vm.toString(i), " should have promptAuthor2")
            );
        }

        // Verify author claimable balances
        uint256 expectedShare1 = payment1 / 2;
        uint256 expectedShare2 = payment2 / 2;

        assertEq(
            nft.authorClaimable(promptAuthor1), expectedShare1, "PromptAuthor1 should have correct claimable balance"
        );
        assertEq(
            nft.authorClaimable(promptAuthor2), expectedShare2, "PromptAuthor2 should have correct claimable balance"
        );
    }
}
