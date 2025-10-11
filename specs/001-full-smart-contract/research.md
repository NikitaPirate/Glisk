# Research: GLISK Smart Contract System

**Feature**: 001-full-smart-contract
**Date**: 2025-10-10
**Purpose**: Resolve technical unknowns and establish best practices for Season 0 NFT contract implementation

## Overview

This document consolidates research findings for implementing the GLISK Season 0 smart contract system. All NEEDS CLARIFICATION items from the Technical Context have been resolved through industry best practices, OpenZeppelin patterns, and Base L2 considerations.

---

## 1. Solidity Version & Compiler Settings

### Decision: Solidity ^0.8.20 with optimizer enabled

**Rationale:**
- Solidity 0.8.20+ includes built-in overflow protection (no SafeMath needed)
- Latest stable version with bug fixes and gas optimizations
- Compatible with Base L2 (EVM-equivalent chain)
- OpenZeppelin Contracts v5.x requires Solidity ^0.8.20

**Compiler Configuration:**
```toml
[profile.default]
solc_version = "0.8.20"
optimizer = true
optimizer_runs = 200
via_ir = false  # Keep IR disabled for initial implementation unless gas issues arise
```

**Alternatives Considered:**
- Solidity 0.8.19: Rejected - missing latest security improvements
- Higher optimizer_runs (1000+): Rejected - increases deployment cost without significant runtime savings for our use case
- via_ir = true: Rejected - adds compilation complexity; reserve for optimization phase if needed

---

## 2. ERC-721 Implementation Pattern

### Decision: Inherit from OpenZeppelin ERC721 with custom extensions

**Rationale:**
- Battle-tested, audited implementation (industry standard)
- Reduces attack surface by using proven code
- ERC721 base provides standard NFT functionality
- Can selectively override functions for custom behavior (e.g., tokenURI)

**Implementation Pattern:**
```solidity
import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721Enumerable.sol"; // Optional
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/common/ERC2981.sol";

contract GliskNFT is ERC721, AccessControl, ReentrancyGuard, ERC2981 {
    // Custom implementation
}
```

**Extensions Used:**
- **ERC721**: Core NFT functionality (ownership, transfers, approvals)
- **AccessControl**: Role-based permissions (Owner, Keeper)
- **ReentrancyGuard**: Protects payment functions from reentrancy attacks
- **ERC2981**: Royalty standard for marketplace integration

**Extensions Considered but Rejected:**
- **ERC721Enumerable**: Rejected - high gas cost for minting, not needed for our use case (no on-chain iteration required)
- **ERC721URIStorage**: Rejected - provides per-token URI storage but we'll implement custom logic for reveal workflow
- **ERC721Burnable**: Rejected - no burn functionality in Season 0 requirements

**Alternatives Considered:**
- Solmate ERC721: Rejected - more gas-efficient but less battle-tested, no AccessControl integration
- Custom ERC721 from scratch: Rejected - violates "Simplicity First" principle, introduces security risk

---

## 3. Access Control Pattern

### Decision: OpenZeppelin AccessControl with two roles (DEFAULT_ADMIN_ROLE, KEEPER_ROLE)

**Rationale:**
- Flexible role-based system (better than Ownable for multi-role scenarios)
- DEFAULT_ADMIN_ROLE (Owner): Full control, can grant/revoke roles
- KEEPER_ROLE: Limited operations (URI updates, price updates)
- Built-in role management, event emission, and access checks

**Role Definitions:**
```solidity
bytes32 public constant KEEPER_ROLE = keccak256("KEEPER_ROLE");
// DEFAULT_ADMIN_ROLE is inherited from AccessControl (bytes32(0))
```

**Access Patterns:**
- Owner operations: `onlyRole(DEFAULT_ADMIN_ROLE)` or custom `onlyOwner` modifier
- Keeper operations: `onlyRole(KEEPER_ROLE)`
- Dual permission: Use `||` or separate functions

