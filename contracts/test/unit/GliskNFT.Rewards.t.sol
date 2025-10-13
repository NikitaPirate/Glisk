// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../../src/GliskNFT.sol";

/**
 * @title GliskNFT Rewards Tests
 * @notice Unit tests for User Story 2: Prompt Author Earnings and Claims
 * @dev Tests the reward accumulation and claiming system for prompt authors
 */
contract GliskNFTRewardsTest is Test {
    GliskNFT public nft;

    address public owner;
    address public author1;
    address public author2;
    address public minter1;
    address public minter2;

    string constant PLACEHOLDER_URI = "ipfs://placeholder";
    uint256 constant INITIAL_PRICE = 0.01 ether;

    event AuthorClaimed(address indexed author, uint256 amount);

    function setUp() public {
        owner = makeAddr("owner");
        author1 = makeAddr("author1");
        author2 = makeAddr("author2");
        minter1 = makeAddr("minter1");
        minter2 = makeAddr("minter2");

        vm.prank(owner);
        nft = new GliskNFT("GLISK Season 0", "GLISK0", PLACEHOLDER_URI, INITIAL_PRICE);

        // Fund test accounts
        vm.deal(minter1, 100 ether);
        vm.deal(minter2, 100 ether);
    }

    /**
     * @notice Test that author claimable balance is 50% of mint payment
     * @dev T029: Verify author claimable balance is 50% of mint payment
     */
    function testAuthorBalanceAfterMint() public {
        uint256 quantity = 5;
        uint256 totalPayment = INITIAL_PRICE * quantity;
        uint256 expectedAuthorShare = totalPayment / 2;

        // Mint NFTs from author1's prompts
        vm.prank(minter1);
        nft.mint{value: totalPayment}(author1, quantity);

        // Check author's claimable balance
        uint256 authorBalance = nft.authorClaimable(author1);
        assertEq(authorBalance, expectedAuthorShare, "Author balance should be 50% of payment");
    }

    /**
     * @notice Test that author can claim rewards and balance resets to zero
     * @dev T030: Author claims rewards, balance transfers and resets to zero
     */
    function testClaimAuthorRewards() public {
        uint256 quantity = 10;
        uint256 totalPayment = INITIAL_PRICE * quantity;
        uint256 expectedAuthorShare = totalPayment / 2;

        // Mint NFTs
        vm.prank(minter1);
        nft.mint{value: totalPayment}(author1, quantity);

        // Record initial balances
        uint256 authorBalanceBefore = author1.balance;
        uint256 claimableBalanceBefore = nft.authorClaimable(author1);
        assertEq(claimableBalanceBefore, expectedAuthorShare, "Initial claimable balance incorrect");

        // Author claims rewards
        vm.expectEmit(true, true, true, true);
        emit AuthorClaimed(author1, expectedAuthorShare);

        vm.prank(author1);
        nft.claimAuthorRewards();

        // Verify balance transferred
        uint256 authorBalanceAfter = author1.balance;
        assertEq(authorBalanceAfter, authorBalanceBefore + expectedAuthorShare, "Author did not receive payment");

        // Verify claimable balance reset to zero
        uint256 claimableBalanceAfter = nft.authorClaimable(author1);
        assertEq(claimableBalanceAfter, 0, "Claimable balance should be zero after claim");
    }

    /**
     * @notice Test that claim with zero balance succeeds without revert
     * @dev T031: Claim with zero balance succeeds without revert
     */
    function testClaimWithZeroBalance() public {
        // Verify author has zero balance
        uint256 claimableBalance = nft.authorClaimable(author1);
        assertEq(claimableBalance, 0, "Author should have zero balance initially");

        // Claim should succeed without revert
        vm.prank(author1);
        nft.claimAuthorRewards();

        // Verify balance still zero
        uint256 claimableBalanceAfter = nft.authorClaimable(author1);
        assertEq(claimableBalanceAfter, 0, "Claimable balance should still be zero");
    }

    /**
     * @notice Test that multiple mints to same author accumulate correctly
     * @dev T032: Multiple mints to same author accumulate correctly
     */
    function testMultipleMintsAccumulate() public {
        uint256 quantity1 = 3;
        uint256 quantity2 = 7;
        uint256 payment1 = INITIAL_PRICE * quantity1;
        uint256 payment2 = INITIAL_PRICE * quantity2;

        // First mint
        vm.prank(minter1);
        nft.mint{value: payment1}(author1, quantity1);

        uint256 balanceAfterFirstMint = nft.authorClaimable(author1);
        assertEq(balanceAfterFirstMint, payment1 / 2, "Balance after first mint incorrect");

        // Second mint from different minter
        vm.prank(minter2);
        nft.mint{value: payment2}(author1, quantity2);

        // Check accumulated balance
        uint256 expectedTotal = (payment1 + payment2) / 2;
        uint256 balanceAfterSecondMint = nft.authorClaimable(author1);
        assertEq(balanceAfterSecondMint, expectedTotal, "Accumulated balance incorrect");

        // Claim all accumulated rewards
        uint256 authorBalanceBefore = author1.balance;
        vm.prank(author1);
        nft.claimAuthorRewards();

        uint256 authorBalanceAfter = author1.balance;
        assertEq(authorBalanceAfter, authorBalanceBefore + expectedTotal, "Did not receive full accumulated amount");
        assertEq(nft.authorClaimable(author1), 0, "Balance should be zero after claim");
    }

    /**
     * @notice Test handling of transfer failure (contract that rejects ETH)
     * @dev T033: Handle transfer failure gracefully (test with contract that rejects ETH)
     */
    function testClaimTransferFails() public {
        // Deploy a contract that rejects ETH
        RejectingContract rejectingAuthor = new RejectingContract();
        address authorAddress = address(rejectingAuthor);

        uint256 quantity = 5;
        uint256 totalPayment = INITIAL_PRICE * quantity;

        // Mint NFTs for rejecting contract
        vm.prank(minter1);
        nft.mint{value: totalPayment}(authorAddress, quantity);

        // Verify balance accumulated
        uint256 claimableBalance = nft.authorClaimable(authorAddress);
        assertGt(claimableBalance, 0, "Author should have claimable balance");

        // Attempt to claim should fail
        vm.prank(authorAddress);
        vm.expectRevert(GliskNFT.TransferFailed.selector);
        nft.claimAuthorRewards();

        // Verify balance was NOT reset (failed transfers don't modify state)
        uint256 claimableBalanceAfter = nft.authorClaimable(authorAddress);
        assertEq(claimableBalanceAfter, claimableBalance, "Balance should not change on failed transfer");
    }

    /**
     * @notice Test multiple authors can independently claim rewards
     */
    function testMultipleAuthorsIndependentClaims() public {
        uint256 quantity1 = 3;
        uint256 quantity2 = 5;
        uint256 payment1 = INITIAL_PRICE * quantity1;
        uint256 payment2 = INITIAL_PRICE * quantity2;

        // Mint from author1's prompts
        vm.prank(minter1);
        nft.mint{value: payment1}(author1, quantity1);

        // Mint from author2's prompts
        vm.prank(minter2);
        nft.mint{value: payment2}(author2, quantity2);

        // Check both authors have correct balances
        assertEq(nft.authorClaimable(author1), payment1 / 2, "Author1 balance incorrect");
        assertEq(nft.authorClaimable(author2), payment2 / 2, "Author2 balance incorrect");

        // Author1 claims
        uint256 author1BalanceBefore = author1.balance;
        vm.prank(author1);
        nft.claimAuthorRewards();

        // Verify author1 received payment and balance reset
        assertEq(author1.balance, author1BalanceBefore + payment1 / 2, "Author1 did not receive payment");
        assertEq(nft.authorClaimable(author1), 0, "Author1 balance should be zero");

        // Verify author2 balance unchanged
        assertEq(nft.authorClaimable(author2), payment2 / 2, "Author2 balance should be unchanged");

        // Author2 claims
        uint256 author2BalanceBefore = author2.balance;
        vm.prank(author2);
        nft.claimAuthorRewards();

        // Verify author2 received payment and balance reset
        assertEq(author2.balance, author2BalanceBefore + payment2 / 2, "Author2 did not receive payment");
        assertEq(nft.authorClaimable(author2), 0, "Author2 balance should be zero");
    }

    /**
     * @notice Test reentrancy protection on claimAuthorRewards
     */
    function testClaimReentrancyProtection() public {
        // Deploy attacking contract
        ReentrancyAttacker attacker = new ReentrancyAttacker(payable(address(nft)));
        address attackerAddress = address(attacker);

        uint256 quantity = 5;
        uint256 totalPayment = INITIAL_PRICE * quantity;

        // Mint NFTs for attacker
        vm.prank(minter1);
        nft.mint{value: totalPayment}(attackerAddress, quantity);

        // Attempt reentrancy attack
        vm.prank(attackerAddress);
        vm.expectRevert(); // Should revert due to ReentrancyGuard
        attacker.attack();
    }

    /**
     * @notice Test claim after season has ended
     * @dev TODO: Enable this test in Phase 9 when endSeason() is implemented
     */
    // function testClaimAfterSeasonEnd() public {
    //     uint256 quantity = 5;
    //     uint256 totalPayment = INITIAL_PRICE * quantity;
    //     uint256 expectedAuthorShare = totalPayment / 2;

    //     // Mint NFTs
    //     vm.prank(minter1);
    //     nft.mint{value: totalPayment}(author1, quantity);

    //     // End season
    //     vm.prank(owner);
    //     nft.endSeason();

    //     // Author should still be able to claim
    //     vm.prank(author1);
    //     nft.claimAuthorRewards();

    //     // Verify claim succeeded
    //     assertEq(nft.authorClaimable(author1), 0, "Balance should be zero after claim");
    //     assertEq(author1.balance, expectedAuthorShare, "Author did not receive payment");
    // }
}

/**
 * @title RejectingContract
 * @notice Helper contract that rejects ETH transfers
 */
contract RejectingContract {
// No receive() or fallback() - will reject ETH
}

/**
 * @title ReentrancyAttacker
 * @notice Helper contract to test reentrancy protection
 */
contract ReentrancyAttacker {
    GliskNFT public nft;
    uint256 public attackCount;

    constructor(address payable _nft) {
        nft = GliskNFT(_nft);
    }

    function attack() external {
        nft.claimAuthorRewards();
    }

    receive() external payable {
        // Attempt to re-enter claim function
        if (attackCount < 2) {
            attackCount++;
            nft.claimAuthorRewards();
        }
    }
}
