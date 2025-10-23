import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  useAccount,
  useReadContract,
  useWriteContract,
  useWaitForTransactionReceipt,
  useChainId,
  usePublicClient,
} from 'wagmi'
import { useQuery } from '@tanstack/react-query'
import { isAddress, parseEventLogs } from 'viem'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { CONTRACT_ADDRESS, GLISK_NFT_ABI } from '@/lib/contract'
import { TokenRevealCard } from '@/components/TokenRevealCard'
import { useTokenPolling } from '@/hooks/useTokenPolling'
import { NFTGrid } from '@/components/NFTGrid'

type TransactionStatus = 'idle' | 'waitingApproval' | 'pending' | 'success' | 'failed' | 'cancelled'

interface TokenDTO {
  token_id: number
  status: string
  image_cid: string | null
  metadata_cid: string | null
  image_url: string | null
  generation_attempts: number
  generation_error: string | null
  reveal_tx_hash: string | null
  created_at: string
}

interface TokensResponse {
  tokens: TokenDTO[]
  total: number
  offset: number
  limit: number
}

async function fetchAuthorTokens(walletAddress: string, page: number): Promise<TokensResponse> {
  const offset = (page - 1) * 20
  const response = await fetch(`/api/authors/${walletAddress}/tokens?offset=${offset}&limit=20`)

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${await response.text()}`)
  }

  return response.json()
}

export function CreatorMintPage() {
  const { creatorAddress } = useParams<{ creatorAddress: string }>()
  const { isConnected, address: connectedWallet } = useAccount()
  const chainId = useChainId()
  const navigate = useNavigate()
  const publicClient = usePublicClient()
  const [quantity, setQuantity] = useState(1)
  const [mintedTokenIds, setMintedTokenIds] = useState<number[]>([]) // Token IDs from BatchMinted event
  const [nftPage, setNftPage] = useState(1)

  // Validate creator address
  const isCreatorAddressValid = creatorAddress ? isAddress(creatorAddress) : false

  // Read mint price from contract
  const {
    data: mintPrice,
    error: mintPriceError,
    isLoading: isMintPriceLoading,
  } = useReadContract({
    address: CONTRACT_ADDRESS,
    abi: GLISK_NFT_ABI,
    functionName: 'mintPrice',
  }) as { data: bigint | undefined; error: Error | null; isLoading: boolean }

  // Write contract hook for minting
  const {
    writeContract,
    data: hash,
    isPending: isWritePending,
    error: writeError,
  } = useWriteContract()

  // Wait for transaction receipt
  const {
    isLoading: isConfirming,
    isSuccess: isConfirmed,
    error: receiptError,
    data: receipt,
  } = useWaitForTransactionReceipt({
    hash,
  })

  // Parse BatchMinted event from transaction receipt
  useEffect(() => {
    if (!receipt || !publicClient) return

    try {
      // Parse event logs to extract token IDs
      const logs = parseEventLogs({
        abi: GLISK_NFT_ABI,
        eventName: 'BatchMinted',
        logs: receipt.logs,
      })

      if (logs.length > 0) {
        const batchMintedEvent = logs[0] as any // Type assertion for event args
        const args = batchMintedEvent.args

        if (args && args.startTokenId !== undefined && args.quantity !== undefined) {
          const startTokenId = Number(args.startTokenId)
          const mintQuantity = Number(args.quantity)

          // Generate array of token IDs: [startTokenId, startTokenId+1, ...]
          const tokenIds = Array.from({ length: mintQuantity }, (_, i) => startTokenId + i)
          setMintedTokenIds(tokenIds)

          console.log('[CreatorMintPage] BatchMinted event parsed:', {
            startTokenId,
            quantity: mintQuantity,
            tokenIds,
          })
        }
      }
    } catch (error) {
      console.error('[CreatorMintPage] Failed to parse BatchMinted event:', error)
    }
  }, [receipt, publicClient])

  // Poll for token status updates
  const {
    tokens,
    isPolling,
    allRevealed,
    error: pollingError,
  } = useTokenPolling(
    mintedTokenIds,
    connectedWallet,
    isConfirmed && mintedTokenIds.length > 0 // Enable polling after mint success
  )

  // Fetch author's NFT collection
  const {
    data: nftData,
    error: nftError,
    isLoading: nftLoading,
  } = useQuery({
    queryKey: ['creator-nfts', creatorAddress, nftPage],
    queryFn: () => fetchAuthorTokens(creatorAddress!, nftPage),
    enabled: !!creatorAddress && isCreatorAddressValid,
    staleTime: 30000,
  })

  const totalPages = Math.ceil((nftData?.total || 0) / 20)

  /**
   * Handles quantity input changes with validation
   * - Ensures quantity is always between 1-10
   * - Handles empty input by resetting to 1
   * - Ignores non-numeric input (NaN)
   */
  const handleQuantityChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value

    // Handle empty input
    if (value === '') {
      setQuantity(1)
      return
    }

    // Parse and validate
    const num = parseInt(value, 10)
    if (isNaN(num)) {
      return
    }

    // Clamp to valid range (1-10)
    const clamped = Math.max(1, Math.min(10, num))
    setQuantity(clamped)
  }

  const handleMint = () => {
    if (!creatorAddress || !mintPrice) return

    writeContract({
      address: CONTRACT_ADDRESS,
      abi: GLISK_NFT_ABI,
      functionName: 'mint',
      args: [creatorAddress as `0x${string}`, BigInt(quantity)],
      value: mintPrice * BigInt(quantity),
    })
  }

  /**
   * Derives transaction status from wagmi hooks state
   * Priority order (from highest to lowest):
   * 1. waitingApproval - User needs to approve in wallet
   * 2. cancelled - User rejected transaction
   * 3. failed - Transaction failed (write error or receipt error)
   * 4. success - Transaction confirmed on-chain
   * 5. pending - Transaction submitted, waiting for confirmation
   * 6. idle - No active transaction
   */
  const getTransactionStatus = (): TransactionStatus => {
    if (isWritePending) return 'waitingApproval'
    if (
      writeError?.message.includes('User rejected') ||
      writeError?.message.includes('User denied')
    )
      return 'cancelled'
    if (writeError) return 'failed'
    if (isConfirmed) return 'success'
    if (receiptError) return 'failed'
    if (isConfirming) return 'pending'
    return 'idle'
  }

  const status = getTransactionStatus()

  // Status message component
  const StatusMessage = () => {
    switch (status) {
      case 'waitingApproval':
        return (
          <div className="p-4 bg-blue-50 border border-blue-200 rounded">
            <p className="text-blue-800">Please approve the transaction in your wallet</p>
          </div>
        )
      case 'pending':
        return (
          <div className="p-4 bg-blue-50 border border-blue-200 rounded">
            <p className="text-blue-800">Minting... waiting for confirmation</p>
          </div>
        )
      case 'success':
        return (
          <div className="p-4 bg-green-50 border border-green-200 rounded">
            <p className="text-green-800">Success! NFTs minted.</p>
            {mintedTokenIds.length > 0 && (
              <p className="text-green-700 text-sm mt-1">Token IDs: {mintedTokenIds.join(', ')}</p>
            )}
          </div>
        )
      case 'cancelled':
        return (
          <div className="p-4 bg-yellow-50 border border-yellow-200 rounded">
            <p className="text-yellow-800">Transaction cancelled</p>
          </div>
        )
      case 'failed':
        return (
          <div className="p-4 bg-red-50 border border-red-200 rounded">
            <p className="text-red-800">
              Error: {receiptError?.message || writeError?.message || 'Transaction failed'}
            </p>
          </div>
        )
      default:
        return null
    }
  }

  if (!creatorAddress) {
    return (
      <div className="container mx-auto px-4 py-8">
        <p className="text-red-600">Error: No creator address provided</p>
      </div>
    )
  }

  if (!isCreatorAddressValid) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="p-4 bg-red-50 border border-red-200 rounded">
          <p className="text-red-800 font-semibold">Invalid creator address</p>
          <p className="text-red-700 mt-2">
            The address "{creatorAddress}" is not a valid Ethereum address.
          </p>
          <p className="text-red-700 mt-1 text-sm">
            Address must be a 40-character hex string starting with "0x" (e.g., 0x1234...5678)
          </p>
        </div>
      </div>
    )
  }

  // Network validation
  const isWrongNetwork = chainId !== 84532

  return (
    <div className="container mx-auto px-4 py-8 max-w-2xl">
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold mb-2">Mint NFT</h1>
          <p className="text-gray-600">Minting for creator: {creatorAddress}</p>
        </div>

        {!isConnected && (
          <div className="p-4 bg-blue-50 border border-blue-200 rounded">
            <p className="text-blue-800">Please connect your wallet to continue</p>
          </div>
        )}

        {isConnected && isWrongNetwork && (
          <div className="p-4 bg-yellow-50 border border-yellow-200 rounded">
            <p className="text-yellow-800">
              Please switch to Base Sepolia network (Chain ID: 84532)
            </p>
          </div>
        )}

        {isConnected && !isWrongNetwork && (
          <div className="space-y-4">
            {isMintPriceLoading && (
              <div className="p-4 bg-gray-50 border border-gray-200 rounded">
                <p className="text-gray-700">Loading contract data...</p>
              </div>
            )}

            {mintPriceError && (
              <div className="p-4 bg-red-50 border border-red-200 rounded">
                <p className="text-red-800">
                  Failed to load contract data. Please check the contract address in your
                  configuration.
                </p>
              </div>
            )}

            {!isMintPriceLoading && !mintPriceError && (
              <>
                <div className="space-y-2">
                  <label htmlFor="quantity" className="block text-sm font-medium text-gray-700">
                    Quantity (1-10):
                  </label>
                  <Input
                    id="quantity"
                    type="number"
                    min="1"
                    max="10"
                    value={quantity}
                    onChange={handleQuantityChange}
                    className="max-w-xs"
                  />
                  <p className="text-sm text-gray-500">
                    You will mint {quantity} NFT{quantity > 1 ? 's' : ''}
                  </p>
                </div>

                <Button
                  onClick={handleMint}
                  disabled={
                    !isConnected || !mintPrice || isWritePending || isConfirming || isWrongNetwork
                  }
                  className="w-full max-w-xs"
                >
                  {isWritePending || isConfirming ? 'Minting...' : 'Mint NFTs'}
                </Button>

                <StatusMessage />

                {/* Token Reveal Grid - Show after successful mint */}
                {isConfirmed && mintedTokenIds.length > 0 && (
                  <div className="mt-8 space-y-4">
                    <div className="border-t pt-6">
                      <h2 className="text-2xl font-bold mb-2">🎰 Revealing your NFTs...</h2>
                      <p className="text-gray-600 mb-4">
                        {allRevealed
                          ? 'All tokens revealed! View them in your profile.'
                          : isPolling
                            ? 'Your NFTs are being generated and revealed on-chain. This may take a few minutes.'
                            : 'Waiting for backend processing...'}
                      </p>

                      {pollingError && (
                        <div className="p-4 bg-red-50 border border-red-200 rounded mb-4">
                          <p className="text-red-800 text-sm">{pollingError}</p>
                        </div>
                      )}

                      {/* Grid of TokenRevealCards */}
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
                        {mintedTokenIds.map(tokenId => {
                          const tokenData = tokens.get(tokenId)
                          return (
                            <TokenRevealCard
                              key={tokenId}
                              tokenId={tokenId}
                              status={tokenData?.status || 'detected'}
                              imageUrl={tokenData?.image_url || null}
                            />
                          )
                        })}
                      </div>

                      {/* View Profile Button - Show when all revealed */}
                      {allRevealed && (
                        <div className="flex justify-center">
                          <Button
                            onClick={() => navigate('/profile?tab=author')}
                            size="lg"
                            className="px-8"
                          >
                            View in Profile
                          </Button>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* Author's NFT Collection Section */}
        {isCreatorAddressValid && (
          <div className="mt-8 space-y-4 border border-gray-200 rounded-lg p-6 bg-white">
            <h2 className="text-xl font-semibold">
              {creatorAddress?.slice(0, 6)}...{creatorAddress?.slice(-4)} Collection
            </h2>
            <p className="text-sm text-gray-600">NFTs created by this author</p>

            {/* Loading state */}
            {nftLoading && (
              <div className="p-4 bg-gray-50 border border-gray-200 rounded">
                <p className="text-gray-700">Loading collection...</p>
              </div>
            )}

            {/* Error state */}
            {!nftLoading && nftError && (
              <div className="p-4 bg-red-50 border border-red-200 rounded">
                <p className="text-red-800">Failed to load NFTs</p>
              </div>
            )}

            {/* Empty state */}
            {!nftLoading && !nftError && nftData && nftData.total === 0 && (
              <div className="p-4 bg-gray-50 border border-gray-200 rounded">
                <p className="text-gray-700">No NFTs yet</p>
              </div>
            )}

            {/* NFT Grid */}
            {!nftLoading && !nftError && nftData && nftData.total > 0 && (
              <>
                <NFTGrid
                  tokens={nftData.tokens.map(token => ({
                    tokenId: token.token_id.toString(),
                  }))}
                />

                {/* Pagination */}
                {totalPages > 1 && (
                  <div className="flex items-center justify-between pt-4">
                    <Button
                      onClick={() => setNftPage(p => p - 1)}
                      disabled={nftPage === 1 || nftLoading}
                      variant="outline"
                    >
                      Previous
                    </Button>
                    <p className="text-sm text-gray-600">
                      Page {nftPage} of {totalPages}
                    </p>
                    <Button
                      onClick={() => setNftPage(p => p + 1)}
                      disabled={nftPage === totalPages || nftLoading}
                      variant="outline"
                    >
                      Next
                    </Button>
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
