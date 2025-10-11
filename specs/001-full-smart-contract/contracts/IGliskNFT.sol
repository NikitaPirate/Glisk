// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title IGliskNFT
 * @notice Interface for the GLISK Season 0 NFT contract
 * @dev Complete interface specification for GliskNFT.sol implementation
 *
 * This interface defines all public and external functions for the GLISK blind box NFT system.
 * The implementation will inherit from OpenZeppelin contracts (ERC721, AccessControl, ReentrancyGuard, ERC2981).
 */
interface IGliskNFT {
    // ============================================
    // EVENTS
    // ============================================

    /// @notice Emitted when NFTs are minted in a batch
    /// @param minter Address that initiated the mint
    /// @param promptAuthor Address of the prompt author credited for this batch
    /// @param startTokenId First token ID in the batch
    /// @param quantity Number of NFTs minted in this batch
    /// @param totalPaid Total ETH paid (including any overpayment)
    event BatchMinted(
        address indexed minter,
        address indexed promptAuthor,
        uint256 indexed startTokenId,
        uint256 quantity,
        uint256 totalPaid
    );

    /// @notice Emitted when a prompt author claims their rewards
    /// @param author Address of the prompt author
    /// @param amount Amount claimed in wei
    event AuthorClaimed(address indexed author, uint256 amount);

    /// @notice Emitted when treasury funds are withdrawn
    /// @param recipient Address receiving the treasury funds (Owner)
    /// @param amount Amount withdrawn in wei
    event TreasuryWithdrawn(address indexed recipient, uint256 amount);

    /// @notice Emitted when unclaimed author rewards are swept to treasury
    /// @param totalAmount Total amount swept in wei
    /// @param authorsCount Number of authors whose balances were swept
    event UnclaimedRewardsSwept(uint256 totalAmount, uint256 authorsCount);

    /// @notice Emitted when mint price is updated
    /// @param oldPrice Previous mint price in wei
    /// @param newPrice New mint price in wei
    event MintPriceUpdated(uint256 oldPrice, uint256 newPrice);

    /// @notice Emitted when placeholder URI is updated
    /// @param newURI New placeholder URI for unrevealed tokens
    event PlaceholderURIUpdated(string newURI);

    /// @notice Emitted when tokens are revealed (URIs set permanently)
    /// @param tokenIds Array of token IDs that were revealed
    event TokensRevealed(uint256[] tokenIds);

    /// @notice Emitted when the season ends
    /// @param timestamp Block timestamp when season ended
    event SeasonEnded(uint256 timestamp);

    /// @notice Emitted when royalty configuration is updated
    /// @param receiver Address that receives royalty payments
    /// @param feeNumerator Royalty fee in basis points (250 = 2.5%)
    event RoyaltyUpdated(address receiver, uint96 feeNumerator);

    /// @notice Emitted when contract receives direct ETH payment
    /// @param sender Address that sent the payment
    /// @param amount Amount received in wei
    event DirectPaymentReceived(address indexed sender, uint256 amount);

    // ============================================
    // ERRORS
    // ============================================

    /// @notice Thrown when minting quantity is zero
    error InvalidQuantity();

    /// @notice Thrown when minting quantity exceeds maximum batch size
    error ExceedsMaxBatchSize();

    /// @notice Thrown when payment is insufficient for requested quantity
    error InsufficientPayment();

    /// @notice Thrown when attempting to mint after season has ended
    error MintingDisabled();

    /// @notice Thrown when season has already ended
    error SeasonAlreadyEnded();

    /// @notice Thrown when attempting to sweep rewards before claim period expires
    error ClaimPeriodActive();

    /// @notice Thrown when attempting to sweep without ending season first
    error SeasonNotEnded();

    /// @notice Thrown when treasury has no balance to withdraw
    error NoBalance();

    /// @notice Thrown when attempting to reveal an already-revealed token
    error AlreadyRevealed(uint256 tokenId);

    /// @notice Thrown when array lengths don't match
    error LengthMismatch();

    /// @notice Thrown when ETH transfer fails
    error TransferFailed();

    // ============================================
    // CORE MINTING FUNCTIONS
    // ============================================

    /**
     * @notice Mint one or more NFTs with specified prompt author
     * @dev Payment split: 50% to author (claimable), 50% to treasury. Overpayment goes to treasury.
     * @param promptAuthor Address of the prompt author to credit for this batch
     * @param quantity Number of NFTs to mint (1 to MAX_BATCH_SIZE)
     *
     * Requirements:
     * - quantity must be > 0 and <= MAX_BATCH_SIZE
     * - msg.value must be >= mintPrice * quantity
     * - season must not have ended
     *
     * Emits: BatchMinted event
     */
    function mint(address promptAuthor, uint256 quantity) external payable;

    // ============================================
    // REWARD MANAGEMENT
    // ============================================

    /**
     * @notice Claim all accumulated rewards for the caller (prompt author)
     * @dev Uses pull pattern for security. Allows zero-balance claims (no revert).
     *
     * Requirements:
     * - None (can be called anytime, even with zero balance)
     *
     * Emits: AuthorClaimed event
     */
    function claimAuthorRewards() external;

