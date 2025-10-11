# Data Model: GLISK Smart Contract System

**Feature**: 001-full-smart-contract
**Date**: 2025-10-10
**Purpose**: Define contract state variables, data structures, and relationships for Season 0 NFT implementation

## Overview

This document defines the on-chain data model for the GliskNFT smart contract. All entities, state variables, and data structures are designed for gas efficiency, security, and alignment with the feature requirements.

---

## Core Entities

### 1. NFT Token

**Description**: Represents an individual minted GLISK blind box NFT.

**On-Chain Data:**
- **Token ID**: uint256 (sequential, starting from 1)
- **Owner**: address (inherited from ERC721)
- **Prompt Author**: address (custom mapping)
- **Metadata URI**: string (custom, supports reveal workflow)
- **Revealed Status**: bool (tracks if token has been permanently revealed)

**Storage Variables:**
```solidity
// Inherited from ERC721
// mapping(uint256 => address) private _owners;
// mapping(address => uint256) private _balances;

// Custom GliskNFT storage
mapping(uint256 => address) public tokenPromptAuthor;  // tokenId => author address
mapping(uint256 => string) private _tokenURIs;         // tokenId => metadata URI (revealed only)
mapping(uint256 => bool) private _revealed;            // tokenId => revealed status
string private _placeholderURI;                        // Default URI for unrevealed tokens
uint256 private _nextTokenId;                          // Sequential counter
```

**Relationships:**
- **1:1 with Owner**: Each token has exactly one owner (ERC721 standard)
- **1:1 with Prompt Author**: Each token is associated with one prompt author address
- **1:1 with URI**: Each revealed token has a unique metadata URI

**State Transitions:**
```
[Unminted] --mint()--> [Minted, Unrevealed (uses placeholderURI)]
[Unrevealed] --revealTokens()--> [Revealed (immutable URI)]
```

**Validation Rules:**
- Token ID must be > 0 and exist (_requireOwned)
- Prompt author must be valid address (0x0 allowed but discouraged)
- Revealed tokens cannot have URI changed again
- Unrevealed tokens always return placeholderURI

---

### 2. Prompt Author Rewards

**Description**: Tracks claimable reward balances for prompt authors who earn 50% of mint payments.

**On-Chain Data:**
- **Author Address**: address (key)
- **Claimable Balance**: uint256 (in wei)

**Storage Variables:**
```solidity
mapping(address => uint256) public authorClaimable;  // author => claimable balance
```

**Relationships:**
- **1:N with Tokens**: One author can be associated with many tokens
- **Independent**: Not tied to specific token IDs, accumulated across all mints

**State Transitions:**
```
[No Balance] --mint()--> [Balance Increases]
[Has Balance] --claimAuthorRewards()--> [Balance Reset to Zero]
[Balance > 0] --sweepUnclaimedRewards()--> [Balance Reset to Zero] (after season end)
```

**Validation Rules:**
- Balance increases by 50% of mint price × quantity per batch mint
- Claim transfers all balance and resets to zero
- Claim with zero balance is allowed (no revert)
- Sweep only allowed after seasonEndTime + CLAIM_PERIOD

---

### 3. Treasury Balance

**Description**: Platform-controlled funds accumulated from mint fees, direct payments, and royalties.

**On-Chain Data:**
- **Balance**: uint256 (in wei)

**Storage Variables:**
```solidity
uint256 public treasuryBalance;  // Accumulated platform funds
```

**Relationships:**
- **Global**: Single treasury balance for entire contract
- **Independent**: Not tied to specific tokens or authors

**State Transitions:**
```
[Balance = 0] --mint()--> [Balance += 50% of payment]
[Balance >= 0] --receive()--> [Balance += msg.value]
[Balance > 0] --withdrawTreasury()--> [Balance Reset to Zero]
[Balance >= 0] --sweepUnclaimedRewards()--> [Balance += swept amount]
```

**Validation Rules:**
- Treasury receives 50% of base mint payment (price × quantity)
- Treasury receives 100% of overpayment (msg.value - required payment)
- Treasury receives 100% of direct payments (via receive())
- Withdrawal transfers all balance and resets to zero
- Only Owner can withdraw

---

### 4. Mint Price

**Description**: Current cost to mint one NFT, stored in wei, updatable by Owner/Keeper.

**On-Chain Data:**
- **Price**: uint256 (in wei)

**Storage Variables:**
```solidity
uint256 public mintPrice;  // Cost per NFT in wei
```

**Relationships:**
- **Global**: Single price applies to all mints
- **Independent**: Not tied to specific tokens

**State Transitions:**
```
[Initial Price] --constructor()--> [Set at deployment]
[Current Price] --setMintPrice()--> [Updated Price]
```

**Validation Rules:**
- Set at contract deployment
- Can be updated by Owner or Keeper role
- Used for payment validation (msg.value >= mintPrice × quantity)
- Target: ~$0.05 USD equivalent in ETH/Base

---

### 5. Season State

**Description**: Tracks the lifecycle state of the season (active or ended).

