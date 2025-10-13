// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../../src/GliskNFT.sol";

/**
 * @title GliskNFT Access Control Tests
 * @notice Unit tests for User Story 6: Role-Based Access Control
 * @dev Tests hierarchical role permissions (Owner and Keeper)
 */
contract GliskNFTAccessTest is Test {
    GliskNFT public gliskNFT;

    address owner = address(1);
    address keeper = address(2);
    address user = address(3);
    address promptAuthor = address(4);

    string constant PLACEHOLDER_URI = "ipfs://placeholder";
    uint256 constant INITIAL_MINT_PRICE = 0.01 ether;

    event RoleGranted(bytes32 indexed role, address indexed account, address indexed sender);
    event RoleRevoked(bytes32 indexed role, address indexed account, address indexed sender);

    function setUp() public {
        // Deploy contract as owner
        vm.startPrank(owner);
        gliskNFT = new GliskNFT("GLISK", "GLK", PLACEHOLDER_URI, INITIAL_MINT_PRICE);
        vm.stopPrank();

        // Fund test accounts
        vm.deal(user, 10 ether);
        vm.deal(keeper, 10 ether);
    }

    /**
     * @notice T074: Owner grants KEEPER_ROLE to address
     */
    function testOwnerGrantsKeeperRole() public {
        bytes32 keeperRole = gliskNFT.KEEPER_ROLE();

        // Verify keeper does not have role initially
        assertFalse(gliskNFT.hasRole(keeperRole, keeper), "Keeper should not have role initially");

        // Owner grants keeper role
        vm.prank(owner);
        vm.expectEmit(true, true, true, true);
        emit RoleGranted(keeperRole, keeper, owner);
        gliskNFT.grantRole(keeperRole, keeper);

        // Verify keeper has role now
        assertTrue(gliskNFT.hasRole(keeperRole, keeper), "Keeper should have role after grant");
    }

    /**
     * @notice T075: Keeper can call revealTokens()
     */
    function testKeeperCanUpdateURIs() public {
        bytes32 keeperRole = gliskNFT.KEEPER_ROLE();

        // Grant keeper role
        vm.prank(owner);
        gliskNFT.grantRole(keeperRole, keeper);

        // Mint a token first
        vm.prank(user);
        gliskNFT.mint{value: INITIAL_MINT_PRICE}(promptAuthor, 1);

        // Prepare reveal data
        uint256[] memory tokenIds = new uint256[](1);
        tokenIds[0] = 1;
        string[] memory uris = new string[](1);
        uris[0] = "ipfs://revealed1";

        // Keeper reveals tokens
        vm.prank(keeper);
        gliskNFT.revealTokens(tokenIds, uris);

        // Verify token is revealed
        assertTrue(gliskNFT.isRevealed(1), "Token should be revealed");
        assertEq(gliskNFT.tokenURI(1), "ipfs://revealed1", "Token URI should be updated");
    }

    /**
     * @notice T076: Keeper can call setMintPrice()
     */
    function testKeeperCanUpdatePrice() public {
        bytes32 keeperRole = gliskNFT.KEEPER_ROLE();

        // Grant keeper role
        vm.prank(owner);
        gliskNFT.grantRole(keeperRole, keeper);

        uint256 newPrice = 0.02 ether;

        // Keeper updates mint price
        vm.prank(keeper);
        gliskNFT.setMintPrice(newPrice);

        // Verify price is updated
        assertEq(gliskNFT.mintPrice(), newPrice, "Mint price should be updated by keeper");
    }

    /**
     * @notice T077: Keeper cannot call withdrawTreasury()
     */
    function testKeeperCannotWithdrawTreasury() public {
        bytes32 keeperRole = gliskNFT.KEEPER_ROLE();

        // Grant keeper role
        vm.prank(owner);
        gliskNFT.grantRole(keeperRole, keeper);

        // Mint to create treasury balance
        vm.prank(user);
        gliskNFT.mint{value: INITIAL_MINT_PRICE}(promptAuthor, 1);

        // Keeper tries to withdraw treasury
        vm.prank(keeper);
        vm.expectRevert();
        gliskNFT.withdrawTreasury();

        // Verify treasury balance is unchanged
        assertGt(gliskNFT.treasuryBalance(), 0, "Treasury should still have balance");
    }

    /**
     * @notice T078: Keeper cannot call endSeason() (will be implemented in Phase 9)
     */
    function testKeeperCannotEndSeason() public {
        bytes32 keeperRole = gliskNFT.KEEPER_ROLE();
        bytes32 adminRole = gliskNFT.DEFAULT_ADMIN_ROLE();

        // Grant keeper role
        vm.prank(owner);
        gliskNFT.grantRole(keeperRole, keeper);

        // Note: endSeason() not implemented yet in Phase 8
        // This test will be updated in Phase 9
        // For now, we just verify keeper has limited permissions
        assertTrue(gliskNFT.hasRole(keeperRole, keeper), "Keeper should have keeper role");
        assertFalse(gliskNFT.hasRole(adminRole, keeper), "Keeper should not have admin role");
    }

    /**
     * @notice T079: Owner revokes KEEPER_ROLE
     */
    function testOwnerRevokesKeeperRole() public {
        bytes32 keeperRole = gliskNFT.KEEPER_ROLE();

        // Grant keeper role first
        vm.prank(owner);
        gliskNFT.grantRole(keeperRole, keeper);

        // Verify keeper has role
        assertTrue(gliskNFT.hasRole(keeperRole, keeper), "Keeper should have role");

        // Owner revokes keeper role
        vm.prank(owner);
        vm.expectEmit(true, true, true, true);
        emit RoleRevoked(keeperRole, keeper, owner);
        gliskNFT.revokeRole(keeperRole, keeper);

        // Verify keeper no longer has role
        assertFalse(gliskNFT.hasRole(keeperRole, keeper), "Keeper should not have role after revoke");
    }

    /**
     * @notice T080: Owner has all permissions
     */
    function testOwnerHasAllPermissions() public {
        bytes32 keeperRole = gliskNFT.KEEPER_ROLE();

        // Owner can update mint price
        vm.prank(owner);
        gliskNFT.setMintPrice(0.02 ether);
        assertEq(gliskNFT.mintPrice(), 0.02 ether, "Owner should update price");

        // Mint a token
        vm.prank(user);
        gliskNFT.mint{value: 0.02 ether}(promptAuthor, 1);

        // Owner can reveal tokens
        uint256[] memory tokenIds = new uint256[](1);
        tokenIds[0] = 1;
        string[] memory uris = new string[](1);
        uris[0] = "ipfs://revealed";

        vm.prank(owner);
        gliskNFT.revealTokens(tokenIds, uris);
        assertTrue(gliskNFT.isRevealed(1), "Owner should reveal tokens");

        // Owner can update placeholder URI
        vm.prank(owner);
        gliskNFT.setPlaceholderURI("ipfs://newplaceholder");

        // Owner can withdraw treasury
        vm.prank(owner);
        gliskNFT.withdrawTreasury();
        assertEq(gliskNFT.treasuryBalance(), 0, "Owner should withdraw treasury");

        // Owner can grant roles
        vm.prank(owner);
        gliskNFT.grantRole(keeperRole, keeper);
        assertTrue(gliskNFT.hasRole(keeperRole, keeper), "Owner should grant roles");

        // Owner can revoke roles
        vm.prank(owner);
        gliskNFT.revokeRole(keeperRole, keeper);
        assertFalse(gliskNFT.hasRole(keeperRole, keeper), "Owner should revoke roles");
    }

    /**
     * @notice Additional test: Non-owner cannot grant roles
     */
    function testNonOwnerCannotGrantRoles() public {
        bytes32 keeperRole = gliskNFT.KEEPER_ROLE();

        // User tries to grant keeper role
        vm.prank(user);
        vm.expectRevert();
        gliskNFT.grantRole(keeperRole, keeper);

        // Verify keeper does not have role
        assertFalse(gliskNFT.hasRole(keeperRole, keeper), "Keeper should not have role");
    }

    /**
     * @notice Additional test: Keeper cannot grant roles
     */
    function testKeeperCannotGrantRoles() public {
        bytes32 keeperRole = gliskNFT.KEEPER_ROLE();

        // Grant keeper role
        vm.prank(owner);
        gliskNFT.grantRole(keeperRole, keeper);

        // Keeper tries to grant keeper role to another address
        vm.prank(keeper);
        vm.expectRevert();
        gliskNFT.grantRole(keeperRole, user);

        // Verify user does not have role
        assertFalse(gliskNFT.hasRole(keeperRole, user), "User should not have role");
    }

    /**
     * @notice Additional test: Keeper cannot update placeholder URI
     */
    function testKeeperCannotUpdatePlaceholderURI() public {
        bytes32 keeperRole = gliskNFT.KEEPER_ROLE();

        // Grant keeper role
        vm.prank(owner);
        gliskNFT.grantRole(keeperRole, keeper);

        // Keeper tries to update placeholder URI
        vm.prank(keeper);
        vm.expectRevert();
        gliskNFT.setPlaceholderURI("ipfs://newplaceholder");
    }

    /**
     * @notice Additional test: Owner retains admin role
     */
    function testOwnerRetainsAdminRole() public {
        bytes32 adminRole = gliskNFT.DEFAULT_ADMIN_ROLE();
        bytes32 keeperRole = gliskNFT.KEEPER_ROLE();

        // Verify owner has admin role
        assertTrue(gliskNFT.hasRole(adminRole, owner), "Owner should have admin role");

        // Grant keeper role to another address
        vm.prank(owner);
        gliskNFT.grantRole(keeperRole, keeper);

        // Verify owner still has admin role
        assertTrue(gliskNFT.hasRole(adminRole, owner), "Owner should still have admin role");

        // Verify keeper does not have admin role
        assertFalse(gliskNFT.hasRole(adminRole, keeper), "Keeper should not have admin role");
    }
}
