// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../../src/GliskNFT.sol";

/**
 * @title GliskNFT Season Management Tests
 * @notice Unit tests for User Story 4: Season End and Unclaimed Rewards
 * @dev Tests season lifecycle, minting restrictions, and reward sweeping
 */
contract GliskNFTSeasonTest is Test {
    GliskNFT public gliskNFT;

    address owner = address(1);
    address user = address(2);
    address promptAuthor1 = address(3);
    address promptAuthor2 = address(4);

    string constant PLACEHOLDER_URI = "ipfs://placeholder";
    uint256 constant INITIAL_MINT_PRICE = 0.01 ether;

    event SeasonEnded(uint256 timestamp);
    event UnclaimedRewardsSwept(uint256 totalAmount, uint256 authorsCount);
    event BatchMinted(
        address indexed minter,
        address indexed promptAuthor,
        uint256 indexed startTokenId,
        uint256 quantity,
        uint256 totalPaid
    );

    function setUp() public {
        // Deploy contract as owner
        vm.startPrank(owner);
        gliskNFT = new GliskNFT("GLISK", "GLK", PLACEHOLDER_URI, INITIAL_MINT_PRICE);
        vm.stopPrank();

        // Fund test accounts
        vm.deal(user, 10 ether);
    }

    /**
     * @notice T087: Owner ends season, minting stops, countdown starts
     */
    function testEndSeason() public {
        // Verify season is not ended initially
        assertFalse(gliskNFT.seasonEnded(), "Season should not be ended initially");
        assertEq(gliskNFT.seasonEndTime(), 0, "Season end time should be zero initially");

        // Owner ends season
        vm.prank(owner);
        vm.expectEmit(false, false, false, false);
        emit SeasonEnded(block.timestamp);
        gliskNFT.endSeason();

        // Verify season is ended
        assertTrue(gliskNFT.seasonEnded(), "Season should be ended");
        assertEq(gliskNFT.seasonEndTime(), block.timestamp, "Season end time should be set");
    }

    /**
     * @notice T088: Mint attempt after seasonEnd reverts
     */
    function testMintRevertsAfterSeasonEnd() public {
        // End season
        vm.prank(owner);
        gliskNFT.endSeason();

        // User tries to mint after season end
        vm.prank(user);
        vm.expectRevert(GliskNFT.MintingDisabled.selector);
        gliskNFT.mint{value: INITIAL_MINT_PRICE}(promptAuthor1, 1);
    }

    /**
     * @notice T089: Authors can claim during countdown period
     */
    function testClaimDuringCountdown() public {
        // Mint to create author rewards
        vm.prank(user);
        gliskNFT.mint{value: INITIAL_MINT_PRICE}(promptAuthor1, 1);

        uint256 authorBalance = gliskNFT.authorClaimable(promptAuthor1);
        assertGt(authorBalance, 0, "Author should have claimable balance");

        // End season
        vm.prank(owner);
        gliskNFT.endSeason();

        // Author claims during countdown
        vm.prank(promptAuthor1);
        gliskNFT.claimAuthorRewards();

        // Verify claim succeeded
        assertEq(gliskNFT.authorClaimable(promptAuthor1), 0, "Author balance should be zero after claim");
        assertEq(promptAuthor1.balance, authorBalance, "Author should receive ETH");
    }

    /**
     * @notice T090: Owner sweeps unclaimed rewards after 2 weeks
     */
    function testSweepAfterCountdown() public {
        // Mint to create author rewards
        vm.prank(user);
        gliskNFT.mint{value: INITIAL_MINT_PRICE * 2}(promptAuthor1, 2);

        vm.prank(user);
        gliskNFT.mint{value: INITIAL_MINT_PRICE}(promptAuthor2, 1);

        uint256 author1Balance = gliskNFT.authorClaimable(promptAuthor1);
        uint256 author2Balance = gliskNFT.authorClaimable(promptAuthor2);
        uint256 treasuryBefore = gliskNFT.treasuryBalance();

        // End season
        vm.prank(owner);
        gliskNFT.endSeason();

        // Fast forward past countdown period (14 days)
        vm.warp(block.timestamp + 14 days + 1);

        // Prepare authors array
        address[] memory authors = new address[](2);
        authors[0] = promptAuthor1;
        authors[1] = promptAuthor2;

        // Owner sweeps unclaimed rewards
        vm.prank(owner);
        vm.expectEmit(false, false, false, true);
        emit UnclaimedRewardsSwept(author1Balance + author2Balance, 2);
        gliskNFT.sweepUnclaimedRewards(authors);

        // Verify rewards were swept to treasury
        assertEq(gliskNFT.authorClaimable(promptAuthor1), 0, "Author 1 balance should be zero");
        assertEq(gliskNFT.authorClaimable(promptAuthor2), 0, "Author 2 balance should be zero");
        assertEq(
            gliskNFT.treasuryBalance(),
            treasuryBefore + author1Balance + author2Balance,
            "Treasury should receive swept funds"
        );
    }

    /**
     * @notice T091: Sweep before countdown expires reverts
     */
    function testSweepRevertsBeforeCountdown() public {
        // Mint to create author rewards
        vm.prank(user);
        gliskNFT.mint{value: INITIAL_MINT_PRICE}(promptAuthor1, 1);

        // End season
        vm.prank(owner);
        gliskNFT.endSeason();

        // Try to sweep before countdown expires (only 1 week)
        vm.warp(block.timestamp + 7 days);

        address[] memory authors = new address[](1);
        authors[0] = promptAuthor1;

        // Sweep should revert
        vm.prank(owner);
        vm.expectRevert(GliskNFT.SweepProtectionActive.selector);
        gliskNFT.sweepUnclaimedRewards(authors);
    }

    /**
     * @notice T092: Sweep without seasonEnd reverts
     */
    function testSweepRevertsSeasonNotEnded() public {
        // Mint to create author rewards
        vm.prank(user);
        gliskNFT.mint{value: INITIAL_MINT_PRICE}(promptAuthor1, 1);

        // Try to sweep without ending season
        address[] memory authors = new address[](1);
        authors[0] = promptAuthor1;

        vm.prank(owner);
        vm.expectRevert(GliskNFT.SeasonNotEnded.selector);
        gliskNFT.sweepUnclaimedRewards(authors);
    }

    /**
     * @notice T093: Cannot end season twice
     */
    function testSeasonEndRevertsIfAlreadyEnded() public {
        // End season first time
        vm.prank(owner);
        gliskNFT.endSeason();

        // Try to end season again
        vm.prank(owner);
        vm.expectRevert(GliskNFT.SeasonAlreadyEnded.selector);
        gliskNFT.endSeason();
    }

    /**
     * @notice T094: Sweep multiple authors correctly
     */
    function testSweepMultipleAuthors() public {
        // Mint with different authors
        vm.startPrank(user);
        gliskNFT.mint{value: INITIAL_MINT_PRICE * 5}(promptAuthor1, 5);
        gliskNFT.mint{value: INITIAL_MINT_PRICE * 3}(promptAuthor2, 3);
        vm.stopPrank();

        uint256 author1Balance = gliskNFT.authorClaimable(promptAuthor1);
        uint256 author2Balance = gliskNFT.authorClaimable(promptAuthor2);
        uint256 treasuryBefore = gliskNFT.treasuryBalance();

        // End season and fast forward
        vm.prank(owner);
        gliskNFT.endSeason();
        vm.warp(block.timestamp + 15 days);

        // Sweep both authors
        address[] memory authors = new address[](2);
        authors[0] = promptAuthor1;
        authors[1] = promptAuthor2;

        vm.prank(owner);
        gliskNFT.sweepUnclaimedRewards(authors);

        // Verify both balances swept
        assertEq(gliskNFT.authorClaimable(promptAuthor1), 0, "Author 1 should have zero balance");
        assertEq(gliskNFT.authorClaimable(promptAuthor2), 0, "Author 2 should have zero balance");
        assertEq(
            gliskNFT.treasuryBalance(),
            treasuryBefore + author1Balance + author2Balance,
            "Treasury should receive both swept amounts"
        );
    }

    /**
     * @notice Additional test: Sweep empty author list
     */
    function testSweepEmptyList() public {
        // End season and fast forward
        vm.prank(owner);
        gliskNFT.endSeason();
        vm.warp(block.timestamp + 15 days);

        // Sweep empty list
        address[] memory authors = new address[](0);

        uint256 treasuryBefore = gliskNFT.treasuryBalance();

        vm.prank(owner);
        gliskNFT.sweepUnclaimedRewards(authors);

        // Verify treasury unchanged
        assertEq(gliskNFT.treasuryBalance(), treasuryBefore, "Treasury should be unchanged");
    }

    /**
     * @notice Additional test: Sweep author with zero balance
     */
    function testSweepAuthorWithZeroBalance() public {
        // Mint for one author only
        vm.prank(user);
        gliskNFT.mint{value: INITIAL_MINT_PRICE}(promptAuthor1, 1);

        uint256 treasuryBefore = gliskNFT.treasuryBalance();

        // End season and fast forward
        vm.prank(owner);
        gliskNFT.endSeason();
        vm.warp(block.timestamp + 15 days);

        // Try to sweep author2 who has no balance
        address[] memory authors = new address[](1);
        authors[0] = promptAuthor2;

        vm.prank(owner);
        gliskNFT.sweepUnclaimedRewards(authors);

        // Treasury receives nothing from empty sweep
        assertEq(gliskNFT.treasuryBalance(), treasuryBefore, "Treasury should be unchanged");
    }

    /**
     * @notice Additional test: Non-owner cannot end season
     */
    function testNonOwnerCannotEndSeason() public {
        vm.prank(user);
        vm.expectRevert();
        gliskNFT.endSeason();
    }

    /**
     * @notice Additional test: Non-owner cannot sweep
     */
    function testNonOwnerCannotSweep() public {
        // End season and fast forward
        vm.prank(owner);
        gliskNFT.endSeason();
        vm.warp(block.timestamp + 15 days);

        address[] memory authors = new address[](1);
        authors[0] = promptAuthor1;

        vm.prank(user);
        vm.expectRevert();
        gliskNFT.sweepUnclaimedRewards(authors);
    }
}
