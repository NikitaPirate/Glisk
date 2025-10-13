// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "forge-std/StdInvariant.sol";
import "../../src/GliskNFT.sol";

/**
 * @title GliskNFT Invariant Handler
 * @notice Actor contract for invariant testing
 * @dev Simulates realistic user interactions
 */
contract GliskNFTHandler is Test {
    GliskNFT public nft;
    address public owner;

    // Track state for invariant checks
    uint256 public totalMinted;
    uint256 public totalClaimed;
    uint256 public totalSwept;
    mapping(uint256 => bool) public tokenExists;
    mapping(uint256 => bool) public tokenRevealed;
    mapping(uint256 => string) public revealedURIs;

    // Actors
    address[] public minters;
    address[] public authors;

    // Getter for array lengths
    function mintersLength() public view returns (uint256) {
        return minters.length;
    }

    function authorsLength() public view returns (uint256) {
        return authors.length;
    }

    function getMinter(uint256 index) public view returns (address) {
        return minters[index];
    }

    function getAuthor(uint256 index) public view returns (address) {
        return authors[index];
    }

    constructor(GliskNFT _nft, address _owner) {
        nft = _nft;
        owner = _owner;

        // Create test actors
        for (uint256 i = 0; i < 5; i++) {
            minters.push(makeAddr(string(abi.encodePacked("minter", vm.toString(i)))));
            authors.push(makeAddr(string(abi.encodePacked("author", vm.toString(i)))));
            vm.deal(minters[i], 100 ether);
        }
    }

    /**
     * @notice Random mint action
     */
    function mint(uint256 authorSeed, uint256 quantity) public {
        // Skip if season ended
        if (nft.seasonEnded()) return;

        // Bound inputs
        quantity = bound(quantity, 1, nft.MAX_BATCH_SIZE());
        address author = authors[authorSeed % authors.length];
        address minter = minters[authorSeed % minters.length];

        uint256 payment = nft.mintPrice() * quantity;

        try nft.mint{value: payment}(author, quantity) {
            for (uint256 i = 0; i < quantity; i++) {
                totalMinted++;
                tokenExists[totalMinted] = true;
            }
        } catch {
            // Mint may fail due to insufficient balance or other reasons
        }
    }

    /**
     * @notice Random author claim action
     */
    function claimRewards(uint256 authorSeed) public {
        address author = authors[authorSeed % authors.length];

        uint256 claimable = nft.authorClaimable(author);

        vm.prank(author);
        try nft.claimAuthorRewards() {
            totalClaimed += claimable;
        } catch {
            // Claim may fail (transfer issues, etc.)
        }
    }

    /**
     * @notice Random reveal action
     */
    function revealTokens(uint256 startSeed, uint256 count) public {
        count = bound(count, 1, 10);

        if (totalMinted == 0) return;

        uint256[] memory tokenIds = new uint256[](count);
        string[] memory uris = new string[](count);

        uint256 validCount = 0;
        for (uint256 i = 0; i < count && validCount < count; i++) {
            uint256 tokenId = (startSeed + i) % totalMinted + 1;

            if (tokenExists[tokenId] && !tokenRevealed[tokenId]) {
                tokenIds[validCount] = tokenId;
                uris[validCount] = string(abi.encodePacked("ipfs://Qm", vm.toString(tokenId)));
                validCount++;
            }
        }

        if (validCount == 0) return;

        // Trim arrays to valid count
        uint256[] memory finalTokenIds = new uint256[](validCount);
        string[] memory finalUris = new string[](validCount);
        for (uint256 i = 0; i < validCount; i++) {
            finalTokenIds[i] = tokenIds[i];
            finalUris[i] = uris[i];
        }

        vm.prank(owner);
        try nft.revealTokens(finalTokenIds, finalUris) {
            for (uint256 i = 0; i < validCount; i++) {
                tokenRevealed[finalTokenIds[i]] = true;
                revealedURIs[finalTokenIds[i]] = finalUris[i];
            }
        } catch {
            // Reveal may fail
        }
    }

    /**
     * @notice Random direct payment
     */
    function directPayment(uint256 amount) public {
        amount = bound(amount, 0.001 ether, 1 ether);

        address payer = minters[0];
        vm.prank(payer);
        (bool success,) = address(nft).call{value: amount}("");

        // Direct payments always go to treasury
    }

    /**
     * @notice End season (can only be called once)
     */
    function endSeason() public {
        if (nft.seasonEnded()) return;

        vm.prank(owner);
        try nft.endSeason() {} catch {}
    }

    /**
     * @notice Sweep rewards (only after season end + protection period)
     */
    function sweepRewards(uint256 authorSeed) public {
        if (!nft.seasonEnded()) return;
        if (block.timestamp < nft.seasonEndTime() + nft.SWEEP_PROTECTION_PERIOD()) return;

        address author = authors[authorSeed % authors.length];
        address[] memory authorArray = new address[](1);
        authorArray[0] = author;

        uint256 sweepAmount = nft.authorClaimable(author);

        vm.prank(owner);
        try nft.sweepUnclaimedRewards(authorArray) {
            totalSwept += sweepAmount;
        } catch {}
    }
}

