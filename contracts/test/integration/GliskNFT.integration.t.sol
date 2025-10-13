// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../../src/GliskNFT.sol";

/**
 * @title GliskNFT Integration Tests
 * @notice Comprehensive end-to-end integration tests for GLISK NFT contract
 * @dev Tests complete user journeys across multiple user stories
 */
contract GliskNFTIntegrationTest is Test {
    GliskNFT public nft;

    // Test actors
    address public owner;
    address public keeper;
    address public user1;
    address public user2;
    address public user3;
    address public author1;
    address public author2;
    address public author3;

    // Test constants
    string constant NAME = "GLISK Season 0";
    string constant SYMBOL = "GLISK0";
    string constant PLACEHOLDER_URI = "ipfs://QmPlaceholder";
    string constant REVEALED_URI_1 = "ipfs://QmRevealed1";
    string constant REVEALED_URI_2 = "ipfs://QmRevealed2";
    string constant REVEALED_URI_3 = "ipfs://QmRevealed3";
    uint256 constant INITIAL_MINT_PRICE = 0.001 ether;
    uint256 constant UPDATED_MINT_PRICE = 0.002 ether;

    // Events to test
    event BatchMinted(
        address indexed minter,
        address indexed promptAuthor,
        uint256 indexed startTokenId,
        uint256 quantity,
        uint256 totalPaid
    );
    event AuthorClaimed(address indexed author, uint256 amount);
    event TokensRevealed(uint256[] tokenIds);
    event SeasonEnded(uint256 timestamp);
    event UnclaimedRewardsSwept(uint256 totalAmount, uint256 authorsCount);
    event MintPriceUpdated(uint256 oldPrice, uint256 newPrice);

    function setUp() public {
        // Setup test accounts
        owner = makeAddr("owner");
        keeper = makeAddr("keeper");
        user1 = makeAddr("user1");
        user2 = makeAddr("user2");
        user3 = makeAddr("user3");
        author1 = makeAddr("author1");
        author2 = makeAddr("author2");
        author3 = makeAddr("author3");

        // Fund test accounts
        vm.deal(owner, 100 ether);
        vm.deal(user1, 10 ether);
        vm.deal(user2, 10 ether);
        vm.deal(user3, 10 ether);

        // Deploy contract as owner
        vm.startPrank(owner);
        nft = new GliskNFT(NAME, SYMBOL, PLACEHOLDER_URI, INITIAL_MINT_PRICE);

        // Grant keeper role
        nft.grantRole(nft.KEEPER_ROLE(), keeper);
        vm.stopPrank();
    }

    /**
     * @notice T112 - Complete user journey: mint → claim → reveal → season end → sweep
     * @dev Tests the entire lifecycle from initial mint to season closure
     */
    function testCompleteUserJourney() public {
        // PHASE 1: Users mint NFTs from different authors
        vm.prank(user1);
        nft.mint{value: INITIAL_MINT_PRICE * 5}(author1, 5);
        assertEq(nft.balanceOf(user1), 5);

        vm.prank(user2);
        nft.mint{value: INITIAL_MINT_PRICE * 3}(author2, 3);
        assertEq(nft.balanceOf(user2), 3);

        vm.prank(user3);
        nft.mint{value: INITIAL_MINT_PRICE * 2}(author1, 2);
        assertEq(nft.balanceOf(user3), 2);

        // Verify author balances
        uint256 author1Expected = (INITIAL_MINT_PRICE * 5) / 2 + (INITIAL_MINT_PRICE * 2) / 2;
        uint256 author2Expected = (INITIAL_MINT_PRICE * 3) / 2;
        assertEq(nft.authorClaimable(author1), author1Expected);
        assertEq(nft.authorClaimable(author2), author2Expected);

        // Verify treasury balance
        uint256 treasuryExpected = (INITIAL_MINT_PRICE * 10) - author1Expected - author2Expected;
        assertEq(nft.treasuryBalance(), treasuryExpected);

        // PHASE 2: Author 1 claims rewards
        uint256 author1BalanceBefore = author1.balance;
        vm.prank(author1);
        nft.claimAuthorRewards();
        assertEq(author1.balance, author1BalanceBefore + author1Expected);
        assertEq(nft.authorClaimable(author1), 0);

        // PHASE 3: Owner reveals some tokens
        uint256[] memory tokenIds = new uint256[](5);
        string[] memory uris = new string[](5);
        for (uint256 i = 0; i < 5; i++) {
            tokenIds[i] = i + 1;
            uris[i] = string(abi.encodePacked(REVEALED_URI_1, vm.toString(i)));
        }

        vm.prank(owner);
        nft.revealTokens(tokenIds, uris);

        // Verify tokens are revealed
        for (uint256 i = 0; i < 5; i++) {
            assertTrue(nft.isRevealed(i + 1));
            assertEq(nft.tokenURI(i + 1), uris[i]);
        }

        // Verify unrevealed tokens still show placeholder
        assertFalse(nft.isRevealed(6));
        assertEq(nft.tokenURI(6), PLACEHOLDER_URI);

        // PHASE 4: Owner ends season
        vm.prank(owner);
        nft.endSeason();
        assertTrue(nft.seasonEnded());
        assertGt(nft.seasonEndTime(), 0);

        // Verify minting is disabled
        vm.prank(user1);
        vm.expectRevert(GliskNFT.MintingDisabled.selector);
        nft.mint{value: INITIAL_MINT_PRICE}(author1, 1);

        // PHASE 5: Author 2 can still claim during countdown
        uint256 author2BalanceBefore = author2.balance;
        vm.prank(author2);
        nft.claimAuthorRewards();
        assertEq(author2.balance, author2BalanceBefore + author2Expected);
        assertEq(nft.authorClaimable(author2), 0);

        // PHASE 6: Fast forward past sweep protection period
        vm.warp(block.timestamp + 14 days + 1);

        // Owner sweeps unclaimed rewards (author1 already claimed, so only author2 if they hadn't)
        // In this test, both authors claimed, so sweep should handle empty balances
        address[] memory authors = new address[](2);
        authors[0] = author1;
        authors[1] = author2;

        uint256 treasuryBefore = nft.treasuryBalance();
        vm.prank(owner);
        nft.sweepUnclaimedRewards(authors);

        // No change since both claimed
        assertEq(nft.treasuryBalance(), treasuryBefore);

        // PHASE 7: Owner withdraws treasury
        uint256 ownerBalanceBefore = owner.balance;
        vm.prank(owner);
        nft.withdrawTreasury();
        assertEq(owner.balance, ownerBalanceBefore + treasuryExpected);
        assertEq(nft.treasuryBalance(), 0);

        // Verify final state
        assertEq(address(nft).balance, 0);
        assertEq(nft.authorClaimable(author1), 0);
        assertEq(nft.authorClaimable(author2), 0);
    }

    /**
     * @notice T113 - Multiple users minting and claiming concurrently
     * @dev Tests concurrent interactions without conflicts
     */
    function testMultipleUsersConcurrent() public {
        // Simulate concurrent mints from multiple users
        uint256[] memory startBalances = new uint256[](3);
        startBalances[0] = user1.balance;
        startBalances[1] = user2.balance;
        startBalances[2] = user3.balance;

        // User 1 mints 10 NFTs
        vm.prank(user1);
        nft.mint{value: INITIAL_MINT_PRICE * 10}(author1, 10);

        // User 2 mints 15 NFTs (different author)
        vm.prank(user2);
        nft.mint{value: INITIAL_MINT_PRICE * 15}(author2, 15);

        // User 3 mints 5 NFTs (same author as user1)
        vm.prank(user3);
        nft.mint{value: INITIAL_MINT_PRICE * 5}(author1, 5);

        // Verify no token ID collisions
        assertEq(nft.balanceOf(user1), 10);
        assertEq(nft.balanceOf(user2), 15);
        assertEq(nft.balanceOf(user3), 5);

        // Verify sequential token IDs
        assertEq(nft.ownerOf(1), user1);
        assertEq(nft.ownerOf(10), user1);
        assertEq(nft.ownerOf(11), user2);
        assertEq(nft.ownerOf(25), user2);
        assertEq(nft.ownerOf(26), user3);
        assertEq(nft.ownerOf(30), user3);

        // Verify author balances accumulated correctly
        uint256 author1Total = (INITIAL_MINT_PRICE * 10) / 2 + (INITIAL_MINT_PRICE * 5) / 2;
        uint256 author2Total = (INITIAL_MINT_PRICE * 15) / 2;
        assertEq(nft.authorClaimable(author1), author1Total);
        assertEq(nft.authorClaimable(author2), author2Total);

        // Simulate concurrent claims
        uint256 author1BalBefore = author1.balance;
        uint256 author2BalBefore = author2.balance;

        vm.prank(author1);
        nft.claimAuthorRewards();

        vm.prank(author2);
        nft.claimAuthorRewards();

        // Verify both authors received correct amounts
        assertEq(author1.balance, author1BalBefore + author1Total);
        assertEq(author2.balance, author2BalBefore + author2Total);
        assertEq(nft.authorClaimable(author1), 0);
        assertEq(nft.authorClaimable(author2), 0);

        // Verify contract balance conservation
        uint256 expectedTreasury = (INITIAL_MINT_PRICE * 30) - author1Total - author2Total;
        assertEq(nft.treasuryBalance(), expectedTreasury);
        assertEq(address(nft).balance, expectedTreasury);
    }

    /**
     * @notice T114 - Price update during active minting season
     * @dev Tests that price changes affect subsequent mints correctly
     */
    function testPriceUpdateMidSeason() public {
        // Phase 1: Mint at initial price
        vm.prank(user1);
        nft.mint{value: INITIAL_MINT_PRICE * 5}(author1, 5);

        uint256 author1BalanceAfterFirst = nft.authorClaimable(author1);
        uint256 treasuryAfterFirst = nft.treasuryBalance();

        assertEq(author1BalanceAfterFirst, (INITIAL_MINT_PRICE * 5) / 2);
        assertEq(treasuryAfterFirst, (INITIAL_MINT_PRICE * 5) - author1BalanceAfterFirst);

        // Phase 2: Keeper updates price
        vm.prank(keeper);
        vm.expectEmit(true, true, true, true);
        emit MintPriceUpdated(INITIAL_MINT_PRICE, UPDATED_MINT_PRICE);
        nft.setMintPrice(UPDATED_MINT_PRICE);

        assertEq(nft.mintPrice(), UPDATED_MINT_PRICE);

        // Phase 3: Mint at new price
        vm.prank(user2);
        nft.mint{value: UPDATED_MINT_PRICE * 3}(author2, 3);

        uint256 author2Balance = nft.authorClaimable(author2);
        assertEq(author2Balance, (UPDATED_MINT_PRICE * 3) / 2);

        // Phase 4: Verify old mints unaffected
        assertEq(nft.authorClaimable(author1), author1BalanceAfterFirst);

        // Phase 5: Mint at new price for same author as first mint
        vm.prank(user3);
        nft.mint{value: UPDATED_MINT_PRICE * 2}(author1, 2);

        // Verify author1 balance accumulated correctly with both prices
        uint256 author1NewShare = (UPDATED_MINT_PRICE * 2) / 2;
        assertEq(nft.authorClaimable(author1), author1BalanceAfterFirst + author1NewShare);

        // Verify tokens were minted (check ownership)
        assertEq(nft.ownerOf(1), user1);
        assertEq(nft.ownerOf(5), user1);

        // Phase 6: Verify insufficient payment at old price fails
        vm.prank(user1);
        vm.expectRevert(GliskNFT.InsufficientPayment.selector);
        nft.mint{value: INITIAL_MINT_PRICE}(author1, 1);

        // Phase 7: Owner can also update price
        vm.prank(owner);
        nft.setMintPrice(INITIAL_MINT_PRICE);
        assertEq(nft.mintPrice(), INITIAL_MINT_PRICE);

        // Mint at reverted price
        vm.prank(user1);
        nft.mint{value: INITIAL_MINT_PRICE}(author3, 1);
        assertEq(nft.balanceOf(user1), 6); // user1 now has 6 total (5 + 1)
    }

    /**
     * @notice T115 - Complete season lifecycle from start to finish
     * @dev Tests season end, countdown, and sweep workflow
     */
    function testSeasonLifecycle() public {
        // PHASE 1: Active season - multiple mints
        vm.prank(user1);
        nft.mint{value: INITIAL_MINT_PRICE * 10}(author1, 10);

        vm.prank(user2);
        nft.mint{value: INITIAL_MINT_PRICE * 8}(author2, 8);

        vm.prank(user3);
        nft.mint{value: INITIAL_MINT_PRICE * 6}(author3, 6);

        uint256 totalMinted = 24;
        assertFalse(nft.seasonEnded());

        // Store expected balances
        uint256 author1Expected = (INITIAL_MINT_PRICE * 10) / 2;
        uint256 author2Expected = (INITIAL_MINT_PRICE * 8) / 2;
        uint256 author3Expected = (INITIAL_MINT_PRICE * 6) / 2;

        // PHASE 2: Author 1 claims during active season
        vm.prank(author1);
        nft.claimAuthorRewards();
        assertEq(nft.authorClaimable(author1), 0);

        // PHASE 3: Owner ends season
        uint256 seasonEndTimestamp = block.timestamp;
        vm.prank(owner);
        vm.expectEmit(true, true, true, true);
        emit SeasonEnded(seasonEndTimestamp);
        nft.endSeason();

        assertTrue(nft.seasonEnded());
        assertEq(nft.seasonEndTime(), seasonEndTimestamp);

        // PHASE 4: Verify minting is disabled
        vm.prank(user1);
        vm.expectRevert(GliskNFT.MintingDisabled.selector);
        nft.mint{value: INITIAL_MINT_PRICE}(author1, 1);

        // PHASE 5: Cannot end season twice
        vm.prank(owner);
        vm.expectRevert(GliskNFT.SeasonAlreadyEnded.selector);
        nft.endSeason();

        // PHASE 6: Authors can still claim during protection period
        vm.prank(author2);
        nft.claimAuthorRewards();
        assertEq(nft.authorClaimable(author2), 0);

        // PHASE 7: Cannot sweep before protection period
        address[] memory authors = new address[](1);
        authors[0] = author3;

        vm.prank(owner);
        vm.expectRevert(GliskNFT.SweepProtectionActive.selector);
        nft.sweepUnclaimedRewards(authors);

        // PHASE 8: Fast forward past protection period
        vm.warp(seasonEndTimestamp + 14 days + 1);

        // PHASE 9: Sweep unclaimed rewards
        uint256 treasuryBefore = nft.treasuryBalance();

        vm.prank(owner);
        vm.expectEmit(true, true, true, true);
        emit UnclaimedRewardsSwept(author3Expected, 1);
        nft.sweepUnclaimedRewards(authors);

        // Verify author3's balance swept to treasury
        assertEq(nft.authorClaimable(author3), 0);
        assertEq(nft.treasuryBalance(), treasuryBefore + author3Expected);

        // PHASE 10: Author 3 tries to claim after sweep
        uint256 author3BalBefore = author3.balance;
        vm.prank(author3);
        nft.claimAuthorRewards(); // Should not revert, just transfer 0
        assertEq(author3.balance, author3BalBefore); // No change

        // PHASE 11: Verify final balances
        uint256 totalRevenue = INITIAL_MINT_PRICE * totalMinted;
        uint256 totalAuthorShare = author1Expected + author2Expected + author3Expected;
        uint256 expectedTreasury = totalRevenue - totalAuthorShare + author3Expected; // +author3 swept

        assertEq(nft.treasuryBalance(), expectedTreasury);
        assertEq(address(nft).balance, expectedTreasury);
    }

    /**
     * @notice T116 - Role management workflow with keeper operations
     * @dev Tests role granting, operations, and revocation
     */
    function testRoleManagementWorkflow() public {
        address newKeeper = makeAddr("newKeeper");

        // PHASE 1: Verify keeper can perform authorized operations
        // Keeper updates price
        vm.prank(keeper);
        nft.setMintPrice(UPDATED_MINT_PRICE);
        assertEq(nft.mintPrice(), UPDATED_MINT_PRICE);

        // Mint some tokens to test reveal
        vm.prank(user1);
        nft.mint{value: UPDATED_MINT_PRICE * 3}(author1, 3);

        // Keeper reveals tokens
        uint256[] memory tokenIds = new uint256[](2);
        string[] memory uris = new string[](2);
        tokenIds[0] = 1;
        tokenIds[1] = 2;
        uris[0] = REVEALED_URI_1;
        uris[1] = REVEALED_URI_2;

        vm.prank(keeper);
        nft.revealTokens(tokenIds, uris);
        assertTrue(nft.isRevealed(1));
        assertTrue(nft.isRevealed(2));

        // PHASE 2: Verify keeper CANNOT perform owner-only operations
        // Cannot withdraw treasury
        vm.prank(keeper);
        vm.expectRevert(); // AccessControlUnauthorizedAccount
        nft.withdrawTreasury();

        // Cannot end season
        vm.prank(keeper);
        vm.expectRevert(); // AccessControlUnauthorizedAccount
        nft.endSeason();

        // Cannot update placeholder URI
        vm.prank(keeper);
        vm.expectRevert(); // AccessControlUnauthorizedAccount
        nft.setPlaceholderURI("ipfs://QmNewPlaceholder");

        // Cannot grant roles
        bytes32 keeperRole = nft.KEEPER_ROLE();
        vm.prank(keeper);
        vm.expectRevert(); // AccessControlUnauthorizedAccount
        nft.grantRole(keeperRole, newKeeper);

        // PHASE 3: Owner grants keeper role to new address
        vm.prank(owner);
        nft.grantRole(keeperRole, newKeeper);
        assertTrue(nft.hasRole(nft.KEEPER_ROLE(), newKeeper));

        // PHASE 4: New keeper can perform keeper operations
        vm.prank(newKeeper);
        nft.setMintPrice(INITIAL_MINT_PRICE);
        assertEq(nft.mintPrice(), INITIAL_MINT_PRICE);

        // PHASE 5: Owner revokes original keeper role
        vm.startPrank(owner);
        nft.revokeRole(keeperRole, keeper);
        assertFalse(nft.hasRole(keeperRole, keeper));
        vm.stopPrank();

        // PHASE 6: Revoked keeper cannot perform operations
        vm.prank(keeper);
        vm.expectRevert();
        nft.setMintPrice(UPDATED_MINT_PRICE);

        // PHASE 7: Owner can still perform all operations
        vm.prank(owner);
        nft.setMintPrice(UPDATED_MINT_PRICE);
        assertEq(nft.mintPrice(), UPDATED_MINT_PRICE);

        vm.prank(owner);
        nft.setPlaceholderURI("ipfs://QmOwnerPlaceholder");

        uint256[] memory ownerTokenIds = new uint256[](1);
        string[] memory ownerUris = new string[](1);
        ownerTokenIds[0] = 3;
        ownerUris[0] = REVEALED_URI_3;

        vm.prank(owner);
        nft.revealTokens(ownerTokenIds, ownerUris);
        assertTrue(nft.isRevealed(3));

        // PHASE 8: Owner can end season and perform final operations
        vm.prank(owner);
        nft.endSeason();
        assertTrue(nft.seasonEnded());

        // Fast forward and sweep
        vm.warp(block.timestamp + 14 days + 1);

        address[] memory authors = new address[](1);
        authors[0] = author1;

        vm.prank(owner);
        nft.sweepUnclaimedRewards(authors);

        // Owner withdraws treasury
        vm.prank(owner);
        nft.withdrawTreasury();
        assertEq(nft.treasuryBalance(), 0);

        // PHASE 9: Verify new keeper still has role and owner retains all permissions
        assertTrue(nft.hasRole(nft.KEEPER_ROLE(), newKeeper));
        assertTrue(nft.hasRole(nft.DEFAULT_ADMIN_ROLE(), owner));
    }

    /**
     * @notice Additional edge case: Direct payment to contract during season
     */
    function testDirectPaymentIntegration() public {
        // User mints normally
        vm.prank(user1);
        nft.mint{value: INITIAL_MINT_PRICE * 5}(author1, 5);

        uint256 treasuryAfterMint = nft.treasuryBalance();

        // Someone sends ETH directly to contract
        uint256 directPayment = 1 ether;
        vm.deal(user2, directPayment + 10 ether);
        vm.prank(user2);
        (bool success,) = address(nft).call{value: directPayment}("");
        assertTrue(success);

        // Treasury should increase
        assertEq(nft.treasuryBalance(), treasuryAfterMint + directPayment);
        // Contract balance = treasury + author claimable
        uint256 authorClaimable = nft.authorClaimable(author1);
        assertEq(address(nft).balance, nft.treasuryBalance() + authorClaimable);

        // Owner can withdraw combined treasury
        vm.prank(owner);
        nft.withdrawTreasury();
        assertEq(nft.treasuryBalance(), 0);
    }

    /**
     * @notice Edge case: Overpayment handling in integration scenario
     */
    function testOverpaymentIntegration() public {
        uint256 overpayment = 0.5 ether;
        uint256 totalPayment = INITIAL_MINT_PRICE * 3 + overpayment;

        vm.prank(user1);
        nft.mint{value: totalPayment}(author1, 3);

        // Author gets 50% of base price only
        uint256 authorShare = (INITIAL_MINT_PRICE * 3) / 2;
        assertEq(nft.authorClaimable(author1), authorShare);

        // Treasury gets remaining base + all overpayment
        uint256 treasuryShare = (INITIAL_MINT_PRICE * 3) - authorShare + overpayment;
        assertEq(nft.treasuryBalance(), treasuryShare);

        // Verify balance conservation
        assertEq(address(nft).balance, totalPayment);
        assertEq(nft.authorClaimable(author1) + nft.treasuryBalance(), totalPayment);
    }

    /**
     * @notice Edge case: Batch reveal integration with multiple keepers
     */
    function testBatchRevealWithMultipleKeepers() public {
        address keeper2 = makeAddr("keeper2");

        // Grant second keeper role
        vm.startPrank(owner);
        nft.grantRole(nft.KEEPER_ROLE(), keeper2);
        vm.stopPrank();

        // Mint tokens
        vm.prank(user1);
        nft.mint{value: INITIAL_MINT_PRICE * 10}(author1, 10);

        // Keeper 1 reveals first batch
        uint256[] memory batch1 = new uint256[](5);
        string[] memory uris1 = new string[](5);
        for (uint256 i = 0; i < 5; i++) {
            batch1[i] = i + 1;
            uris1[i] = string(abi.encodePacked("ipfs://batch1/", vm.toString(i)));
        }

        vm.prank(keeper);
        nft.revealTokens(batch1, uris1);

        // Keeper 2 reveals second batch
        uint256[] memory batch2 = new uint256[](5);
        string[] memory uris2 = new string[](5);
        for (uint256 i = 0; i < 5; i++) {
            batch2[i] = i + 6;
            uris2[i] = string(abi.encodePacked("ipfs://batch2/", vm.toString(i)));
        }

        vm.prank(keeper2);
        nft.revealTokens(batch2, uris2);

        // Verify all tokens revealed correctly
        for (uint256 i = 1; i <= 10; i++) {
            assertTrue(nft.isRevealed(i));
        }
    }
}
