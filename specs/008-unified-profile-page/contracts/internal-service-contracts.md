# Internal Service Contracts: Unified Profile Page

**Date**: 2025-10-22

## Frontend-Backend Contracts

### Authored NFTs Flow

```
Frontend (Author Tab) → Backend API → Database
```

**Request**:
```typescript
GET /api/authors/${walletAddress}/tokens?page=${page}&limit=20
```

**Response**:
```typescript
interface AuthorTokensResponse {
  tokens: TokenResponse[];
  total: number;
  page: number;
  limit: number;
}
```

### Frontend-Blockchain Contract

```
Frontend (Collector Tab) → thirdweb SDK → RPC → Smart Contract
```

**Contract Methods Used**:
- `balanceOf(address owner) returns (uint256)`
- `tokenOfOwnerByIndex(address owner, uint256 index) returns (uint256)`
- `tokenURI(uint256 tokenId) returns (string)`

**thirdweb Extension**:
```typescript
const { data: nfts } = useReadContract(getOwnedNFTs, {
  contract: gliskContract,
  owner: walletAddress,
});
```

## Component Contracts

### Profile Page Props

```typescript
interface ProfileProps {
  // No props - uses wagmi useAccount for wallet address
}
```

### Tab Panel Internal Interface

```typescript
interface AuthorTabPanelProps {
  address: string;
}

interface CollectorTabPanelProps {
  address: string;
}
```

### NFT Grid Component

```typescript
interface NFTGridProps {
  nfts: (Token | NFTMetadata)[];
  isLoading: boolean;
  error?: string;
}
```

### Pagination Controls

```typescript
interface PaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  disabled: boolean;
}
```

## Validation Contracts

### Backend Input Validation

```python
# Wallet address: Checksummed Ethereum address
def validate_wallet_address(address: str) -> str:
    if len(address) != 42 or not address.startswith('0x'):
        raise ValueError("Invalid address format")
    return Web3.to_checksum_address(address)

# Pagination parameters
page: int = Query(1, ge=1)  # Must be >= 1
limit: int = Query(20, ge=1, le=100)  # Must be 1-100
```

### Frontend State Validation

```typescript
// Tab param validation
const validateTab = (tab: string | null): TabType => {
  return tab === 'collector' ? 'collector' : 'author';
};

// Pagination bounds
const canGoPrevious = currentPage > 1 && !isLoading;
const canGoNext = currentPage < totalPages && !isLoading;
```