**Alternatives Considered:**
- Ownable: Rejected - doesn't support multiple roles, would need separate Keeper logic
- Custom access control: Rejected - reinventing the wheel, violates "Simplicity First"
- Ownable2Step: Rejected - good for ownership transfer but doesn't support keeper role

---

## 4. Payment Distribution Pattern

### Decision: Pull-over-push with claimable balances tracked in mapping

**Rationale:**
- **Security**: Pull pattern prevents reentrancy attacks and DoS via failed transfers
- **Gas Efficiency**: Single storage update per mint, claim transfers happen separately
- **Flexibility**: Authors claim rewards when they choose (no forced transfers during mint)

**Implementation Pattern:**
```solidity
// Storage
mapping(address => uint256) public authorClaimable;
uint256 public treasuryBalance;

// Mint function updates balances
function mint() external payable {
    uint256 authorShare = msg.value / 2;
    uint256 treasuryShare = msg.value - authorShare; // Handles odd amounts

    authorClaimable[promptAuthor] += authorShare;
    treasuryBalance += treasuryShare;

    emit Minted(...);
}

// Authors pull rewards
function claimAuthorRewards() external nonReentrant {
    uint256 amount = authorClaimable[msg.sender];
    authorClaimable[msg.sender] = 0;  // Update state before transfer

    (bool success, ) = msg.sender.call{value: amount}("");
    require(success, "Transfer failed");

    emit AuthorClaimed(msg.sender, amount);
}
```

**Alternatives Considered:**
- Push pattern (transfer during mint): Rejected - vulnerable to reentrancy and DoS attacks
- Escrow contract: Rejected - adds unnecessary complexity for our use case
- ERC20 reward tokens: Rejected - requires additional token contract, violates simplicity

---

## 5. Batch Minting Implementation

### Decision: Loop-based minting within single transaction with quantity parameter

**Rationale:**
- Simple implementation: loop from 0 to quantity
- Gas-efficient for users: single transaction cost instead of N transactions
- Sequential token IDs: easy to track and manage

**Implementation Pattern:**
```solidity
uint256 private _nextTokenId = 1; // Start at 1 (0 is invalid)

function mint(address promptAuthor, uint256 quantity) external payable nonReentrant {
    require(quantity > 0 && quantity <= MAX_BATCH_SIZE, "Invalid quantity");
    require(msg.value >= mintPrice * quantity, "Insufficient payment");
    require(!seasonEnded, "Season ended");

    // Payment distribution
    uint256 totalPrice = mintPrice * quantity;
    uint256 authorShare = totalPrice / 2;
    uint256 treasuryShare = totalPrice - authorShare;

    // Handle overpayment
    if (msg.value > totalPrice) {
        treasuryShare += (msg.value - totalPrice);
    }

    authorClaimable[promptAuthor] += authorShare;
    treasuryBalance += treasuryShare;

    // Mint tokens
    uint256 startTokenId = _nextTokenId;
    for (uint256 i = 0; i < quantity; i++) {
        uint256 tokenId = _nextTokenId++;
        _safeMint(msg.sender, tokenId);
        tokenPromptAuthor[tokenId] = promptAuthor;
    }

    emit BatchMinted(msg.sender, promptAuthor, startTokenId, quantity, msg.value);
}
```

