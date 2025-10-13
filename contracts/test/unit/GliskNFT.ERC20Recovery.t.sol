// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../../src/GliskNFT.sol";
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

/**
 * @title Mock ERC20 Token for Testing
 * @notice Simple ERC20 implementation for recovery testing
 */
contract MockERC20 is ERC20 {
    constructor() ERC20("MockToken", "MOCK") {
        _mint(msg.sender, 1000000 * 10 ** decimals());
    }

    function mint(address to, uint256 amount) external {
        _mint(to, amount);
    }
}

/**
 * @title GliskNFT ERC20 Recovery Tests
 * @notice Tests for the ERC20 token recovery safety mechanism
 * @dev This is a safety feature to recover accidentally sent ERC20 tokens
 */
contract GliskNFTERC20RecoveryTest is Test {
    GliskNFT public nft;
    MockERC20 public token;

    address public owner;
    address public nonOwner;

    string constant NAME = "GLISK Season 0";
    string constant SYMBOL = "GLISK0";
    string constant PLACEHOLDER_URI = "ipfs://QmPlaceholder";
    uint256 constant INITIAL_MINT_PRICE = 0.001 ether;

    event ERC20Recovered(address indexed token, address indexed to, uint256 amount);

    function setUp() public {
        owner = makeAddr("owner");
        nonOwner = makeAddr("nonOwner");

        vm.deal(owner, 100 ether);
        vm.deal(nonOwner, 100 ether);

        // Deploy contracts
        vm.startPrank(owner);
        nft = new GliskNFT(NAME, SYMBOL, PLACEHOLDER_URI, INITIAL_MINT_PRICE);
        token = new MockERC20();
        vm.stopPrank();
    }

    /**
     * @notice T143 - Test owner can recover ERC20 tokens
     */
    function testRecoverERC20Tokens() public {
        // Accidentally send tokens to the NFT contract
        uint256 amount = 1000 * 10 ** token.decimals();

        vm.prank(owner);
        token.transfer(address(nft), amount);

        // Verify tokens are in the contract
        assertEq(token.balanceOf(address(nft)), amount);
        assertEq(token.balanceOf(owner), token.totalSupply() - amount);

        // Owner recovers the tokens
        vm.prank(owner);
        vm.expectEmit(true, true, false, true);
        emit ERC20Recovered(address(token), owner, amount);
        nft.recoverERC20(address(token), amount);

        // Verify tokens were recovered
        assertEq(token.balanceOf(address(nft)), 0);
        assertEq(token.balanceOf(owner), token.totalSupply());
    }

    /**
     * @notice T143 - Test partial recovery
     */
    function testRecoverPartialAmount() public {
        // Send tokens to the contract
        uint256 totalAmount = 1000 * 10 ** token.decimals();
        uint256 recoverAmount = 600 * 10 ** token.decimals();

        vm.prank(owner);
        token.transfer(address(nft), totalAmount);

        // Recover only part of the tokens
        vm.prank(owner);
        nft.recoverERC20(address(token), recoverAmount);

        // Verify partial recovery
        assertEq(token.balanceOf(address(nft)), totalAmount - recoverAmount);
        assertEq(token.balanceOf(owner), token.totalSupply() - totalAmount + recoverAmount);
    }

    /**
     * @notice T144 - Test non-owner cannot recover ERC20 tokens
     */
    function testUnauthorizedCannotRecoverERC20() public {
        // Send tokens to the contract
        uint256 amount = 1000 * 10 ** token.decimals();

        vm.prank(owner);
        token.transfer(address(nft), amount);

        // Try to recover as non-owner
        bytes32 adminRole = nft.DEFAULT_ADMIN_ROLE();
        vm.prank(nonOwner);
        vm.expectRevert(
            abi.encodeWithSelector(
                IAccessControl.AccessControlUnauthorizedAccount.selector, nonOwner, adminRole
            )
        );
        nft.recoverERC20(address(token), amount);

        // Verify tokens are still in the contract
        assertEq(token.balanceOf(address(nft)), amount);
    }

    /**
     * @notice Test recovering zero amount
     */
    function testRecoverZeroAmount() public {
        // Send tokens to the contract
        uint256 amount = 1000 * 10 ** token.decimals();

        vm.prank(owner);
        token.transfer(address(nft), amount);

        // Recover zero amount (should succeed but do nothing)
        vm.prank(owner);
        nft.recoverERC20(address(token), 0);

        // Verify tokens are still in the contract
        assertEq(token.balanceOf(address(nft)), amount);
    }

    /**
     * @notice Test recovering when no tokens are in contract
     */
    function testRecoverWithNoBalance() public {
        // Try to recover when contract has no tokens
        vm.prank(owner);
        vm.expectRevert(); // ERC20 will revert on insufficient balance
        nft.recoverERC20(address(token), 1000);
    }

    /**
     * @notice Test recovering multiple different ERC20 tokens
     */
    function testRecoverMultipleTokenTypes() public {
        // Deploy second token
        MockERC20 token2 = new MockERC20();

        // Send both tokens to the contract
        uint256 amount1 = 1000 * 10 ** token.decimals();
        uint256 amount2 = 500 * 10 ** token2.decimals();

        vm.startPrank(owner);
        token.transfer(address(nft), amount1);

        vm.startPrank(address(this));
        token2.transfer(address(nft), amount2);
        vm.stopPrank();

        // Recover first token
        vm.prank(owner);
        nft.recoverERC20(address(token), amount1);

        assertEq(token.balanceOf(address(nft)), 0);
        assertEq(token2.balanceOf(address(nft)), amount2);

        // Recover second token
        vm.prank(owner);
        nft.recoverERC20(address(token2), amount2);

        assertEq(token2.balanceOf(address(nft)), 0);
    }

    /**
     * @notice Test event emission
     */
    function testERC20RecoveryEmitsEvent() public {
        uint256 amount = 1000 * 10 ** token.decimals();

        vm.prank(owner);
        token.transfer(address(nft), amount);

        // Expect event to be emitted
        vm.expectEmit(true, true, false, true);
        emit ERC20Recovered(address(token), owner, amount);

        vm.prank(owner);
        nft.recoverERC20(address(token), amount);
    }

    /**
     * @notice Fuzz test: recover various amounts
     */
    function testFuzzRecoverAmount(uint96 amount) public {
        // Bound amount to reasonable values
        amount = uint96(bound(amount, 1, token.totalSupply() / 2));

        // Send tokens to contract
        vm.prank(owner);
        token.transfer(address(nft), amount);

        // Recover tokens
        vm.prank(owner);
        nft.recoverERC20(address(token), amount);

        // Verify recovery
        assertEq(token.balanceOf(address(nft)), 0);
    }
}