**On-Chain Data:**
- **Season Ended**: bool (has seasonEnd been triggered)
- **Season End Time**: uint256 (timestamp when seasonEnd was called)
- **Claim Period**: uint256 constant (2 weeks = 14 days)

**Storage Variables:**
```solidity
bool public seasonEnded;                     // Has season been ended
uint256 public seasonEndTime;                // Timestamp of seasonEnd call
uint256 public constant CLAIM_PERIOD = 14 days;  // Grace period for author claims
```

**Relationships:**
- **Global**: Single season state for entire contract
- **Affects**: Minting (disabled when seasonEnded = true)
- **Affects**: Sweeping (enabled after seasonEndTime + CLAIM_PERIOD)

**State Transitions:**
```
[seasonEnded = false] --endSeason()--> [seasonEnded = true, seasonEndTime = now]
[Claims Active] --time passes--> [Claims Expired (after CLAIM_PERIOD)]
[Claims Expired] --sweepUnclaimedRewards()--> [Balances Moved to Treasury]
```

**Validation Rules:**
- Minting reverts if seasonEnded = true
- endSeason() can only be called once
- sweepUnclaimedRewards() requires seasonEnded = true AND block.timestamp >= seasonEndTime + CLAIM_PERIOD
- Authors can claim during and after CLAIM_PERIOD (no time restriction on claims)

---

### 6. Access Control Roles

**Description**: Role-based permissions for privileged operations.

**On-Chain Data:**
- **DEFAULT_ADMIN_ROLE**: bytes32(0) (Owner role, inherited from AccessControl)
- **KEEPER_ROLE**: keccak256("KEEPER_ROLE") (Limited operations role)

**Storage Variables:**
```solidity
// Inherited from OpenZeppelin AccessControl
// mapping(bytes32 => RoleData) private _roles;

bytes32 public constant KEEPER_ROLE = keccak256("KEEPER_ROLE");
```

**Role Permissions:**

| Operation | Owner (DEFAULT_ADMIN_ROLE) | Keeper (KEEPER_ROLE) |
|-----------|---------------------------|---------------------|
| Grant/Revoke Roles | ✅ | ❌ |
| Update Mint Price | ✅ | ✅ |
| Update Placeholder URI | ✅ | ❌ |
| Reveal Tokens (set URIs) | ✅ | ✅ |
| Withdraw Treasury | ✅ | ❌ |
| End Season | ✅ | ❌ |
| Sweep Unclaimed Rewards | ✅ | ❌ |
| Update Royalty | ✅ | ❌ |

**Relationships:**
- **N:M**: Multiple addresses can have multiple roles
- **Hierarchical**: Owner has all permissions, Keeper is limited

**Validation Rules:**
- Owner is set in constructor and can grant roles
- Only Owner can grant or revoke roles
- Role checks use `onlyRole()` modifier
- Operations revert if caller lacks required role

---

### 7. Royalty Configuration

**Description**: ERC-2981 royalty information for secondary sales.

**On-Chain Data:**
- **Receiver**: address (treasury address)
- **Fee Numerator**: uint96 (basis points, e.g., 250 = 2.5%)

**Storage Variables:**
```solidity
// Inherited from OpenZeppelin ERC2981
// RoyaltyInfo private _defaultRoyaltyInfo;

// Access via royaltyInfo(tokenId, salePrice) view function
```

**Relationships:**
- **Global**: Single default royalty applies to all tokens
- **Receiver**: Typically treasury address

**State Transitions:**
```
[Default Royalty] --constructor()--> [Set at deployment (2.5%, treasury)]
[Current Royalty] --setDefaultRoyalty()--> [Updated Royalty]
```

**Validation Rules:**
- Receiver must be valid address
- Fee numerator uses basis points (10000 = 100%)
- Recommended: 250 basis points (2.5%)
- Only Owner can update royalty

---

## Supporting Data Structures

### Batch Mint Parameters

**Description**: Input parameters for batch minting operation.

**Structure:**
```solidity
// Function signature (not a stored struct)
function mint(address promptAuthor, uint256 quantity) external payable;
```

**Fields:**
- **promptAuthor**: address - The prompt author to credit for this batch
- **quantity**: uint256 - Number of NFTs to mint (1 to MAX_BATCH_SIZE)
- **msg.value**: uint256 - ETH payment (must be >= mintPrice × quantity)

**Validation:**
- `quantity > 0` (cannot mint zero)
- `quantity <= MAX_BATCH_SIZE` (typically 50)
- `msg.value >= mintPrice * quantity` (sufficient payment)
- `!seasonEnded` (season must be active)

---

### Reveal Batch Parameters

**Description**: Input parameters for batch reveal operation.

**Structure:**
```solidity
// Function signature (not a stored struct)
function revealTokens(uint256[] calldata tokenIds, string[] calldata uris) external;
```

**Fields:**
- **tokenIds**: uint256[] - Array of token IDs to reveal
- **uris**: string[] - Corresponding metadata URIs (IPFS links)

**Validation:**
- `tokenIds.length == uris.length` (array length match)
- All token IDs must exist
- All tokens must be unrevealed (`!_revealed[tokenId]`)
- Only Owner or Keeper can execute

---

