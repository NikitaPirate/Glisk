// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../../src/GliskNFT.sol";

/**
 * @title GliskNFT Enumerable Tests
 * @notice Unit tests for ERC721Enumerable functionality
 * @dev Tests totalSupply, tokenByIndex, and tokenOfOwnerByIndex functions
 */
contract GliskNFTEnumerableTest is Test {
    GliskNFT public nft;

    address public owner;
    address public user1;
    address public user2;
    address public user3;
    address public promptAuthor;

    string constant NAME = "GLISK Season 0";
    string constant SYMBOL = "GLISK0";
    string constant PLACEHOLDER_URI = "ipfs://placeholder";
    uint256 constant INITIAL_MINT_PRICE = 0.00001 ether;

    function setUp() public {
        owner = address(this);
        user1 = makeAddr("user1");
        user2 = makeAddr("user2");
        user3 = makeAddr("user3");
        promptAuthor = makeAddr("promptAuthor");

        // Deploy contract
        nft = new GliskNFT(NAME, SYMBOL, PLACEHOLDER_URI, INITIAL_MINT_PRICE);

        // Fund test users
        vm.deal(user1, 10 ether);
        vm.deal(user2, 10 ether);
        vm.deal(user3, 10 ether);
    }

    // ============================================
    // totalSupply() Tests
    // ============================================

    /// @notice Test: totalSupply is 0 on deployment
    function testTotalSupplyStartsAtZero() public view {
        assertEq(nft.totalSupply(), 0, "Total supply should start at 0");
    }

    /// @notice Test: totalSupply increases by 1 after single mint
    function testTotalSupplyIncrementsAfterSingleMint() public {
        uint256 initialSupply = nft.totalSupply();

        vm.prank(user1);
        nft.mint{value: INITIAL_MINT_PRICE}(promptAuthor, 1);

        assertEq(nft.totalSupply(), initialSupply + 1, "Total supply should increase by 1");
        assertEq(nft.totalSupply(), 1, "Total supply should be 1");
    }

    /// @notice Test: totalSupply increases by batch quantity after batch mint
    function testTotalSupplyIncrementsAfterBatchMint() public {
        uint256 quantity = 5;
        uint256 initialSupply = nft.totalSupply();

        vm.prank(user1);
        nft.mint{value: INITIAL_MINT_PRICE * quantity}(promptAuthor, quantity);

        assertEq(nft.totalSupply(), initialSupply + quantity, "Total supply should increase by quantity");
        assertEq(nft.totalSupply(), quantity, "Total supply should equal minted quantity");
    }

    /// @notice Test: totalSupply tracks total across multiple users
    function testTotalSupplyAcrossMultipleUsers() public {
        // User1 mints 3 tokens
        vm.prank(user1);
        nft.mint{value: INITIAL_MINT_PRICE * 3}(promptAuthor, 3);
        assertEq(nft.totalSupply(), 3, "Total supply should be 3 after first mint");

        // User2 mints 2 tokens
        vm.prank(user2);
        nft.mint{value: INITIAL_MINT_PRICE * 2}(promptAuthor, 2);
        assertEq(nft.totalSupply(), 5, "Total supply should be 5 after second mint");

        // User3 mints 1 token
        vm.prank(user3);
        nft.mint{value: INITIAL_MINT_PRICE * 1}(promptAuthor, 1);
        assertEq(nft.totalSupply(), 6, "Total supply should be 6 after third mint");
    }

    /// @notice Test: totalSupply equals nextTokenId - 1
    function testTotalSupplyMatchesNextTokenId() public {
        uint256 quantity = 10;

        vm.prank(user1);
        nft.mint{value: INITIAL_MINT_PRICE * quantity}(promptAuthor, quantity);

        // nextTokenId is the next token to be minted (starts at 1)
        // totalSupply is the count of minted tokens
        // So: totalSupply = nextTokenId - 1
        assertEq(nft.totalSupply(), nft.nextTokenId() - 1, "totalSupply should equal nextTokenId - 1");
    }

    // ============================================
    // tokenByIndex() Tests
    // ============================================

    /// @notice Test: tokenByIndex returns correct token IDs for sequential mints
    function testTokenByIndexSequentialMints() public {
        uint256 quantity = 5;

        vm.prank(user1);
        nft.mint{value: INITIAL_MINT_PRICE * quantity}(promptAuthor, quantity);

        // Token IDs start at 1
        for (uint256 i = 0; i < quantity; i++) {
            uint256 tokenId = nft.tokenByIndex(i);
            assertEq(tokenId, i + 1, "Token ID should be sequential starting from 1");
        }
    }

    /// @notice Test: tokenByIndex reverts when index >= totalSupply
    function testTokenByIndexRevertsOnOutOfBounds() public {
        // Mint 3 tokens
        vm.prank(user1);
        nft.mint{value: INITIAL_MINT_PRICE * 3}(promptAuthor, 3);

        // Valid indices: 0, 1, 2
        nft.tokenByIndex(0);
        nft.tokenByIndex(1);
        nft.tokenByIndex(2);

        // Index 3 should revert
        vm.expectRevert();
        nft.tokenByIndex(3);
    }

    /// @notice Test: tokenByIndex works with maximum batch size
    function testTokenByIndexMaxBatchSize() public {
        uint256 maxBatch = 50; // MAX_BATCH_SIZE

        vm.prank(user1);
        nft.mint{value: INITIAL_MINT_PRICE * maxBatch}(promptAuthor, maxBatch);

        assertEq(nft.totalSupply(), maxBatch, "Total supply should be max batch size");

        // Check first and last tokens
        assertEq(nft.tokenByIndex(0), 1, "First token should be ID 1");
        assertEq(nft.tokenByIndex(maxBatch - 1), maxBatch, "Last token should be ID maxBatch");
    }

    // ============================================
    // tokenOfOwnerByIndex() Tests
    // ============================================

    /// @notice Test: tokenOfOwnerByIndex returns correct tokens for single owner
    function testTokenOfOwnerByIndexSingleOwner() public {
        uint256 quantity = 3;

        vm.prank(user1);
        nft.mint{value: INITIAL_MINT_PRICE * quantity}(promptAuthor, quantity);

        assertEq(nft.balanceOf(user1), quantity, "User1 should own 3 tokens");

        // Check owner's tokens by index
        for (uint256 i = 0; i < quantity; i++) {
            uint256 tokenId = nft.tokenOfOwnerByIndex(user1, i);
            assertEq(nft.ownerOf(tokenId), user1, "Token should belong to user1");
        }
    }

    /// @notice Test: tokenOfOwnerByIndex correctly tracks different owners
    function testTokenOfOwnerByIndexMultipleOwners() public {
        // User1 mints 2 tokens (IDs: 1, 2)
        vm.prank(user1);
        nft.mint{value: INITIAL_MINT_PRICE * 2}(promptAuthor, 2);

        // User2 mints 3 tokens (IDs: 3, 4, 5)
        vm.prank(user2);
        nft.mint{value: INITIAL_MINT_PRICE * 3}(promptAuthor, 3);

        // User3 mints 1 token (ID: 6)
        vm.prank(user3);
        nft.mint{value: INITIAL_MINT_PRICE * 1}(promptAuthor, 1);

        // Verify user1's tokens
        assertEq(nft.balanceOf(user1), 2, "User1 should own 2 tokens");
        uint256 user1Token0 = nft.tokenOfOwnerByIndex(user1, 0);
        uint256 user1Token1 = nft.tokenOfOwnerByIndex(user1, 1);
        assertEq(nft.ownerOf(user1Token0), user1, "First token should belong to user1");
        assertEq(nft.ownerOf(user1Token1), user1, "Second token should belong to user1");

        // Verify user2's tokens
        assertEq(nft.balanceOf(user2), 3, "User2 should own 3 tokens");
        for (uint256 i = 0; i < 3; i++) {
            uint256 tokenId = nft.tokenOfOwnerByIndex(user2, i);
            assertEq(nft.ownerOf(tokenId), user2, "Token should belong to user2");
        }

        // Verify user3's token
        assertEq(nft.balanceOf(user3), 1, "User3 should own 1 token");
        uint256 user3Token0 = nft.tokenOfOwnerByIndex(user3, 0);
        assertEq(nft.ownerOf(user3Token0), user3, "Token should belong to user3");
    }

    /// @notice Test: tokenOfOwnerByIndex reverts when index >= owner's balance
    function testTokenOfOwnerByIndexRevertsOnOutOfBounds() public {
        // User1 mints 2 tokens
        vm.prank(user1);
        nft.mint{value: INITIAL_MINT_PRICE * 2}(promptAuthor, 2);

        // Valid indices: 0, 1
        nft.tokenOfOwnerByIndex(user1, 0);
        nft.tokenOfOwnerByIndex(user1, 1);

        // Index 2 should revert
        vm.expectRevert();
        nft.tokenOfOwnerByIndex(user1, 2);
    }

    /// @notice Test: tokenOfOwnerByIndex updates correctly after transfer
    function testTokenOfOwnerByIndexAfterTransfer() public {
        // User1 mints 3 tokens
        vm.prank(user1);
        nft.mint{value: INITIAL_MINT_PRICE * 3}(promptAuthor, 3);

        assertEq(nft.balanceOf(user1), 3, "User1 should own 3 tokens before transfer");
        assertEq(nft.balanceOf(user2), 0, "User2 should own 0 tokens before transfer");

        // Get first token ID
        uint256 tokenToTransfer = nft.tokenOfOwnerByIndex(user1, 0);

        // User1 transfers token to user2
        vm.prank(user1);
        nft.transferFrom(user1, user2, tokenToTransfer);

        // Verify balances updated
        assertEq(nft.balanceOf(user1), 2, "User1 should own 2 tokens after transfer");
        assertEq(nft.balanceOf(user2), 1, "User2 should own 1 token after transfer");

        // Verify user2 owns the transferred token
        uint256 user2Token0 = nft.tokenOfOwnerByIndex(user2, 0);
        assertEq(user2Token0, tokenToTransfer, "User2's token should be the transferred token");
        assertEq(nft.ownerOf(user2Token0), user2, "Transferred token should belong to user2");

        // Verify user1 still owns remaining tokens
        for (uint256 i = 0; i < 2; i++) {
            uint256 tokenId = nft.tokenOfOwnerByIndex(user1, i);
            assertEq(nft.ownerOf(tokenId), user1, "Remaining tokens should belong to user1");
        }
    }

    // ============================================
    // Integration Tests
    // ============================================

    /// @notice Test: Enumerate all tokens in the contract
    function testEnumerateAllTokens() public {
        uint256 totalMinted = 10;

        vm.prank(user1);
        nft.mint{value: INITIAL_MINT_PRICE * totalMinted}(promptAuthor, totalMinted);

        // Enumerate all tokens
        uint256[] memory allTokens = new uint256[](totalMinted);
        for (uint256 i = 0; i < totalMinted; i++) {
            allTokens[i] = nft.tokenByIndex(i);
        }

        // Verify all token IDs are sequential and unique
        for (uint256 i = 0; i < totalMinted; i++) {
            assertEq(allTokens[i], i + 1, "Token IDs should be sequential starting from 1");

            // Verify uniqueness (no duplicates)
            for (uint256 j = i + 1; j < totalMinted; j++) {
                assertTrue(allTokens[i] != allTokens[j], "Token IDs should be unique");
            }
        }
    }

    /// @notice Test: supportsInterface returns true for IERC721Enumerable
    function testSupportsEnumerableInterface() public view {
        // IERC721Enumerable interface ID: 0x780e9d63
        bytes4 enumerableInterfaceId = 0x780e9d63;
        assertTrue(nft.supportsInterface(enumerableInterfaceId), "Contract should support IERC721Enumerable");
    }

    /// @notice Test: Gas cost comparison for batch minting
    /// @dev Documents gas increase with Enumerable (for documentation purposes)
    function testGasCostBatchMint() public {
        uint256 quantity = 5;

        uint256 gasBefore = gasleft();
        vm.prank(user1);
        nft.mint{value: INITIAL_MINT_PRICE * quantity}(promptAuthor, quantity);
        uint256 gasUsed = gasBefore - gasleft();

        // Log gas used (for manual inspection during testing)
        emit log_named_uint("Gas used for 5-token batch mint with Enumerable", gasUsed);

        // Verify mint succeeded
        assertEq(nft.totalSupply(), quantity, "Batch mint should succeed");
    }
}
