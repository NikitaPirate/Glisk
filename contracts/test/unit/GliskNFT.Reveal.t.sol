// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../../src/GliskNFT.sol";

/**
 * @title GliskNFT Reveal Tests
 * @notice Unit tests for User Story 8: NFT Reveal and Metadata Update
 * @dev Tests the reveal workflow from placeholder to permanent URIs
 */
contract GliskNFTRevealTest is Test {
    GliskNFT public nft;

    address public owner;
    address public keeper;
    address public author;
    address public minter;
    address public unauthorized;

    string constant PLACEHOLDER_URI = "ipfs://QmPlaceholder/metadata.json";
    string constant NEW_PLACEHOLDER_URI = "ipfs://QmNewPlaceholder/metadata.json";
    uint256 constant INITIAL_PRICE = 0.01 ether;

    event PlaceholderURIUpdated(string newURI);
    event TokensRevealed(uint256[] tokenIds);

    function setUp() public {
        owner = makeAddr("owner");
        keeper = makeAddr("keeper");
        author = makeAddr("author");
        minter = makeAddr("minter");
        unauthorized = makeAddr("unauthorized");

        vm.prank(owner);
        nft = new GliskNFT("GLISK Season 0", "GLISK0", PLACEHOLDER_URI, INITIAL_PRICE);

        // Grant keeper role
        bytes32 keeperRole = nft.KEEPER_ROLE(); // Read role constant first
        vm.prank(owner);
        nft.grantRole(keeperRole, keeper);

        // Fund minter
        vm.deal(minter, 100 ether);
    }

    /**
     * @notice Helper function to mint tokens for testing
     */
    function mintTokens(uint256 quantity) internal returns (uint256 startTokenId) {
        vm.prank(minter);
        nft.mint{value: INITIAL_PRICE * quantity}(author, quantity);
        return 1; // Token IDs start at 1
    }

    /**
     * @notice Test that unrevealed tokens return placeholder URI
     * @dev T039: New token returns placeholder URI
     */
    function testTokenURIUnrevealed() public {
        // Mint a token
        uint256 tokenId = mintTokens(1);

        // Check token URI returns placeholder
        string memory uri = nft.tokenURI(tokenId);
        assertEq(uri, PLACEHOLDER_URI, "Unrevealed token should return placeholder URI");
    }

    /**
     * @notice Test that owner can update placeholder URI
     * @dev T040: Owner updates placeholder, unrevealed tokens reflect change
     */
    function testUpdatePlaceholderURI() public {
        // Mint tokens
        uint256 token1 = mintTokens(1);
        uint256 token2 = mintTokens(1);

        // Verify initial placeholder
        assertEq(nft.tokenURI(token1), PLACEHOLDER_URI, "Should have initial placeholder");
        assertEq(nft.tokenURI(token2), PLACEHOLDER_URI, "Should have initial placeholder");

        // Owner updates placeholder
        vm.expectEmit(true, true, true, true);
        emit PlaceholderURIUpdated(NEW_PLACEHOLDER_URI);

        vm.prank(owner);
        nft.setPlaceholderURI(NEW_PLACEHOLDER_URI);

        // Both unrevealed tokens should reflect new placeholder
        assertEq(nft.tokenURI(token1), NEW_PLACEHOLDER_URI, "Should have new placeholder");
        assertEq(nft.tokenURI(token2), NEW_PLACEHOLDER_URI, "Should have new placeholder");
    }

    /**
     * @notice Test that owner/keeper can reveal tokens with unique URIs
     * @dev T041: Owner/Keeper reveals batch of tokens with unique URIs
     */
    function testRevealTokens() public {
        // Mint tokens
        uint256 token1 = 1;
        uint256 token2 = 2;
        uint256 token3 = 3;
        mintTokens(3);

        // Prepare reveal data
        uint256[] memory tokenIds = new uint256[](3);
        tokenIds[0] = token1;
        tokenIds[1] = token2;
        tokenIds[2] = token3;

        string[] memory uris = new string[](3);
        uris[0] = "ipfs://QmToken1/metadata.json";
        uris[1] = "ipfs://QmToken2/metadata.json";
        uris[2] = "ipfs://QmToken3/metadata.json";

        // Owner reveals tokens
        vm.expectEmit(true, true, true, true);
        emit TokensRevealed(tokenIds);

        vm.prank(owner);
        nft.revealTokens(tokenIds, uris);

        // Verify revealed URIs
        assertEq(nft.tokenURI(token1), uris[0], "Token 1 should have revealed URI");
        assertEq(nft.tokenURI(token2), uris[1], "Token 2 should have revealed URI");
        assertEq(nft.tokenURI(token3), uris[2], "Token 3 should have revealed URI");

        // Verify revealed status
        assertTrue(nft.isRevealed(token1), "Token 1 should be revealed");
        assertTrue(nft.isRevealed(token2), "Token 2 should be revealed");
        assertTrue(nft.isRevealed(token3), "Token 3 should be revealed");
    }

    /**
     * @notice Test that revealed tokens cannot be changed again
     * @dev T042: Attempting to re-reveal token reverts
     */
    function testRevealedTokenImmutable() public {
        // Mint and reveal a token
        uint256 tokenId = mintTokens(1);

        uint256[] memory tokenIds = new uint256[](1);
        tokenIds[0] = tokenId;

        string[] memory uris = new string[](1);
        uris[0] = "ipfs://QmOriginal/metadata.json";

        vm.prank(owner);
        nft.revealTokens(tokenIds, uris);

        // Verify token is revealed
        assertTrue(nft.isRevealed(tokenId), "Token should be revealed");
        assertEq(nft.tokenURI(tokenId), uris[0], "Token should have original URI");

        // Attempt to reveal again with different URI
        string[] memory newUris = new string[](1);
        newUris[0] = "ipfs://QmDifferent/metadata.json";

        vm.prank(owner);
        vm.expectRevert(abi.encodeWithSelector(GliskNFT.AlreadyRevealed.selector, tokenId));
        nft.revealTokens(tokenIds, newUris);

        // Verify URI unchanged
        assertEq(nft.tokenURI(tokenId), uris[0], "URI should remain unchanged");
    }

    /**
     * @notice Test that mismatched array lengths revert
     * @dev T043: Mismatched array lengths revert
     */
    function testRevealLengthMismatch() public {
        // Mint tokens
        mintTokens(3);

        // Create mismatched arrays
        uint256[] memory tokenIds = new uint256[](3);
        tokenIds[0] = 1;
        tokenIds[1] = 2;
        tokenIds[2] = 3;

        string[] memory uris = new string[](2); // Wrong length!
        uris[0] = "ipfs://QmToken1/metadata.json";
        uris[1] = "ipfs://QmToken2/metadata.json";

        // Attempt to reveal should revert
        vm.prank(owner);
        vm.expectRevert(GliskNFT.LengthMismatch.selector);
        nft.revealTokens(tokenIds, uris);
    }

    /**
     * @notice Test isRevealed() returns correct status
     * @dev T044: isRevealed() returns correct status
     */
    function testIsRevealed() public {
        // Mint tokens
        uint256 token1 = 1;
        uint256 token2 = 2;
        mintTokens(2);

        // Both should be unrevealed initially
        assertFalse(nft.isRevealed(token1), "Token 1 should be unrevealed");
        assertFalse(nft.isRevealed(token2), "Token 2 should be unrevealed");

        // Reveal token 1
        uint256[] memory tokenIds = new uint256[](1);
        tokenIds[0] = token1;

        string[] memory uris = new string[](1);
        uris[0] = "ipfs://QmToken1/metadata.json";

        vm.prank(owner);
        nft.revealTokens(tokenIds, uris);

        // Token 1 should be revealed, token 2 should not
        assertTrue(nft.isRevealed(token1), "Token 1 should be revealed");
        assertFalse(nft.isRevealed(token2), "Token 2 should still be unrevealed");
    }

    /**
     * @notice Test that keeper role can reveal tokens
     * @dev T045: Keeper role can reveal tokens
     */
    function testKeeperCanReveal() public {
        // Mint tokens
        uint256 tokenId = mintTokens(1);

        uint256[] memory tokenIds = new uint256[](1);
        tokenIds[0] = tokenId;

        string[] memory uris = new string[](1);
        uris[0] = "ipfs://QmToken/metadata.json";

        // Keeper reveals token
        vm.prank(keeper);
        nft.revealTokens(tokenIds, uris);

        // Verify reveal succeeded
        assertTrue(nft.isRevealed(tokenId), "Token should be revealed by keeper");
        assertEq(nft.tokenURI(tokenId), uris[0], "Token should have revealed URI");
    }

    /**
     * @notice Test that unauthorized users cannot reveal tokens
     */
    function testUnauthorizedCannotReveal() public {
        // Mint tokens
        mintTokens(1);

        uint256[] memory tokenIds = new uint256[](1);
        tokenIds[0] = 1;

        string[] memory uris = new string[](1);
        uris[0] = "ipfs://QmToken/metadata.json";

        // Unauthorized user attempts to reveal
        vm.prank(unauthorized);
        vm.expectRevert();
        nft.revealTokens(tokenIds, uris);
    }

    /**
     * @notice Test that unauthorized users cannot update placeholder URI
     */
    function testUnauthorizedCannotUpdatePlaceholder() public {
        // Unauthorized user attempts to update placeholder
        vm.prank(unauthorized);
        vm.expectRevert();
        nft.setPlaceholderURI(NEW_PLACEHOLDER_URI);
    }

    /**
     * @notice Test that keeper cannot update placeholder URI (owner only)
     */
    function testKeeperCannotUpdatePlaceholder() public {
        // Keeper attempts to update placeholder
        vm.prank(keeper);
        vm.expectRevert();
        nft.setPlaceholderURI(NEW_PLACEHOLDER_URI);
    }

    /**
     * @notice Test that updating placeholder doesn't affect revealed tokens
     */
    function testPlaceholderUpdateDoesNotAffectRevealed() public {
        // Mint and reveal token 1
        uint256 token1 = 1;
        uint256 token2 = 2;
        mintTokens(2);

        uint256[] memory tokenIds = new uint256[](1);
        tokenIds[0] = token1;

        string[] memory uris = new string[](1);
        string memory revealedURI = "ipfs://QmRevealed/metadata.json";
        uris[0] = revealedURI;

        vm.prank(owner);
        nft.revealTokens(tokenIds, uris);

        // Update placeholder
        vm.prank(owner);
        nft.setPlaceholderURI(NEW_PLACEHOLDER_URI);

        // Token 1 should still have revealed URI
        assertEq(nft.tokenURI(token1), revealedURI, "Revealed token should not change");

        // Token 2 should have new placeholder
        assertEq(nft.tokenURI(token2), NEW_PLACEHOLDER_URI, "Unrevealed token should have new placeholder");
    }

    /**
     * @notice Test revealing empty batch succeeds
     */
    function testRevealEmptyBatch() public {
        uint256[] memory tokenIds = new uint256[](0);
        string[] memory uris = new string[](0);

        // Should succeed without reverting
        vm.prank(owner);
        nft.revealTokens(tokenIds, uris);
    }

    /**
     * @notice Test tokenURI reverts for non-existent token
     */
    function testTokenURIRevertsForNonExistentToken() public {
        // Attempt to get URI for non-existent token
        vm.expectRevert();
        nft.tokenURI(999);
    }

    /**
     * @notice Test batch reveal with large number of tokens
     */
    function testBatchRevealLargeQuantity() public {
        // Mint 50 tokens (max batch size)
        uint256 quantity = 50;
        mintTokens(quantity);

        // Prepare reveal data
        uint256[] memory tokenIds = new uint256[](quantity);
        string[] memory uris = new string[](quantity);

        for (uint256 i = 0; i < quantity; i++) {
            tokenIds[i] = i + 1;
            uris[i] = string(abi.encodePacked("ipfs://QmToken", vm.toString(i + 1), "/metadata.json"));
        }

        // Reveal all tokens
        vm.prank(owner);
        nft.revealTokens(tokenIds, uris);

        // Verify all tokens are revealed
        for (uint256 i = 0; i < quantity; i++) {
            assertTrue(nft.isRevealed(i + 1), "Token should be revealed");
            assertEq(nft.tokenURI(i + 1), uris[i], "Token should have correct URI");
        }
    }

    /**
     * @notice Test tokenPromptAuthor is accessible after reveal
     */
    function testPromptAuthorAccessibleAfterReveal() public {
        // Mint token
        uint256 tokenId = mintTokens(1);

        // Reveal token
        uint256[] memory tokenIds = new uint256[](1);
        tokenIds[0] = tokenId;

        string[] memory uris = new string[](1);
        uris[0] = "ipfs://QmToken/metadata.json";

        vm.prank(owner);
        nft.revealTokens(tokenIds, uris);

        // Verify prompt author is still accessible
        assertEq(nft.tokenPromptAuthor(tokenId), author, "Prompt author should be accessible after reveal");
    }
}