## Storage Layout Summary

**Optimization Considerations:**
- Use uint256 for counters and balances (EVM native size)
- Pack boolean flags together if possible (future optimization)
- Use mappings for dynamic O(1) lookups
- Avoid arrays for unbounded data (no author enumeration on-chain)

**Estimated Storage Slots:**

| Variable | Type | Slots | Notes |
|----------|------|-------|-------|
| _nextTokenId | uint256 | 1 | Sequential counter |
| mintPrice | uint256 | 1 | Wei amount |
| seasonEnded | bool | 1 | Can be packed |
| seasonEndTime | uint256 | 1 | Timestamp |
| treasuryBalance | uint256 | 1 | Wei amount |
| _placeholderURI | string | 1+ | Dynamic length |
| tokenPromptAuthor | mapping | N/A | Per token |
| _tokenURIs | mapping | N/A | Per revealed token |
| _revealed | mapping | N/A | Per token |
| authorClaimable | mapping | N/A | Per author |
| ERC721 state | inherited | 2+ | Owners, balances |
| AccessControl state | inherited | 1+ | Role data |
| ERC2981 state | inherited | 1 | Royalty info |

**Total Fixed Slots**: ~10-15 slots
**Dynamic Mappings**: Scale with usage (tokens, authors)

---

## Invariants

**Critical Invariants (must always hold):**

1. **Token ID Uniqueness**: No two tokens share the same token ID
   ```
   ∀ token IDs: unique and sequential starting from 1
   ```

2. **Balance Conservation**: Sum of all balances equals contract balance
   ```
   contract.balance == treasuryBalance + Σ(authorClaimable[author])
   ```

3. **Reveal Immutability**: Revealed tokens cannot be unrevealed
   ```
   ∀ tokenId: if _revealed[tokenId] == true, then _tokenURIs[tokenId] is permanent
   ```

4. **Season End Finality**: Once season ends, minting is permanently disabled
   ```
   if seasonEnded == true: mint() always reverts
   ```

5. **Role Hierarchy**: Owner has all permissions that Keeper has
   ```
   ∀ operation: if Keeper can do X, then Owner can do X
   ```

6. **Payment Distribution**: Every mint splits payment 50/50 (base amount only)
   ```
   ∀ mint: authorShare + treasuryShare == mintPrice × quantity (before overpayment)
   ```

---

## Events

**Complete Event Definitions:**

```solidity
// Minting events
event BatchMinted(
    address indexed minter,
    address indexed promptAuthor,
    uint256 indexed startTokenId,
    uint256 quantity,
    uint256 totalPaid
);

// Reward events
event AuthorClaimed(address indexed author, uint256 amount);
event TreasuryWithdrawn(address indexed recipient, uint256 amount);
event UnclaimedRewardsSwept(uint256 totalAmount, uint256 authorsCount);

// Admin events
event MintPriceUpdated(uint256 oldPrice, uint256 newPrice);
event PlaceholderURIUpdated(string newURI);
event TokensRevealed(uint256[] tokenIds);
event SeasonEnded(uint256 timestamp);
event RoyaltyUpdated(address receiver, uint96 feeNumerator);

// Payment events
event DirectPaymentReceived(address indexed sender, uint256 amount);

// Role events (inherited from AccessControl)
// event RoleGranted(bytes32 indexed role, address indexed account, address indexed sender);
// event RoleRevoked(bytes32 indexed role, address indexed account, address indexed sender);
```

**Indexing Strategy:**
- **Indexed fields**: Addresses (minter, author, recipient), start token IDs
- **Non-indexed fields**: Amounts, quantities, arrays, strings
- **Limit**: Max 3 indexed parameters per event (EVM limitation)

---

## Gas Considerations

**Estimated Gas Costs (Base L2):**

| Operation | Gas Estimate | Notes |
|-----------|--------------|-------|
| Single mint | ~80-100k | Includes _safeMint + storage |
| Batch mint (50 NFTs) | ~3.5-4.5M | Linear scaling |
| Claim author rewards | ~50-60k | Transfer + storage update |
| Withdraw treasury | ~50-60k | Transfer + storage update |
| Update mint price | ~30-40k | Storage update |
| Reveal tokens (10) | ~200-300k | String storage + bool updates |
| End season | ~30-40k | Bool + uint256 storage |
| Sweep rewards (100 authors) | ~2-3M | Batch iterations + transfers |

**Optimization Opportunities:**
- Use uint96 for mintPrice (saves gas if < 2^96 wei)
- Pack seasonEnded + seasonEndTime into single slot
- Batch operations wherever possible (already implemented)

---

## Summary

This data model provides:
- **Clear entity definitions** with storage variables and relationships
- **State transition diagrams** for each entity
- **Validation rules** enforced at contract level
- **Storage layout** optimized for gas efficiency
- **Critical invariants** for testing and security
- **Comprehensive events** for off-chain indexing

All entities align with the feature requirements in spec.md and support the implementation patterns defined in research.md.

**Next Steps:**
1. Generate Solidity interface contracts based on this data model
2. Create quickstart.md with deployment and usage guide
3. Update agent context with technology stack
