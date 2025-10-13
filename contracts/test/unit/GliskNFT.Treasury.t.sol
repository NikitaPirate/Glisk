// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../../src/GliskNFT.sol";

/**
 * @title GliskNFT Treasury Tests
 * @notice Unit tests for User Story 5: Treasury Management
 * @dev Tests the treasury accumulation and withdrawal system
 */
contract GliskNFTTreasuryTest is Test {
    GliskNFT public nft;

    address public owner;
    address public author;
    address public minter1;
    address public minter2;
    address public unauthorized;

    string constant PLACEHOLDER_URI = "ipfs://placeholder";
    uint256 constant INITIAL_PRICE = 0.01 ether;

    event TreasuryWithdrawn(address indexed recipient, uint256 amount);
    event DirectPaymentReceived(address indexed sender, uint256 amount);

    function setUp() public {
        owner = makeAddr("owner");
        author = makeAddr("author");
        minter1 = makeAddr("minter1");
        minter2 = makeAddr("minter2");
        unauthorized = makeAddr("unauthorized");

        vm.prank(owner);
        nft = new GliskNFT("GLISK Season 0", "GLISK0", PLACEHOLDER_URI, INITIAL_PRICE);

        // Fund test accounts
        vm.deal(minter1, 100 ether);
        vm.deal(minter2, 100 ether);
        vm.deal(unauthorized, 100 ether);
    }

    /**
     * @notice Test that treasury balance increases by 50% per mint
     * @dev T054: Treasury balance increases by 50% per mint
     */
    function testTreasuryAccumulatesFromMints() public {
        uint256 quantity = 5;
        uint256 totalPayment = INITIAL_PRICE * quantity;
        uint256 expectedTreasuryShare = totalPayment / 2;

        // Initial treasury balance should be zero
        assertEq(nft.treasuryBalance(), 0, "Initial treasury should be zero");

        // Mint NFTs
        vm.prank(minter1);
        nft.mint{value: totalPayment}(author, quantity);

        // Check treasury balance
        uint256 treasuryBalance = nft.treasuryBalance();
        assertEq(treasuryBalance, expectedTreasuryShare, "Treasury should have 50% of payment");

        // Second mint should accumulate
        vm.prank(minter2);
        nft.mint{value: totalPayment}(author, quantity);

        uint256 treasuryBalanceAfter = nft.treasuryBalance();
        assertEq(treasuryBalanceAfter, expectedTreasuryShare * 2, "Treasury should accumulate from multiple mints");
    }

    /**
     * @notice Test that direct ETH payments go to treasury
     * @dev T055: Send ETH directly to contract, verify treasury balance increases
     */
    function testDirectPaymentToTreasury() public {
        uint256 paymentAmount = 1 ether;

        // Record initial balance
        uint256 treasuryBefore = nft.treasuryBalance();

        // Send ETH directly to contract
        vm.expectEmit(true, true, true, true);
        emit DirectPaymentReceived(minter1, paymentAmount);

        vm.prank(minter1);
        (bool success,) = address(nft).call{value: paymentAmount}("");
        assertTrue(success, "Direct payment should succeed");

        // Verify treasury balance increased
        uint256 treasuryAfter = nft.treasuryBalance();
        assertEq(treasuryAfter, treasuryBefore + paymentAmount, "Treasury should receive direct payment");
    }

    /**
     * @notice Test that owner can withdraw all treasury funds
     * @dev T056: Owner withdraws all treasury funds
     */
    function testWithdrawTreasury() public {
        uint256 quantity = 10;
        uint256 totalPayment = INITIAL_PRICE * quantity;

        // Mint to accumulate treasury
        vm.prank(minter1);
        nft.mint{value: totalPayment}(author, quantity);

        // Add direct payment
        uint256 directPayment = 2 ether;
        vm.prank(minter2);
        (bool success,) = address(nft).call{value: directPayment}("");
        assertTrue(success, "Direct payment should succeed");

        uint256 expectedTreasuryBalance = (totalPayment / 2) + directPayment;
        assertEq(nft.treasuryBalance(), expectedTreasuryBalance, "Treasury balance incorrect before withdrawal");

        // Owner withdraws treasury
        uint256 ownerBalanceBefore = owner.balance;

        vm.expectEmit(true, true, true, true);
        emit TreasuryWithdrawn(owner, expectedTreasuryBalance);

        vm.prank(owner);
        nft.withdrawTreasury();

        // Verify owner received funds
        uint256 ownerBalanceAfter = owner.balance;
        assertEq(ownerBalanceAfter, ownerBalanceBefore + expectedTreasuryBalance, "Owner should receive treasury funds");

        // Verify treasury balance reset to zero
        assertEq(nft.treasuryBalance(), 0, "Treasury balance should be zero after withdrawal");
    }

    /**
     * @notice Test that non-owner cannot withdraw treasury
     * @dev T057: Non-owner cannot withdraw
     */
    function testWithdrawRevertsUnauthorized() public {
        uint256 quantity = 5;
        uint256 totalPayment = INITIAL_PRICE * quantity;

        // Mint to accumulate treasury
        vm.prank(minter1);
        nft.mint{value: totalPayment}(author, quantity);

        // Unauthorized user attempts to withdraw
        vm.prank(unauthorized);
        vm.expectRevert();
        nft.withdrawTreasury();

        // Verify treasury balance unchanged
        assertGt(nft.treasuryBalance(), 0, "Treasury balance should still have funds");
    }

    /**
     * @notice Test that withdraw with zero balance reverts
     * @dev T058: Withdraw with zero balance reverts
     */
    function testWithdrawRevertsNoBalance() public {
        // Verify treasury is empty
        assertEq(nft.treasuryBalance(), 0, "Treasury should be empty");

        // Owner attempts to withdraw empty treasury
        vm.prank(owner);
        vm.expectRevert(GliskNFT.NoBalance.selector);
        nft.withdrawTreasury();
    }

    /**
     * @notice Test treasury accumulation with overpayment
     */
    function testTreasuryReceivesOverpayment() public {
        uint256 quantity = 3;
        uint256 requiredPayment = INITIAL_PRICE * quantity;
        uint256 overpayment = 0.5 ether;
        uint256 totalPayment = requiredPayment + overpayment;

        // Mint with overpayment
        vm.prank(minter1);
        nft.mint{value: totalPayment}(author, quantity);

        // Treasury should receive 50% of base + 100% of overpayment
        uint256 expectedTreasuryShare = (requiredPayment / 2) + overpayment;
        assertEq(nft.treasuryBalance(), expectedTreasuryShare, "Treasury should receive base share + overpayment");
    }

    /**
     * @notice Test multiple direct payments accumulate
     */
    function testMultipleDirectPaymentsAccumulate() public {
        uint256 payment1 = 1 ether;
        uint256 payment2 = 2 ether;
        uint256 payment3 = 0.5 ether;

        // First payment
        vm.prank(minter1);
        (bool success1,) = address(nft).call{value: payment1}("");
        assertTrue(success1, "Payment 1 should succeed");

        assertEq(nft.treasuryBalance(), payment1, "Treasury should have payment 1");

        // Second payment
        vm.prank(minter2);
        (bool success2,) = address(nft).call{value: payment2}("");
        assertTrue(success2, "Payment 2 should succeed");

        assertEq(nft.treasuryBalance(), payment1 + payment2, "Treasury should have payment 1 + 2");

        // Third payment
        vm.prank(minter1);
        (bool success3,) = address(nft).call{value: payment3}("");
        assertTrue(success3, "Payment 3 should succeed");

        assertEq(nft.treasuryBalance(), payment1 + payment2 + payment3, "Treasury should have all payments");
    }

    /**
     * @notice Test withdrawal reentrancy protection
     */
    function testWithdrawReentrancyProtection() public {
        // Deploy attacking contract
        TreasuryAttacker attacker = new TreasuryAttacker(payable(address(nft)));

        // Transfer ownership to attacker
        bytes32 adminRole = nft.DEFAULT_ADMIN_ROLE();
        vm.prank(owner);
        nft.grantRole(adminRole, address(attacker));

        // Fund treasury
        vm.prank(minter1);
        (bool success,) = address(nft).call{value: 1 ether}("");
        assertTrue(success, "Direct payment should succeed");

        // Attempt reentrancy attack
        vm.prank(address(attacker));
        vm.expectRevert(); // Should revert due to ReentrancyGuard
        attacker.attack();
    }

    /**
     * @notice Test treasury withdrawal after author claims
     */
    function testWithdrawTreasuryAfterAuthorClaims() public {
        uint256 quantity = 10;
        uint256 totalPayment = INITIAL_PRICE * quantity;

        // Mint NFTs
        vm.prank(minter1);
        nft.mint{value: totalPayment}(author, quantity);

        uint256 expectedTreasuryShare = totalPayment / 2;
        uint256 expectedAuthorShare = totalPayment / 2;

        // Author claims rewards
        vm.prank(author);
        nft.claimAuthorRewards();

        // Verify author received their share
        assertEq(author.balance, expectedAuthorShare, "Author should have their share");

        // Treasury balance should remain unchanged
        assertEq(nft.treasuryBalance(), expectedTreasuryShare, "Treasury balance should be unchanged");

        // Owner withdraws treasury
        vm.prank(owner);
        nft.withdrawTreasury();

        // Verify owner received treasury funds
        assertEq(owner.balance, expectedTreasuryShare, "Owner should receive treasury share");
        assertEq(nft.treasuryBalance(), 0, "Treasury should be empty");
    }

    /**
     * @notice Test contract balance invariant
     */
    function testBalanceInvariant() public {
        uint256 quantity = 5;
        uint256 totalPayment = INITIAL_PRICE * quantity;

        // Mint NFTs
        vm.prank(minter1);
        nft.mint{value: totalPayment}(author, quantity);

        // Add direct payment
        uint256 directPayment = 1 ether;
        vm.prank(minter2);
        (bool success,) = address(nft).call{value: directPayment}("");
        assertTrue(success, "Direct payment should succeed");

        // Verify balance invariant: contract.balance == treasuryBalance + authorClaimable
        uint256 contractBalance = address(nft).balance;
        uint256 treasuryBalance = nft.treasuryBalance();
        uint256 authorBalance = nft.authorClaimable(author);

        assertEq(contractBalance, treasuryBalance + authorBalance, "Balance invariant should hold");
    }

    /**
     * @notice Test withdrawal with failed transfer
     */
    function testWithdrawTransferFails() public {
        // Deploy rejecting contract
        RejectingOwner rejectingOwner = new RejectingOwner();

        // Grant admin role to rejecting contract
        bytes32 adminRole = nft.DEFAULT_ADMIN_ROLE();
        vm.prank(owner);
        nft.grantRole(adminRole, address(rejectingOwner));

        // Fund treasury
        vm.prank(minter1);
        (bool success,) = address(nft).call{value: 1 ether}("");
        assertTrue(success, "Direct payment should succeed");

        // Attempt withdrawal from rejecting contract
        vm.prank(address(rejectingOwner));
        vm.expectRevert(GliskNFT.TransferFailed.selector);
        nft.withdrawTreasury();

        // Verify treasury balance unchanged
        assertEq(nft.treasuryBalance(), 1 ether, "Treasury balance should be unchanged after failed transfer");
    }
}

/**
 * @title TreasuryAttacker
 * @notice Helper contract to test reentrancy protection on withdrawTreasury
 */
contract TreasuryAttacker {
    GliskNFT public nft;
    uint256 public attackCount;

    constructor(address payable _nft) {
        nft = GliskNFT(_nft);
    }

    function attack() external {
        nft.withdrawTreasury();
    }

    receive() external payable {
        // Attempt to re-enter withdrawTreasury
        if (attackCount < 2) {
            attackCount++;
            nft.withdrawTreasury();
        }
    }
}

/**
 * @title RejectingOwner
 * @notice Helper contract that rejects ETH transfers
 */
contract RejectingOwner {
// No receive() or fallback() - will reject ETH
}
