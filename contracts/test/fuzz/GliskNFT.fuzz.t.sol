// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../../src/GliskNFT.sol";

/**
 * @title GliskNFT Fuzz Tests
 * @notice Property-based testing with randomized inputs
 * @dev Tests contract behavior under various input conditions
 */
contract GliskNFTFuzzTest is Test {
    GliskNFT public nft;

    // Test actors
    address public owner;
    address public keeper;

    // Test constants
    string constant NAME = "GLISK Season 0";
    string constant SYMBOL = "GLISK0";
    string constant PLACEHOLDER_URI = "ipfs://QmPlaceholder";
    uint256 constant INITIAL_MINT_PRICE = 0.001 ether;
    uint256 constant MAX_BATCH_SIZE = 50;

    function setUp() public {
        owner = makeAddr("owner");
        keeper = makeAddr("keeper");

        vm.deal(owner, 100 ether);

        vm.startPrank(owner);
        nft = new GliskNFT(NAME, SYMBOL, PLACEHOLDER_URI, INITIAL_MINT_PRICE);
        nft.grantRole(nft.KEEPER_ROLE(), keeper);
        vm.stopPrank();
    }

    /**
     * @notice T119 - Fuzz test mint quantity and payment amounts
     * @dev Tests that minting works correctly with various quantities and payments
     */
    function testFuzzMintQuantity(uint8 quantity, uint256 paymentMultiplier) public {
        // Bound inputs to valid ranges
        quantity = uint8(bound(quantity, 1, MAX_BATCH_SIZE));
        paymentMultiplier = bound(paymentMultiplier, 1, 10); // 1x to 10x the required payment

        address minter = makeAddr("minter");
        address author = makeAddr("author");

        uint256 requiredPayment = INITIAL_MINT_PRICE * quantity;
        uint256 actualPayment = requiredPayment * paymentMultiplier;

        vm.deal(minter, actualPayment);

        // Perform mint
        vm.prank(minter);
        nft.mint{value: actualPayment}(author, quantity);

        // Verify minter received correct number of tokens
        assertEq(nft.balanceOf(minter), quantity);

        // Verify payment distribution
        uint256 authorShare = requiredPayment / 2;
        uint256 treasuryShare = requiredPayment - authorShare;

        // Overpayment goes to treasury
        if (actualPayment > requiredPayment) {
            treasuryShare += (actualPayment - requiredPayment);
        }

        assertEq(nft.authorClaimable(author), authorShare);
        assertEq(nft.treasuryBalance(), treasuryShare);

        // Verify balance conservation
        assertEq(address(nft).balance, actualPayment);
        assertEq(nft.authorClaimable(author) + nft.treasuryBalance(), actualPayment);
    }

    /**
     * @notice T119 - Fuzz test with insufficient payment (should revert)
     */
    function testFuzzMintInsufficientPayment(uint8 quantity, uint256 paymentPercentage) public {
        quantity = uint8(bound(quantity, 1, MAX_BATCH_SIZE));
        paymentPercentage = bound(paymentPercentage, 1, 99); // 1% to 99% of required

        address minter = makeAddr("minter");
        address author = makeAddr("author");

        uint256 requiredPayment = INITIAL_MINT_PRICE * quantity;
        uint256 insufficientPayment = (requiredPayment * paymentPercentage) / 100;

        vm.deal(minter, insufficientPayment);

        // Should revert with insufficient payment
        vm.prank(minter);
        vm.expectRevert(GliskNFT.InsufficientPayment.selector);
        nft.mint{value: insufficientPayment}(author, quantity);
    }

    /**
     * @notice T120 - Fuzz test payment distribution with various amounts
     * @dev Verifies 50/50 split is maintained across different payment amounts
     */
    function testFuzzPaymentDistribution(uint8 numMints, uint8 quantityPerMint) public {
        numMints = uint8(bound(numMints, 1, 20)); // 1 to 20 mints
        quantityPerMint = uint8(bound(quantityPerMint, 1, 10)); // 1 to 10 NFTs per mint

        address author = makeAddr("author");

        uint256 totalPaid = 0;
        uint256 expectedAuthorShare = 0;

        // Perform multiple mints
        for (uint256 i = 0; i < numMints; i++) {
            address minter = makeAddr(string(abi.encodePacked("minter", vm.toString(i))));
            uint256 payment = INITIAL_MINT_PRICE * quantityPerMint;

            vm.deal(minter, payment);
            vm.prank(minter);
            nft.mint{value: payment}(author, quantityPerMint);

            totalPaid += payment;
            expectedAuthorShare += payment / 2;
        }

        // Verify author received exactly 50% of all payments
        assertEq(nft.authorClaimable(author), expectedAuthorShare);

        // Verify treasury received remaining 50%
        uint256 expectedTreasuryShare = totalPaid - expectedAuthorShare;
        assertEq(nft.treasuryBalance(), expectedTreasuryShare);

        // Verify balance conservation
        assertEq(address(nft).balance, totalPaid);
        assertEq(nft.authorClaimable(author) + nft.treasuryBalance(), totalPaid);
    }

    /**
     * @notice T120 - Fuzz test overpayment handling
     */
    function testFuzzOverpaymentDistribution(uint8 quantity, uint256 overpaymentEth) public {
        quantity = uint8(bound(quantity, 1, MAX_BATCH_SIZE));
        overpaymentEth = bound(overpaymentEth, 0, 10 ether); // 0 to 10 ETH overpayment

        address minter = makeAddr("minter");
        address author = makeAddr("author");

        uint256 requiredPayment = INITIAL_MINT_PRICE * quantity;
        uint256 totalPayment = requiredPayment + overpaymentEth;

        vm.deal(minter, totalPayment);
        vm.prank(minter);
        nft.mint{value: totalPayment}(author, quantity);

        // Author gets 50% of base payment only
        uint256 authorShare = requiredPayment / 2;
        assertEq(nft.authorClaimable(author), authorShare);

        // Treasury gets remaining base + ALL overpayment
        uint256 treasuryShare = (requiredPayment - authorShare) + overpaymentEth;
        assertEq(nft.treasuryBalance(), treasuryShare);

        // Verify balance conservation
        assertEq(address(nft).balance, totalPayment);
        assertEq(nft.authorClaimable(author) + nft.treasuryBalance(), totalPayment);
    }

    /**
     * @notice T121 - Fuzz test batch reveal with various batch sizes
     */
    function testFuzzBatchReveal(uint8 mintQuantity, uint8 revealBatchSize) public {
        mintQuantity = uint8(bound(mintQuantity, 10, MAX_BATCH_SIZE));
        revealBatchSize = uint8(bound(revealBatchSize, 1, mintQuantity));

        address minter = makeAddr("minter");
        address author = makeAddr("author");

        // Mint tokens
        uint256 payment = INITIAL_MINT_PRICE * mintQuantity;
        vm.deal(minter, payment);
        vm.prank(minter);
        nft.mint{value: payment}(author, mintQuantity);

        // Prepare reveal batch
        uint256[] memory tokenIds = new uint256[](revealBatchSize);
        string[] memory uris = new string[](revealBatchSize);

        for (uint256 i = 0; i < revealBatchSize; i++) {
            tokenIds[i] = i + 1;
            uris[i] = string(abi.encodePacked("ipfs://Qm", vm.toString(i)));
        }

        // Reveal batch
        vm.prank(owner);
        nft.revealTokens(tokenIds, uris);

        // Verify revealed tokens
        for (uint256 i = 0; i < revealBatchSize; i++) {
            assertTrue(nft.isRevealed(tokenIds[i]));
            assertEq(nft.tokenURI(tokenIds[i]), uris[i]);
        }

        // Verify unrevealed tokens still show placeholder
        if (mintQuantity > revealBatchSize) {
            assertFalse(nft.isRevealed(revealBatchSize + 1));
            assertEq(nft.tokenURI(revealBatchSize + 1), PLACEHOLDER_URI);
        }
    }

    /**
     * @notice T121 - Fuzz test reveal with mismatched array lengths (should revert)
     */
    function testFuzzRevealLengthMismatch(uint8 tokenIdsLength, uint8 urisLength) public {
        tokenIdsLength = uint8(bound(tokenIdsLength, 1, 20));
        urisLength = uint8(bound(urisLength, 1, 20));

        // Only test when lengths differ
        vm.assume(tokenIdsLength != urisLength);

        // Mint some tokens first
        address minter = makeAddr("minter");
        address author = makeAddr("author");
        uint256 payment = INITIAL_MINT_PRICE * 20;
        vm.deal(minter, payment);
        vm.prank(minter);
        nft.mint{value: payment}(author, 20);

        // Create mismatched arrays
        uint256[] memory tokenIds = new uint256[](tokenIdsLength);
        string[] memory uris = new string[](urisLength);

        for (uint256 i = 0; i < tokenIdsLength; i++) {
            tokenIds[i] = i + 1;
        }
        for (uint256 i = 0; i < urisLength; i++) {
            uris[i] = string(abi.encodePacked("ipfs://Qm", vm.toString(i)));
        }

        // Should revert with length mismatch
        vm.prank(owner);
        vm.expectRevert(GliskNFT.LengthMismatch.selector);
        nft.revealTokens(tokenIds, uris);
    }

    /**
     * @notice Fuzz test multiple authors accumulating rewards independently
     */
    function testFuzzMultipleAuthorsAccumulation(uint8 numAuthors, uint8 mintsPerAuthor) public {
        numAuthors = uint8(bound(numAuthors, 2, 10));
        mintsPerAuthor = uint8(bound(mintsPerAuthor, 1, 5));

        uint256 totalContractBalance = 0;
        uint256 totalAuthorExpected = 0;

        // Create authors and perform mints
        for (uint256 i = 0; i < numAuthors; i++) {
            address author = makeAddr(string(abi.encodePacked("author", vm.toString(i))));
            uint256 authorTotal = 0;

            for (uint256 j = 0; j < mintsPerAuthor; j++) {
                address minter = makeAddr(string(abi.encodePacked("minter", vm.toString(i), vm.toString(j))));
                uint256 payment = INITIAL_MINT_PRICE * (j + 1); // Vary quantity

                vm.deal(minter, payment);
                vm.prank(minter);
                nft.mint{value: payment}(author, j + 1);

                authorTotal += payment / 2;
                totalContractBalance += payment;
            }

            // Verify this author's balance immediately
            assertEq(nft.authorClaimable(author), authorTotal);
            totalAuthorExpected += authorTotal;
        }

        // Verify contract balance conservation
        uint256 expectedTreasury = totalContractBalance - totalAuthorExpected;
        assertEq(nft.treasuryBalance(), expectedTreasury);
        assertEq(address(nft).balance, totalContractBalance);
    }

    /**
     * @notice Fuzz test price updates with various values
     */
    function testFuzzPriceUpdate(uint256 newPrice) public {
        newPrice = bound(newPrice, 0.0001 ether, 1 ether); // 0.0001 to 1 ETH

        // Owner updates price
        vm.prank(owner);
        nft.setMintPrice(newPrice);

        assertEq(nft.mintPrice(), newPrice);

        // Verify minting works with new price
        address minter = makeAddr("minter");
        address author = makeAddr("author");
        uint256 quantity = 5;
        uint256 payment = newPrice * quantity;

        vm.deal(minter, payment);
        vm.prank(minter);
        nft.mint{value: payment}(author, quantity);

        assertEq(nft.balanceOf(minter), quantity);
    }

    /**
     * @notice Fuzz test author claim with various accumulated amounts
     */
    function testFuzzAuthorClaim(uint8 numMints, uint8 quantityPerMint) public {
        numMints = uint8(bound(numMints, 1, 20));
        quantityPerMint = uint8(bound(quantityPerMint, 1, 10));

        address author = makeAddr("author");
        uint256 expectedClaimable = 0;

        // Accumulate balance through multiple mints
        for (uint256 i = 0; i < numMints; i++) {
            address minter = makeAddr(string(abi.encodePacked("minter", vm.toString(i))));
            uint256 payment = INITIAL_MINT_PRICE * quantityPerMint;

            vm.deal(minter, payment);
            vm.prank(minter);
            nft.mint{value: payment}(author, quantityPerMint);

            expectedClaimable += payment / 2;
        }

        // Verify accumulated balance
        assertEq(nft.authorClaimable(author), expectedClaimable);

        // Claim rewards
        uint256 authorBalanceBefore = author.balance;
        vm.prank(author);
        nft.claimAuthorRewards();

        // Verify transfer and reset
        assertEq(author.balance, authorBalanceBefore + expectedClaimable);
        assertEq(nft.authorClaimable(author), 0);
    }

    /**
     * @notice Fuzz test sweep after season end with various author counts
     */
    function testFuzzSeasonSweep(uint8 numAuthors) public {
        numAuthors = uint8(bound(numAuthors, 1, 20));

        uint256 totalUnclaimedBefore = 0;

        // Mint for multiple authors
        address[] memory authors = new address[](numAuthors);
        for (uint256 i = 0; i < numAuthors; i++) {
            address author = makeAddr(string(abi.encodePacked("author", vm.toString(i))));
            authors[i] = author;

            address minter = makeAddr(string(abi.encodePacked("minter", vm.toString(i))));
            uint256 payment = INITIAL_MINT_PRICE * 5;

            vm.deal(minter, payment);
            vm.prank(minter);
            nft.mint{value: payment}(author, 5);

            totalUnclaimedBefore += nft.authorClaimable(author);
        }

        // End season
        vm.prank(owner);
        nft.endSeason();

        // Fast forward past protection period
        vm.warp(block.timestamp + 14 days + 1);

        // Sweep all authors
        uint256 treasuryBefore = nft.treasuryBalance();
        vm.prank(owner);
        nft.sweepUnclaimedRewards(authors);

        // Verify all balances swept to treasury
        for (uint256 i = 0; i < numAuthors; i++) {
            assertEq(nft.authorClaimable(authors[i]), 0);
        }

        assertEq(nft.treasuryBalance(), treasuryBefore + totalUnclaimedBefore);
    }

    /**
     * @notice Fuzz test direct payments to contract
     */
    function testFuzzDirectPayment(uint256 paymentAmount) public {
        paymentAmount = bound(paymentAmount, 0.001 ether, 10 ether);

        uint256 treasuryBefore = nft.treasuryBalance();

        address payer = makeAddr("payer");
        vm.deal(payer, paymentAmount);

        vm.prank(payer);
        (bool success,) = address(nft).call{value: paymentAmount}("");
        assertTrue(success);

        assertEq(nft.treasuryBalance(), treasuryBefore + paymentAmount);
        assertEq(address(nft).balance, treasuryBefore + paymentAmount);
    }
}