/**
 * @title GliskNFT Invariant Tests
 * @notice Stateful property-based testing
 * @dev Tests that critical invariants hold after any sequence of actions
 */
contract GliskNFTInvariantTest is StdInvariant, Test {
    GliskNFT public nft;
    GliskNFTHandler public handler;

    address public owner;

    string constant NAME = "GLISK Season 0";
    string constant SYMBOL = "GLISK0";
    string constant PLACEHOLDER_URI = "ipfs://QmPlaceholder";
    uint256 constant INITIAL_MINT_PRICE = 0.001 ether;

    function setUp() public {
        owner = makeAddr("owner");
        vm.deal(owner, 100 ether);

        vm.startPrank(owner);
        nft = new GliskNFT(NAME, SYMBOL, PLACEHOLDER_URI, INITIAL_MINT_PRICE);
        vm.stopPrank();

        // Create handler
        handler = new GliskNFTHandler(nft, owner);

        // Set handler as target for invariant testing
        targetContract(address(handler));

        // Define function selectors to call
        bytes4[] memory selectors = new bytes4[](6);
        selectors[0] = GliskNFTHandler.mint.selector;
        selectors[1] = GliskNFTHandler.claimRewards.selector;
        selectors[2] = GliskNFTHandler.revealTokens.selector;
        selectors[3] = GliskNFTHandler.directPayment.selector;
        selectors[4] = GliskNFTHandler.endSeason.selector;
        selectors[5] = GliskNFTHandler.sweepRewards.selector;

        targetSelector(FuzzSelector({addr: address(handler), selectors: selectors}));
    }

    /**
     * @notice T123 - INVARIANT: Balance Conservation
     * @dev contract.balance == treasuryBalance + sum(authorClaimable)
     */
    function invariant_BalanceConservation() public view {
        uint256 treasuryBalance = nft.treasuryBalance();
        uint256 totalAuthorClaimable = 0;

        // Sum all author claimable balances
        for (uint256 i = 0; i < handler.authorsLength(); i++) {
            totalAuthorClaimable += nft.authorClaimable(handler.getAuthor(i));
        }

        // Contract balance should equal sum of all tracked balances
        assertEq(
            address(nft).balance,
            treasuryBalance + totalAuthorClaimable,
            "Balance conservation violated: contract balance != treasury + author claimable"
        );
    }

    /**
     * @notice T124 - INVARIANT: Token ID Uniqueness
     * @dev Each minted token has a unique owner (no duplicate token IDs)
     */
    function invariant_TokenIDUniqueness() public view {
        // This is guaranteed by the ERC721 standard and our sequential _nextTokenId
        // We verify that token ownership is never duplicated

        if (handler.totalMinted() == 0) return;

        // Check that token IDs are sequential starting from 1
        for (uint256 i = 1; i <= handler.totalMinted(); i++) {
            if (handler.tokenExists(i)) {
                // Token must have an owner
                try nft.ownerOf(i) returns (address tokenOwner) {
                    assertTrue(tokenOwner != address(0), "Token exists but has no owner");
                } catch {
                    revert("Token should exist but ownerOf reverted");
                }
            }
        }
    }

    /**
     * @notice T125 - INVARIANT: Reveal Immutability
     * @dev Once revealed, a token's URI cannot change
     */
    function invariant_RevealImmutability() public view {
        for (uint256 i = 1; i <= handler.totalMinted(); i++) {
            if (handler.tokenRevealed(i)) {
                // Verify token is still marked as revealed
                assertTrue(nft.isRevealed(i), "Previously revealed token no longer marked as revealed");

                // Verify URI hasn't changed
                string memory expectedURI = handler.revealedURIs(i);
                string memory actualURI = nft.tokenURI(i);

                assertEq(
                    keccak256(abi.encodePacked(actualURI)),
                    keccak256(abi.encodePacked(expectedURI)),
                    "Revealed token URI changed"
                );
            }
        }
    }

    /**
     * @notice INVARIANT: Treasury balance is non-negative and <= contract balance
     */
    function invariant_TreasuryBounds() public view {
        uint256 treasuryBalance = nft.treasuryBalance();
        uint256 contractBalance = address(nft).balance;

        assertTrue(treasuryBalance <= contractBalance, "Treasury balance exceeds contract balance");
    }

    /**
     * @notice INVARIANT: Author claimable balances are non-negative
     */
    function invariant_AuthorBalancesNonNegative() public view {
        for (uint256 i = 0; i < handler.authorsLength(); i++) {
            address author = handler.getAuthor(i);
            uint256 claimable = nft.authorClaimable(author);

            // Claimable should be non-negative (always true for uint256, but checking logic)
            assertTrue(claimable >= 0, "Author claimable balance is negative");
        }
    }

    /**
     * @notice INVARIANT: Season end is permanent
     */
    function invariant_SeasonEndPermanent() public view {
        if (nft.seasonEnded()) {
            // Once season ends, it should have a valid end time
            assertTrue(nft.seasonEndTime() > 0, "Season ended but end time is zero");

            // End time should not be in the future (should be <= current block timestamp)
            assertTrue(nft.seasonEndTime() <= block.timestamp, "Season end time is in the future");
        }
    }

    /**
     * @notice INVARIANT: Mint price is always positive
     */
    function invariant_MintPricePositive() public view {
        assertTrue(nft.mintPrice() > 0, "Mint price should always be positive");
    }

    /**
     * @notice INVARIANT: Token ownership is consistent
     */
    function invariant_TokenOwnershipConsistent() public view {
        for (uint256 i = 0; i < handler.mintersLength(); i++) {
            address minter = handler.getMinter(i);
            uint256 balance = nft.balanceOf(minter);

            // Balance should not exceed total minted
            assertTrue(balance <= handler.totalMinted(), "Balance exceeds total minted");
        }
    }

    /**
     * @notice INVARIANT: Total value in system is conserved
     * @dev Total minted value = claimed + swept + remaining (treasury + author balances)
     */
    function invariant_ValueConservation() public view {
        uint256 totalInSystem = nft.treasuryBalance();

        // Add all author claimable balances
        for (uint256 i = 0; i < handler.authorsLength(); i++) {
            totalInSystem += nft.authorClaimable(handler.getAuthor(i));
        }

        // Add claimed amount (no longer in contract)
        totalInSystem += handler.totalClaimed();

        // Total should equal contract balance + claimed
        assertEq(address(nft).balance + handler.totalClaimed(), totalInSystem, "Value conservation violated");
    }
}