**Gas Limit Consideration:**
- Set MAX_BATCH_SIZE = 50 (conservative limit for Base L2)
- Each _safeMint costs ~50-70k gas
- Total for 50 NFTs: ~2.5-3.5M gas (well under Base's 30M gas limit)

**Alternatives Considered:**
- ERC721A (Azuki's implementation): Rejected - optimizes for sequential mints but adds complexity, our batch sizes don't justify it
- Merkle tree minting: Rejected - for allowlist scenarios, not applicable here
- Off-chain coordination with single on-chain commit: Rejected - over-engineered for our simple mint flow

---

## 6. NFT Reveal Workflow

### Decision: Two-tier URI system (placeholder + per-token revealed URIs)

**Rationale:**
- Supports blind box experience (all start with placeholder)
- Allows batch reveal via URI updates
- Immutable after reveal for reliability
- Owner can update placeholder anytime for unrevealed tokens

**Implementation Pattern:**
```solidity
// Storage
string private _placeholderURI;
mapping(uint256 => string) private _tokenURIs;
mapping(uint256 => bool) private _revealed;

// Constructor sets initial placeholder
constructor(string memory placeholderURI_) {
    _placeholderURI = placeholderURI_;
}

// Override tokenURI from ERC721
function tokenURI(uint256 tokenId) public view override returns (string memory) {
    _requireOwned(tokenId);

    if (_revealed[tokenId]) {
        return _tokenURIs[tokenId];
    }
    return _placeholderURI;
}

// Update placeholder (affects all unrevealed)
function setPlaceholderURI(string memory newURI) external onlyRole(DEFAULT_ADMIN_ROLE) {
    _placeholderURI = newURI;
    emit PlaceholderURIUpdated(newURI);
}

// Batch reveal
function revealTokens(uint256[] calldata tokenIds, string[] calldata uris)
    external
    onlyRole(KEEPER_ROLE)
{
    require(tokenIds.length == uris.length, "Length mismatch");

    for (uint256 i = 0; i < tokenIds.length; i++) {
        require(!_revealed[tokenIds[i]], "Already revealed");
        _tokenURIs[tokenIds[i]] = uris[i];
        _revealed[tokenIds[i]] = true;
    }

    emit TokensRevealed(tokenIds);
}
```

**Alternatives Considered:**
- ERC721URIStorage: Rejected - allows URI updates anytime, we need immutability after reveal
- Single global URI with token ID appended: Rejected - doesn't support placeholder/reveal workflow
- IPFS CID stored on-chain: Rejected - CIDs are long, expensive to store individually

---

## 7. Season End & Reward Sweep

### Decision: Two-step process (seasonEnd trigger → 2-week countdown → sweepUnclaimedRewards)

**Rationale:**
- Protects author rewards with grace period
- Simple boolean + timestamp pattern
- Prevents premature sweep with require checks

**Implementation Pattern:**
```solidity
// Storage
bool public seasonEnded;
uint256 public seasonEndTime;
uint256 public constant CLAIM_PERIOD = 14 days;

// Step 1: Owner triggers season end
function endSeason() external onlyRole(DEFAULT_ADMIN_ROLE) {
    require(!seasonEnded, "Already ended");
    seasonEnded = true;
    seasonEndTime = block.timestamp;
    emit SeasonEnded(seasonEndTime);
}

// Step 2: Owner sweeps after countdown
function sweepUnclaimedRewards() external onlyRole(DEFAULT_ADMIN_ROLE) {
    require(seasonEnded, "Season not ended");
    require(block.timestamp >= seasonEndTime + CLAIM_PERIOD, "Claim period active");

    // Sweep all unclaimed author balances
    // NOTE: This requires iterating or tracking authors (gas consideration)
    // Alternative: Sweep specific authors in batches

    emit UnclaimedRewardsSwept(totalSwept);
}
```

**Challenge: Author Tracking**
- Problem: No efficient way to iterate all authors without enumeration
- Solutions:
  1. **Off-chain indexing** (recommended): Backend indexes all mint events, provides author list to sweep function
  2. **Batch sweep with address array**: `sweepUnclaimedRewards(address[] calldata authors)`
  3. **EnumerableSet of authors**: Track all authors on-chain (gas-intensive for writes)

**Recommended Approach**: Batch sweep with address array provided off-chain
```solidity
function sweepUnclaimedRewards(address[] calldata authors) external onlyRole(DEFAULT_ADMIN_ROLE) {
    require(seasonEnded, "Season not ended");
    require(block.timestamp >= seasonEndTime + CLAIM_PERIOD, "Claim period active");

    uint256 totalSwept = 0;
    for (uint256 i = 0; i < authors.length; i++) {
        uint256 amount = authorClaimable[authors[i]];
        if (amount > 0) {
            authorClaimable[authors[i]] = 0;
            totalSwept += amount;
        }
    }

    treasuryBalance += totalSwept;
    emit UnclaimedRewardsSwept(totalSwept, authors.length);
}
```

**Alternatives Considered:**
- Automatic sweep on claim after period: Rejected - requires checks on every claim, gas-inefficient
- Individual author sweep: Rejected - requires many transactions, not user-friendly
- No sweep mechanism: Rejected - leaves funds locked forever

---

## 8. Treasury Withdrawal Pattern

### Decision: Simple withdrawal function with nonReentrant protection

**Rationale:**
- Owner-only operation
- Pull pattern for security
- Withdraws all treasury balance in one transaction

**Implementation Pattern:**
```solidity
function withdrawTreasury() external onlyRole(DEFAULT_ADMIN_ROLE) nonReentrant {
    uint256 amount = treasuryBalance;
    require(amount > 0, "No balance");

    treasuryBalance = 0;  // Update state before transfer

    (bool success, ) = msg.sender.call{value: amount}("");
    require(success, "Transfer failed");

    emit TreasuryWithdrawn(msg.sender, amount);
}

// Accept direct payments to contract (goes to treasury)
receive() external payable {
    treasuryBalance += msg.value;
    emit DirectPaymentReceived(msg.sender, msg.value);
}
```

**Alternatives Considered:**
- Partial withdrawals: Rejected - not needed, adds complexity
- Scheduled withdrawals: Rejected - over-engineered
- Push to designated treasury address: Rejected - less flexible than pull pattern

---

## 9. ERC-2981 Royalty Implementation

### Decision: OpenZeppelin ERC2981 with default royalty to treasury

**Rationale:**
- Standard marketplace integration
- Simple default royalty (applies to all tokens)
- Treasury receives all royalty payments (single receiver)

**Implementation Pattern:**
```solidity
import "@openzeppelin/contracts/token/common/ERC2981.sol";

contract GliskNFT is ERC721, ERC2981, ... {

    constructor(...) {
        // Set default royalty: 2.5% (250 basis points) to treasury address
        _setDefaultRoyalty(treasuryAddress, 250);
    }

    // Update royalty if needed
    function setDefaultRoyalty(address receiver, uint96 feeNumerator)
        external
        onlyRole(DEFAULT_ADMIN_ROLE)
    {
        _setDefaultRoyalty(receiver, feeNumerator);
        emit RoyaltyUpdated(receiver, feeNumerator);
    }

    // Required override for multiple inheritance
    function supportsInterface(bytes4 interfaceId)
        public
        view
        override(ERC721, ERC2981, AccessControl)
        returns (bool)
    {
        return super.supportsInterface(interfaceId);
    }
}
```

**Alternatives Considered:**
- Per-token royalty: Rejected - would split between author and treasury, but ERC2981 only supports single receiver per token
- Custom royalty registry: Rejected - over-engineered, marketplace support is minimal anyway
- No royalty support: Rejected - easy to implement, potential future revenue

---

## 10. Event Design for Off-Chain Indexing

### Decision: Comprehensive events for all critical state changes

**Rationale:**
- Backend services need to monitor mints for image generation
- Events enable off-chain indexing (The Graph, custom indexer)
- Provides audit trail for payments and rewards

**Key Events:**
```solidity
// Minting
event BatchMinted(
    address indexed minter,
    address indexed promptAuthor,
    uint256 indexed startTokenId,
    uint256 quantity,
    uint256 totalPaid
);

// Rewards
event AuthorClaimed(address indexed author, uint256 amount);
event TreasuryWithdrawn(address indexed recipient, uint256 amount);
event UnclaimedRewardsSwept(uint256 amount, uint256 authorsCount);

// Admin
event MintPriceUpdated(uint256 oldPrice, uint256 newPrice);
event PlaceholderURIUpdated(string newURI);
event TokensRevealed(uint256[] tokenIds);
event SeasonEnded(uint256 timestamp);

// Payments
event DirectPaymentReceived(address indexed sender, uint256 amount);
```

**Best Practices:**
- Use `indexed` for filterable fields (addresses, IDs)
- Limit to 3 indexed parameters per event (EVM limitation)
- Include both old and new values for updates
- Emit before external calls (when possible)

---

## 11. Testing Strategy

### Decision: Foundry-based testing with unit + integration coverage

**Rationale:**
- Foundry provides fast, gas-efficient testing
- Solidity-based tests (no JS/TS context switching)
- Built-in fuzzing and invariant testing
- Anvil for local chain simulation

**Test Structure:**
```
test/
├── unit/
│   ├── GliskNFT.t.sol               # Core functionality
│   ├── GliskNFT.Minting.t.sol       # Batch minting tests
│   ├── GliskNFT.Payments.t.sol      # Payment distribution
│   ├── GliskNFT.Reveal.t.sol        # URI and reveal logic
│   ├── GliskNFT.Season.t.sol        # Season end and sweep
│   └── GliskNFT.Access.t.sol        # Role-based access
└── integration/
    └── GliskNFT.integration.t.sol   # End-to-end scenarios
```

**Coverage Targets:**
- Unit tests: 100% function coverage
- Integration tests: All user scenarios from spec.md
- Fuzz tests: Payment calculations, batch sizes
- Invariant tests: Balance accounting (sum of author balances + treasury = contract balance)

**Alternatives Considered:**
- Hardhat: Rejected - slower test execution, TypeScript overhead
- Truffle: Rejected - outdated, less active development
- Hybrid (Foundry + Hardhat): Rejected - unnecessary complexity for our scope

---

## 12. Deployment & Verification Strategy

### Decision: Foundry scripts with environment-based configuration

**Rationale:**
- Foundry script for automated deployment
- Environment variables for network selection
- Built-in verification via `forge verify-contract`

**Deployment Flow:**
```solidity
// script/Deploy.s.sol
contract DeployGliskNFT is Script {
    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        string memory placeholderURI = vm.envString("PLACEHOLDER_URI");
        uint256 initialPrice = vm.envUint("INITIAL_MINT_PRICE");

        vm.startBroadcast(deployerPrivateKey);

        GliskNFT nft = new GliskNFT(
            "GLISK Season 0",
            "GLISK0",
            placeholderURI,
            initialPrice
        );

        vm.stopBroadcast();

        console.log("GliskNFT deployed to:", address(nft));
    }
}
```

**Network Configuration (foundry.toml):**
```toml
[rpc_endpoints]
base_mainnet = "${BASE_MAINNET_RPC_URL}"
base_sepolia = "${BASE_SEPOLIA_RPC_URL}"

[etherscan]
base_mainnet = { key = "${BASESCAN_API_KEY}", url = "https://api.basescan.org/api" }
base_sepolia = { key = "${BASESCAN_API_KEY}", url = "https://api-sepolia.basescan.org/api" }
```

**Deployment Commands:**
```bash
# Testnet
forge script script/Deploy.s.sol --rpc-url base_sepolia --broadcast --verify

# Mainnet
forge script script/Deploy.s.sol --rpc-url base_mainnet --broadcast --verify
```

**Alternatives Considered:**
- Hardhat Ignition: Rejected - requires Hardhat setup
- Manual deployment: Rejected - error-prone, not repeatable
- Remix: Rejected - not scriptable, difficult to version control

---

## 13. Gas Optimization Strategies

### Decision: Target optimizations with measurement, no premature optimization

**Rationale:**
- Base L2 has lower gas costs than Ethereum mainnet
- Prioritize security and clarity over gas savings
- Optimize only if measurements show need

**Measurement Approach:**
```bash
forge test --gas-report
```

**Targeted Optimizations (if needed):**
1. **Batch operations**: Already using batch mint
2. **Storage packing**: Use uint96 for prices if < 2^96 wei
3. **Cached storage reads**: Store frequently-read values in memory
4. **Short-circuit logic**: Order require checks by likelihood of failure

**Example Storage Packing:**
```solidity
// Instead of:
uint256 public mintPrice;
bool public seasonEnded;
uint256 public seasonEndTime;

// Pack into fewer slots:
uint96 public mintPrice;          // Slot 1 (96 bits)
bool public seasonEnded;           // Slot 1 (8 bits)
uint152 private _padding;          // Slot 1 (152 bits unused)
uint256 public seasonEndTime;      // Slot 2
```

**Anti-Patterns to Avoid:**
- Assembly unless absolutely necessary
- Unchecked arithmetic (security risk)
- Removing SafeMath (Solidity 0.8+ has built-in checks)

**Alternatives Considered:**
- Aggressive optimization upfront: Rejected - violates "Clear Over Clever" principle
- No optimization: Rejected - may lead to poor user experience if costs are high
- Custom EVM tricks: Rejected - increases audit complexity and risk

---

## 14. Security Considerations

### Decision: Defense-in-depth with OpenZeppelin + manual review + testing

**Rationale:**
- Use battle-tested libraries
- Follow checks-effects-interactions pattern
- Comprehensive test coverage
- Manual security review before mainnet

**Security Checklist:**
- [x] **Reentrancy**: Use ReentrancyGuard on all payable functions
- [x] **Access Control**: Use AccessControl for role verification
- [x] **Integer Overflow**: Solidity 0.8+ has built-in checks
- [x] **Pull over Push**: Use claimable balances, not direct transfers in mint
- [x] **State Before External Calls**: Update state before transfers
- [x] **Input Validation**: Check quantity > 0, payment >= required, etc.
- [x] **Event Emission**: Emit events before external calls when possible
- [x] **Gas Limits**: Set MAX_BATCH_SIZE to prevent DoS

**Known Vulnerabilities to Prevent:**
1. **Reentrancy in claim**: Use ReentrancyGuard + state-before-transfer
2. **DoS via revert in batch**: Use pull pattern for rewards
3. **Unchecked transfers**: Use require(success) on .call{value}
4. **Role escalation**: Ensure only admin can grant roles
5. **Token ID collision**: Use sequential counter

**Pre-Deployment Security Steps:**
1. Internal code review against OWASP smart contract top 10
2. Slither static analysis
3. Foundry invariant testing
4. Testnet deployment with stress testing
5. Consider external audit for mainnet (budget permitting)

---

## Summary of Decisions

| Topic | Decision | Rationale |
|-------|----------|-----------|
| Solidity Version | 0.8.20 with optimizer | Latest stable, OpenZeppelin v5 compatible |
| ERC-721 Base | OpenZeppelin ERC721 | Battle-tested, reduces attack surface |
| Access Control | AccessControl (2 roles) | Flexible multi-role support |
| Payment Pattern | Pull-over-push with mappings | Security and gas efficiency |
| Batch Minting | Loop-based, max 50 NFTs | Simple, gas-efficient, safe limits |
| Reveal Workflow | Placeholder + per-token URIs | Supports blind box experience |
| Season End | Two-step with 2-week countdown | Author protection with grace period |
| Treasury | Single withdrawal function | Simple, secure |
| Royalties | ERC2981 default 2.5% | Standard marketplace integration |
| Events | Comprehensive emission | Enables off-chain indexing |
| Testing | Foundry unit + integration | Fast, Solidity-native |
| Deployment | Foundry scripts | Automated, verifiable |
| Gas Optimization | Measure first, optimize selectively | Balance clarity and cost |
| Security | OpenZeppelin + testing + review | Defense-in-depth approach |

---

## Next Steps (Phase 1)

1. Generate `data-model.md` with contract state variables and structures
2. Create Solidity interface/signature contracts in `contracts/` directory
3. Generate `quickstart.md` with setup, deployment, and usage instructions
4. Update agent context with technology stack

All research decisions are now resolved and ready for design phase.