    /**
     * @notice Get claimable balance for a prompt author
     * @param author Address of the prompt author
     * @return Claimable balance in wei
     */
    function authorClaimable(address author) external view returns (uint256);

    // ============================================
    // TREASURY MANAGEMENT
    // ============================================

    /**
     * @notice Withdraw all treasury funds (Owner only)
     * @dev Transfers entire treasury balance to caller
     *
     * Requirements:
     * - Caller must have DEFAULT_ADMIN_ROLE
     * - Treasury balance must be > 0
     *
     * Emits: TreasuryWithdrawn event
     */
    function withdrawTreasury() external;

    /**
     * @notice Get current treasury balance
     * @return Treasury balance in wei
     */
    function treasuryBalance() external view returns (uint256);

    // ============================================
    // NFT REVEAL WORKFLOW
    // ============================================

    /**
     * @notice Reveal multiple tokens by setting their URIs permanently
     * @dev Owner or Keeper only. Once revealed, URIs cannot be changed.
     * @param tokenIds Array of token IDs to reveal
     * @param uris Array of corresponding IPFS URIs
     *
     * Requirements:
     * - Caller must have DEFAULT_ADMIN_ROLE or KEEPER_ROLE
     * - tokenIds.length must equal uris.length
     * - All tokens must exist and not be revealed
     *
     * Emits: TokensRevealed event
     */
    function revealTokens(uint256[] calldata tokenIds, string[] calldata uris) external;

    /**
     * @notice Update placeholder URI for all unrevealed tokens (Owner only)
     * @param newURI New placeholder URI
     *
     * Requirements:
     * - Caller must have DEFAULT_ADMIN_ROLE
     *
     * Emits: PlaceholderURIUpdated event
     */
    function setPlaceholderURI(string calldata newURI) external;

    /**
     * @notice Check if a token has been revealed
     * @param tokenId Token ID to check
     * @return True if token is revealed, false if using placeholder
     */
    function isRevealed(uint256 tokenId) external view returns (bool);

    /**
     * @notice Get prompt author for a token
     * @param tokenId Token ID
     * @return Address of the prompt author
     */
    function tokenPromptAuthor(uint256 tokenId) external view returns (address);

    // ============================================
    // PRICING
    // ============================================

    /**
     * @notice Update mint price (Owner or Keeper)
     * @param newPrice New mint price in wei
     *
     * Requirements:
     * - Caller must have DEFAULT_ADMIN_ROLE or KEEPER_ROLE
     *
     * Emits: MintPriceUpdated event
     */
    function setMintPrice(uint256 newPrice) external;

    /**
     * @notice Get current mint price
     * @return Mint price in wei per NFT
     */
    function mintPrice() external view returns (uint256);

    // ============================================
    // SEASON MANAGEMENT
    // ============================================

    /**
     * @notice End the season and start 2-week claim countdown (Owner only)
     * @dev Permanently disables minting. Cannot be reversed.
     *
     * Requirements:
     * - Caller must have DEFAULT_ADMIN_ROLE
     * - Season must not have already ended
     *
     * Emits: SeasonEnded event
     */
    function endSeason() external;

    /**
     * @notice Sweep unclaimed author rewards to treasury after claim period (Owner only)
     * @dev Transfers unclaimed balances from specified authors to treasury
     * @param authors Array of author addresses to sweep
     *
     * Requirements:
     * - Caller must have DEFAULT_ADMIN_ROLE
     * - Season must have ended
     * - Current time must be >= seasonEndTime + CLAIM_PERIOD
     *
     * Emits: UnclaimedRewardsSwept event
     */
    function sweepUnclaimedRewards(address[] calldata authors) external;

    /**
     * @notice Check if season has ended
     * @return True if season ended, false if still active
     */
    function seasonEnded() external view returns (bool);

    /**
     * @notice Get season end timestamp
     * @return Timestamp when season ended (0 if not ended)
     */
    function seasonEndTime() external view returns (uint256);

    /**
     * @notice Get claim period duration in seconds
     * @return Duration of claim period (14 days)
     */
    function CLAIM_PERIOD() external view returns (uint256);

    // ============================================
    // ROYALTY MANAGEMENT
    // ============================================

    /**
     * @notice Update default royalty configuration (Owner only)
     * @param receiver Address to receive royalty payments
     * @param feeNumerator Royalty fee in basis points (250 = 2.5%)
     *
     * Requirements:
     * - Caller must have DEFAULT_ADMIN_ROLE
     *
     * Emits: RoyaltyUpdated event
     */
    function setDefaultRoyalty(address receiver, uint96 feeNumerator) external;

    // ============================================
    // CONSTANTS
    // ============================================

    /**
     * @notice Maximum number of NFTs that can be minted in a single transaction
     * @return Maximum batch size
     */
    function MAX_BATCH_SIZE() external view returns (uint256);

    /**
     * @notice Keeper role identifier
     * @return Role hash for KEEPER_ROLE
     */
    function KEEPER_ROLE() external view returns (bytes32);
}
