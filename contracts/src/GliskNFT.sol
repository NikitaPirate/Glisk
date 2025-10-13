// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/common/ERC2981.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

/**
 * @title GliskNFT
 * @notice GLISK Season 0 blind box NFT contract with prompt author attribution and rewards
 * @dev Implements ERC721, AccessControl, ReentrancyGuard, and ERC2981 for comprehensive NFT functionality
 *
 * Key Features:
 * - Batch minting with prompt author attribution
 * - 50/50 payment split between author rewards and treasury
 * - NFT reveal workflow (placeholder → permanent URI)
 * - Role-based access control (Owner, Keeper)
 * - Season lifecycle management (end season → sweep countdown)
 * - ERC-2981 royalty support
 */
contract GliskNFT is ERC721, AccessControl, ReentrancyGuard, ERC2981 {
    // ============================================
    // CUSTOM ERRORS
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

    /// @notice Thrown when attempting to sweep rewards before protection period expires
    error SweepProtectionActive();

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
    // EVENTS
    // ============================================

    /// @notice Emitted when NFTs are minted in a batch
    event BatchMinted(
        address indexed minter,
        address indexed promptAuthor,
        uint256 indexed startTokenId,
        uint256 quantity,
        uint256 totalPaid
    );

    /// @notice Emitted when a prompt author claims their rewards
    event AuthorClaimed(address indexed author, uint256 amount);

    /// @notice Emitted when treasury funds are withdrawn
    event TreasuryWithdrawn(address indexed recipient, uint256 amount);

    /// @notice Emitted when unclaimed author rewards are swept to treasury
    event UnclaimedRewardsSwept(uint256 totalAmount, uint256 authorsCount);

    /// @notice Emitted when mint price is updated
    event MintPriceUpdated(uint256 oldPrice, uint256 newPrice);

    /// @notice Emitted when placeholder URI is updated
    event PlaceholderURIUpdated(string newURI);

    /// @notice Emitted when tokens are revealed (URIs set permanently)
    event TokensRevealed(uint256[] tokenIds);

    /// @notice Emitted when the season ends
    event SeasonEnded(uint256 timestamp);

    /// @notice Emitted when royalty configuration is updated
    event RoyaltyUpdated(address receiver, uint96 feeNumerator);

    /// @notice Emitted when contract receives direct ETH payment
    event DirectPaymentReceived(address indexed sender, uint256 amount);

    /// @notice Emitted when ERC20 tokens are recovered from the contract
    event ERC20Recovered(address indexed token, address indexed to, uint256 amount);

    // ============================================
    // CONSTANTS
    // ============================================

    /// @notice Keeper role identifier for limited operations
    bytes32 public constant KEEPER_ROLE = keccak256("KEEPER_ROLE");

    /// @notice Protection period after season end before sweep is allowed (14 days)
    uint256 public constant SWEEP_PROTECTION_PERIOD = 14 days;

    /// @notice Maximum number of NFTs that can be minted in a single transaction
    uint256 public constant MAX_BATCH_SIZE = 50;

    // ============================================
    // STATE VARIABLES
    // ============================================

    /// @notice Sequential token ID counter (starts at 1)
    uint256 private _nextTokenId;

    /// @notice Current mint price in wei per NFT
    uint256 public mintPrice;

    /// @notice Accumulated treasury balance in wei
    uint256 public treasuryBalance;

    /// @notice Placeholder URI for unrevealed tokens
    string private _placeholderURI;

    /// @notice Whether the season has ended
    bool public seasonEnded;

    /// @notice Timestamp when season ended (0 if not ended)
    uint256 public seasonEndTime;

    // ============================================
    // MAPPINGS
    // ============================================

    /// @notice Maps token ID to prompt author address
    mapping(uint256 => address) public tokenPromptAuthor;

    /// @notice Maps token ID to revealed metadata URI
    mapping(uint256 => string) private _tokenURIs;

    /// @notice Maps token ID to reveal status
    mapping(uint256 => bool) private _revealed;

    /// @notice Maps author address to claimable balance
    mapping(address => uint256) public authorClaimable;

    // ============================================
    // CONSTRUCTOR
    // ============================================

    /**
     * @notice Initialize the GLISK NFT contract
     * @param name_ Token name (e.g., "GLISK Season 0")
     * @param symbol_ Token symbol (e.g., "GLISK0")
     * @param placeholderURI_ Initial placeholder URI for unrevealed tokens
     * @param initialMintPrice_ Initial mint price in wei
     */
    constructor(string memory name_, string memory symbol_, string memory placeholderURI_, uint256 initialMintPrice_)
        ERC721(name_, symbol_)
    {
        // Grant DEFAULT_ADMIN_ROLE to deployer
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);

        // Initialize state
        _placeholderURI = placeholderURI_;
        mintPrice = initialMintPrice_;
        _nextTokenId = 1; // Start token IDs at 1

        // Set default royalty to deployer at 2.5% (250 basis points)
        _setDefaultRoyalty(msg.sender, 250);
    }

    // ============================================
    // INTERFACE SUPPORT
    // ============================================

    /**
     * @notice Check if contract supports a given interface
     * @param interfaceId Interface identifier to check
     * @return True if interface is supported
     */
    function supportsInterface(bytes4 interfaceId)
        public
        view
        override(ERC721, ERC2981, AccessControl)
        returns (bool)
    {
        return super.supportsInterface(interfaceId);
    }

    // ============================================
    // RECEIVE FUNCTION
    // ============================================

    /**
     * @notice Accept direct ETH payments to treasury
     * @dev All direct payments are added to treasury balance
     */
    receive() external payable {
        treasuryBalance += msg.value;
        emit DirectPaymentReceived(msg.sender, msg.value);
    }

    // ============================================
    // CORE MINTING FUNCTIONS (User Story 1)
    // ============================================

    /**
     * @notice Mint one or more NFTs with specified prompt author
     * @dev Payment split: 50% to author (claimable), 50% to treasury. Overpayment goes entirely to treasury.
     *      Uses _safeMint to ensure recipient can receive NFTs.
     *      Token IDs are sequential starting from 1.
     *
     * @param promptAuthor Address of the prompt author to credit for this batch
     * @param quantity Number of NFTs to mint (must be 1 to MAX_BATCH_SIZE)
     *
     * Requirements:
     * - quantity must be > 0 and <= MAX_BATCH_SIZE (50)
     * - msg.value must be >= mintPrice * quantity
     * - season must not have ended
     *
     * Emits: BatchMinted event with minter, promptAuthor, startTokenId, quantity, and totalPaid
     *
     * Payment Distribution:
     * - Base payment (mintPrice * quantity) is split 50/50 between author and treasury
     * - Any overpayment (msg.value - base payment) goes entirely to treasury
     * - Author's share is added to authorClaimable[promptAuthor] for later claim
     * - Treasury's share is added to treasuryBalance
     *
     * Gas Optimization:
     * - Batch minting reduces per-token gas cost
     * - State updates happen once per batch, not per token
     */
    function mint(address promptAuthor, uint256 quantity) external payable nonReentrant {
        // Validate quantity
        if (quantity == 0) revert InvalidQuantity();
        if (quantity > MAX_BATCH_SIZE) revert ExceedsMaxBatchSize();

        // Calculate required payment
        uint256 totalPrice = mintPrice * quantity;

        // Validate payment
        if (msg.value < totalPrice) revert InsufficientPayment();

        // Check season is active
        if (seasonEnded) revert MintingDisabled();

        // Calculate payment distribution
        // Base payment split: 50/50 between author and treasury
        uint256 authorShare = totalPrice / 2;
        uint256 treasuryShare = totalPrice - authorShare; // Handles odd amounts

        // Add any overpayment to treasury
        if (msg.value > totalPrice) {
            treasuryShare += (msg.value - totalPrice);
        }

        // Update balances
        authorClaimable[promptAuthor] += authorShare;
        treasuryBalance += treasuryShare;

        // Record starting token ID for event
        uint256 startTokenId = _nextTokenId;

        // Mint tokens in batch
        for (uint256 i = 0; i < quantity; i++) {
            uint256 tokenId = _nextTokenId++;
            _safeMint(msg.sender, tokenId);
            tokenPromptAuthor[tokenId] = promptAuthor;
        }

        // Emit batch minted event
        emit BatchMinted(msg.sender, promptAuthor, startTokenId, quantity, msg.value);
    }

    // ============================================
    // AUTHOR REWARDS FUNCTIONS (User Story 2)
    // ============================================

    /**
     * @notice Claim accumulated author rewards
     * @dev Prompt authors can call this function to claim their 50% share from all mints
     *      attributed to their prompts. Uses pull pattern for security (reentrancy protection).
     *      Transfer happens using low-level call to support both EOAs and contracts.
     *
     * Requirements:
     * - Author must have claimable balance (zero balance is allowed, will succeed with no transfer)
     * - Transfer must succeed (will revert if recipient rejects payment)
     *
     * Security:
     * - nonReentrant modifier prevents reentrancy attacks
     * - State updated before external call (checks-effects-interactions pattern)
     * - Uses low-level call{value} for maximum compatibility
     *
     * Emits: AuthorClaimed event with author address and claimed amount
     *
     * Gas Considerations:
     * - Single storage read and write
     * - ETH transfer via call (~2300+ gas for recipient)
     */
    function claimAuthorRewards() external nonReentrant {
        // Read claimable balance
        uint256 amount = authorClaimable[msg.sender];

        // Allow claim with zero balance (no revert, just no transfer)
        if (amount == 0) {
            return;
        }

        // Update state before transfer (prevent reentrancy)
        authorClaimable[msg.sender] = 0;

        // Transfer ETH to author
        (bool success,) = msg.sender.call{value: amount}("");
        if (!success) revert TransferFailed();

        // Emit event
        emit AuthorClaimed(msg.sender, amount);
    }

    // ============================================
    // NFT REVEAL AND METADATA FUNCTIONS (User Story 8)
    // ============================================

    /**
     * @notice Get the metadata URI for a token
     * @dev Returns revealed URI if token is revealed, otherwise returns placeholder URI
     *      Overrides ERC721.tokenURI() to implement reveal workflow
     *
     * @param tokenId The token ID to query
     * @return The metadata URI (IPFS link or other)
     *
     * Requirements:
     * - Token must exist
     *
     * Behavior:
     * - Revealed tokens: Returns unique permanent URI from _tokenURIs mapping
     * - Unrevealed tokens: Returns shared _placeholderURI
     * - Non-existent tokens: Reverts (via _requireOwned)
     */
    function tokenURI(uint256 tokenId) public view override returns (string memory) {
        // Ensure token exists (reverts if not)
        _requireOwned(tokenId);

        // Return revealed URI if token has been revealed
        if (_revealed[tokenId]) {
            return _tokenURIs[tokenId];
        }

        // Return placeholder URI for unrevealed tokens
        return _placeholderURI;
    }

    /**
     * @notice Update the placeholder URI for all unrevealed tokens
     * @dev Owner can update placeholder at any time to change appearance of unrevealed tokens
     *      Does not affect already-revealed tokens
     *
     * @param newURI The new placeholder URI
     *
     * Requirements:
     * - Caller must have DEFAULT_ADMIN_ROLE (Owner)
     *
     * Emits: PlaceholderURIUpdated event with new URI
     *
     * Use Cases:
     * - Update placeholder during development/testing
     * - Change placeholder artwork for marketing
     * - Fix placeholder URI if initial one has issues
     */
    function setPlaceholderURI(string memory newURI) external onlyRole(DEFAULT_ADMIN_ROLE) {
        _placeholderURI = newURI;
        emit PlaceholderURIUpdated(newURI);
    }

    /**
     * @notice Reveal tokens by setting their permanent metadata URIs
     * @dev Batch operation to reveal multiple tokens at once. Once revealed, tokens are immutable.
     *      Both Owner and Keeper roles can reveal tokens (Keeper for operational efficiency).
     *
     * @param tokenIds Array of token IDs to reveal
     * @param uris Array of corresponding metadata URIs (must match tokenIds length)
     *
     * Requirements:
     * - Caller must have DEFAULT_ADMIN_ROLE (Owner) or KEEPER_ROLE
     * - Array lengths must match (tokenIds.length == uris.length)
     * - All tokens must exist
     * - All tokens must not be already revealed (immutability check)
     *
     * Emits: TokensRevealed event with array of revealed token IDs
     *
     * Gas Considerations:
     * - Batch operation reduces transaction overhead
     * - Recommended batch size: 10-50 tokens per transaction
     * - String storage is expensive; consider batch size vs gas limit
     */
    function revealTokens(uint256[] calldata tokenIds, string[] calldata uris) external {
        // Require either Owner (DEFAULT_ADMIN_ROLE) or Keeper (KEEPER_ROLE)
        if (!hasRole(DEFAULT_ADMIN_ROLE, msg.sender) && !hasRole(KEEPER_ROLE, msg.sender)) {
            revert AccessControlUnauthorizedAccount(msg.sender, KEEPER_ROLE);
        }
        // Validate array lengths match
        if (tokenIds.length != uris.length) revert LengthMismatch();

        // Reveal each token
        for (uint256 i = 0; i < tokenIds.length; i++) {
            uint256 tokenId = tokenIds[i];

            // Check token is not already revealed (immutability)
            if (_revealed[tokenId]) revert AlreadyRevealed(tokenId);

            // Set permanent URI and mark as revealed
            _tokenURIs[tokenId] = uris[i];
            _revealed[tokenId] = true;
        }

        // Emit event with all revealed token IDs
        emit TokensRevealed(tokenIds);
    }

    /**
     * @notice Check if a token has been revealed
     * @dev Public view function to query reveal status
     *
     * @param tokenId The token ID to check
     * @return True if token has been revealed, false otherwise
     *
     * Note: Does not check if token exists. Returns false for non-existent tokens.
     */
    function isRevealed(uint256 tokenId) external view returns (bool) {
        return _revealed[tokenId];
    }

    // ============================================
    // TREASURY MANAGEMENT FUNCTIONS (User Story 5)
    // ============================================

    /**
     * @notice Withdraw all treasury funds to owner
     * @dev Owner can call this function to withdraw accumulated treasury balance
     *      (50% of all mints + overpayments + direct payments).
     *      Uses pull pattern with reentrancy protection for security.
     *
     * Requirements:
     * - Caller must have DEFAULT_ADMIN_ROLE (Owner)
     * - Treasury balance must be > 0
     * - Transfer must succeed (will revert if owner rejects payment)
     *
     * Security:
     * - nonReentrant modifier prevents reentrancy attacks
     * - State updated before external call (checks-effects-interactions pattern)
     * - Uses low-level call{value} for maximum compatibility
     *
     * Emits: TreasuryWithdrawn event with recipient address and withdrawn amount
     *
     * Gas Considerations:
     * - Single storage read and write
     * - ETH transfer via call (~2300+ gas for recipient)
     *
     * Note: Withdraws ALL treasury balance in one transaction
     */
    function withdrawTreasury() external onlyRole(DEFAULT_ADMIN_ROLE) nonReentrant {
        // Check treasury has balance
        uint256 amount = treasuryBalance;
        if (amount == 0) revert NoBalance();

        // Update state before transfer (prevent reentrancy)
        treasuryBalance = 0;

        // Transfer ETH to owner
        (bool success,) = msg.sender.call{value: amount}("");
        if (!success) revert TransferFailed();

        // Emit event
        emit TreasuryWithdrawn(msg.sender, amount);
    }

    // ============================================
    // DYNAMIC PRICING FUNCTIONS (User Story 3)
    // ============================================

    /**
     * @notice Update the mint price
     * @dev Owner or Keeper can adjust the mint price to respond to ETH volatility
     *      or market conditions. Does not affect already-minted tokens or their
     *      associated balances. Only future mints will use the new price.
     *
     * @param newPrice The new mint price in wei per NFT
     *
     * Requirements:
     * - Caller must have DEFAULT_ADMIN_ROLE (Owner) or KEEPER_ROLE
     *
     * Emits: MintPriceUpdated event with old price and new price
     *
     * Use Cases:
     * - Respond to ETH price volatility (maintain ~$0.05 USD target)
     * - Adjust pricing based on demand
     * - Set promotional pricing
     * - Set to zero for free mint periods
     *
     * Note: Price update does not affect past mints. Author rewards and treasury
     *       balances from previous mints remain unchanged.
     */
    function setMintPrice(uint256 newPrice) external {
        // Require either Owner (DEFAULT_ADMIN_ROLE) or Keeper (KEEPER_ROLE)
        if (!hasRole(DEFAULT_ADMIN_ROLE, msg.sender) && !hasRole(KEEPER_ROLE, msg.sender)) {
            revert AccessControlUnauthorizedAccount(msg.sender, KEEPER_ROLE);
        }

        uint256 oldPrice = mintPrice;
        mintPrice = newPrice;

        emit MintPriceUpdated(oldPrice, newPrice);
    }

    // ============================================
    // SEASON LIFECYCLE FUNCTIONS (User Story 4)
    // ============================================

    /**
     * @notice End the current season
     * @dev Permanently disables minting and starts the 2-week countdown for sweeping unclaimed rewards.
     *      This operation is irreversible. Once a season ends, a new contract must be deployed
     *      for the next season.
     *
     * Requirements:
     * - Caller must have DEFAULT_ADMIN_ROLE (Owner)
     * - Season must not have already ended
     *
     * Emits: SeasonEnded event with current timestamp
     *
     * Effects:
     * - Sets seasonEnded = true (permanently disables mint())
     * - Records seasonEndTime = block.timestamp (starts countdown)
     * - Authors can still claim their rewards at any time
     * - After SWEEP_PROTECTION_PERIOD (14 days), unclaimed rewards can be swept to treasury
     *
     * Use Cases:
     * - End of planned season duration (~1-3 months)
     * - Emergency shutdown if needed
     * - Transition to new season (requires new contract deployment)
     */
    function endSeason() external onlyRole(DEFAULT_ADMIN_ROLE) {
        // Check season hasn't already ended
        if (seasonEnded) revert SeasonAlreadyEnded();

        // Mark season as ended and record timestamp
        seasonEnded = true;
        seasonEndTime = block.timestamp;

        emit SeasonEnded(block.timestamp);
    }

    /**
     * @notice Sweep unclaimed author rewards to treasury after protection period
     * @dev After season ends and SWEEP_PROTECTION_PERIOD expires, Owner can sweep
     *      unclaimed rewards from specified authors to the treasury. This gives authors
     *      a 2-week grace period to claim their rewards.
     *
     * @param authors Array of author addresses whose unclaimed rewards should be swept
     *
     * Requirements:
     * - Caller must have DEFAULT_ADMIN_ROLE (Owner)
     * - Season must have ended (seasonEnded == true)
     * - SWEEP_PROTECTION_PERIOD must have elapsed (14 days after seasonEndTime)
     *
     * Emits: UnclaimedRewardsSwept event with total swept amount and author count
     *
     * Gas Considerations:
     * - Batch operation to reduce transaction overhead
     * - Recommended batch size: 100-200 authors per transaction
     * - Can be called multiple times with different author lists
     *
     * Security:
     * - Authors with zero balance are skipped (no revert)
     * - State updated before any external calls
     * - No reentrancy risk (no external calls to unknown addresses)
     *
     * Note: This operation does NOT prevent authors from future claims if called
     *       before they claim. However, after sweep, their balance is zero.
     */
    function sweepUnclaimedRewards(address[] calldata authors) external onlyRole(DEFAULT_ADMIN_ROLE) {
        // Check season has ended
        if (!seasonEnded) revert SeasonNotEnded();

        // Check sweep protection period has passed
        if (block.timestamp < seasonEndTime + SWEEP_PROTECTION_PERIOD) {
            revert SweepProtectionActive();
        }

        uint256 totalSwept = 0;
        uint256 authorsSwept = 0;

        // Sweep unclaimed rewards from each author
        for (uint256 i = 0; i < authors.length; i++) {
            address author = authors[i];
            uint256 amount = authorClaimable[author];

            // Skip authors with zero balance
            if (amount == 0) continue;

            // Reset author balance and accumulate total
            authorClaimable[author] = 0;
            totalSwept += amount;
            authorsSwept++;
        }

        // Add swept rewards to treasury
        if (totalSwept > 0) {
            treasuryBalance += totalSwept;
        }

        emit UnclaimedRewardsSwept(totalSwept, authorsSwept);
    }

    // ============================================
    // ROYALTY MANAGEMENT FUNCTIONS (User Story 7)
    // ============================================

    /**
     * @notice Update the default royalty configuration for secondary sales
     * @dev Sets the ERC-2981 royalty information that marketplaces will query.
     *      Typically, the receiver should be the treasury address to accumulate
     *      royalties from secondary sales.
     *
     * @param receiver Address that will receive royalty payments (usually treasury)
     * @param feeNumerator Royalty fee in basis points (e.g., 250 = 2.5%, max 10000 = 100%)
     *
     * Requirements:
     * - Caller must have DEFAULT_ADMIN_ROLE (Owner)
     * - feeNumerator must be <= 10000 (enforced by OpenZeppelin ERC2981)
     *
     * Emits: RoyaltyUpdated event with receiver address and fee numerator
     *
     * ERC-2981 Standard:
     * - Single receiver per contract (no per-token royalties in this implementation)
     * - Royalty amount = (salePrice * feeNumerator) / 10000
     * - Marketplaces call royaltyInfo(tokenId, salePrice) to determine payment
     *
     * Recommended Values:
     * - 250 basis points (2.5%) for standard royalties
     * - Receiver: treasury address to accumulate platform funds
     *
     * Use Cases:
     * - Initial setup during deployment (constructor sets default)
     * - Update royalty percentage based on market conditions
     * - Change receiver address (e.g., new treasury contract)
     * - Disable royalties (set feeNumerator to 0)
     */
    function setDefaultRoyalty(address receiver, uint96 feeNumerator) external onlyRole(DEFAULT_ADMIN_ROLE) {
        _setDefaultRoyalty(receiver, feeNumerator);
        emit RoyaltyUpdated(receiver, feeNumerator);
    }

    // ============================================
    // ERC20 RECOVERY FUNCTIONS (Safety Mechanism)
    // ============================================

    /**
     * @notice Recover ERC20 tokens accidentally sent to this contract
     * @dev This is a safety mechanism to recover tokens that users may accidentally send.
     *      The contract is designed to work exclusively with ETH, not ERC20 tokens.
     *      Only the Owner can recover tokens, preventing unauthorized access.
     *
     * @param tokenAddress Address of the ERC20 token contract to recover
     * @param amount Amount of tokens to recover (in token's smallest unit)
     *
     * Requirements:
     * - Caller must have DEFAULT_ADMIN_ROLE (Owner)
     * - Contract must have sufficient token balance
     * - Token transfer must succeed
     *
     * Emits: ERC20Recovered event with token address, recipient, and amount
     *
     * Security:
     * - Owner-only access prevents unauthorized token recovery
     * - Uses standard ERC20 transfer (no reentrancy risk for tokens)
     * - Does not affect ETH balances or core contract functionality
     *
     * Use Cases:
     * - User accidentally sends ERC20 tokens to the NFT contract
     * - Airdrops sent to the contract address
     * - Recovery of any ERC20-compatible tokens
     *
     * Note: This is a pure safety mechanism. The contract does not hold or
     *       require ERC20 tokens for any functionality. All payments are in ETH.
     */
    function recoverERC20(address tokenAddress, uint256 amount) external onlyRole(DEFAULT_ADMIN_ROLE) {
        // Transfer tokens to the caller (owner)
        IERC20(tokenAddress).transfer(msg.sender, amount);

        // Emit recovery event
        emit ERC20Recovered(tokenAddress, msg.sender, amount);
    }
}
