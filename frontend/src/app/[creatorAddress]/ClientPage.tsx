'use client'

import { useState, useCallback } from 'react'
import { useAccount, useReadContract, useChainId } from 'wagmi'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { isAddress, parseEventLogs } from 'viem'
import { IdentityCard } from '@coinbase/onchainkit/identity'
import { Transaction, TransactionButton } from '@coinbase/onchainkit/transaction'
import type { LifecycleStatus } from '@coinbase/onchainkit/transaction'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { CONTRACT_ADDRESS, GLISK_NFT_ABI } from '@/lib/contract'
import { network } from '@/lib/wagmi'
import { TokenRevealCard } from '@/components/TokenRevealCard'
import { NFTCard } from '@/components/NFTCard'
import { useTokenPolling } from '@/hooks/useTokenPolling'
import { NFTGrid } from '@/components/NFTGrid'
import { Header } from '@/components/HeaderNext'

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

interface AuthorDTO {
  wallet_address: string
  twitter_handle: string | null
}

async function fetchAuthorTokens(walletAddress: string, page: number): Promise<TokensResponse> {
  const offset = (page - 1) * 20
  const response = await fetch(`/api/authors/${walletAddress}/tokens?offset=${offset}&limit=20`)

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${await response.text()}`)
  }

  return response.json()
}

async function fetchAuthorData(walletAddress: string): Promise<AuthorDTO> {
  const response = await fetch(`/api/authors/${walletAddress}`)

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${await response.text()}`)
  }

  return response.json()
}

export function CreatorMintPageClient({ creatorAddress }: { creatorAddress: string }) {
  const { isConnected, address: connectedWallet } = useAccount()
  const chainId = useChainId()
  const queryClient = useQueryClient()
  const [quantity, setQuantity] = useState(1)
  const [mintedTokenIds, setMintedTokenIds] = useState<number[]>([]) // Token IDs from BatchMinted event
  const [nftPage, setNftPage] = useState(1)
  const [transactionStatus, setTransactionStatus] = useState<TransactionStatus>('idle')
  const [transactionError, setTransactionError] = useState<string | null>(null)

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

  // Handle OnchainKit Transaction lifecycle
  const handleTransactionStatus = useCallback((status: LifecycleStatus) => {
    console.log('[Transaction] Lifecycle status:', status)
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const statusData = status.statusData as any

    // Map OnchainKit status to our internal status
    switch (status.statusName) {
      case 'init':
      case 'transactionIdle':
        setTransactionStatus('idle')
        setTransactionError(null)
        break
      case 'buildingTransaction':
      case 'transactionPending':
        setTransactionStatus('pending')
        break
      case 'success': {
        setTransactionStatus('success')
        setTransactionError(null)

        // Parse BatchMinted event from receipts
        if (statusData?.transactionReceipts && statusData.transactionReceipts.length > 0) {
          const receipt = statusData.transactionReceipts[0]
          try {
            const logs = parseEventLogs({
              abi: GLISK_NFT_ABI,
              eventName: 'BatchMinted',
              logs: receipt.logs,
            })

            if (logs.length > 0) {
              const batchMintedEvent = logs[0] as {
                args?: { startTokenId?: bigint; quantity?: bigint }
              }
              const args = batchMintedEvent.args

              if (args && args.startTokenId !== undefined && args.quantity !== undefined) {
                const startTokenId = Number(args.startTokenId)
                const mintQuantity = Number(args.quantity)
                const tokenIds = Array.from({ length: mintQuantity }, (_, i) => startTokenId + i)
                setMintedTokenIds(tokenIds)
                console.log('[Transaction] BatchMinted event parsed:', { tokenIds })
              }
            }
          } catch (error) {
            console.error('[Transaction] Failed to parse BatchMinted event:', error)
          }
        }
        break
      }
      case 'error': {
        // Check if user rejected/cancelled
        const errorMessage =
          typeof statusData === 'string'
            ? statusData
            : statusData?.message || statusData?.error?.message || ''
        if (
          errorMessage.includes('User rejected') ||
          errorMessage.includes('User denied') ||
          errorMessage.includes('rejected') ||
          errorMessage.includes('denied')
        ) {
          setTransactionStatus('cancelled')
          setTransactionError('Transaction cancelled')
        } else {
          setTransactionStatus('failed')
          setTransactionError(errorMessage || 'Transaction failed')
        }
        break
      }
    }
  }, [])

  // Poll for token status updates
  const { tokens, allRevealed } = useTokenPolling(
    mintedTokenIds,
    connectedWallet,
    transactionStatus === 'success' && mintedTokenIds.length > 0 // Enable polling after mint success
  )

  // Fetch author data
  const { data: authorData, isLoading: authorLoading } = useQuery({
    queryKey: ['author-data', creatorAddress],
    queryFn: () => fetchAuthorData(creatorAddress!),
    enabled: !!creatorAddress && isCreatorAddressValid,
    staleTime: 60000,
  })

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

  // Prepare contract calls for OnchainKit Transaction
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const mintCalls: any[] =
    !creatorAddress || !mintPrice
      ? []
      : [
          {
            address: CONTRACT_ADDRESS,
            abi: GLISK_NFT_ABI,
            functionName: 'mint',
            args: [creatorAddress as `0x${string}`, BigInt(quantity)],
            value: mintPrice * BigInt(quantity),
          },
        ]

  const handleMintMore = () => {
    // Reset mint state (triggers Card Transformation back to mint form)
    setMintedTokenIds([])
    setQuantity(1)
    setTransactionStatus('idle')
    setTransactionError(null)

    // Invalidate gallery query to fetch newly minted NFTs
    queryClient.invalidateQueries({ queryKey: ['creator-nfts', creatorAddress] })
  }

  // Status message component
  const StatusMessage = () => {
    switch (transactionStatus) {
      case 'waitingApproval':
        return (
          <p className="text-sm text-blue-600 dark:text-blue-400">
            Please approve the transaction in your wallet
          </p>
        )
      case 'pending':
        return <p className="text-sm text-blue-600 dark:text-blue-400">Minting...</p>
      case 'success':
        return (
          <div className="space-y-1">
            <p className="text-sm text-green-600 dark:text-green-400">Success! NFTs minted.</p>
            {mintedTokenIds.length > 0 && (
              <p className="text-sm text-green-600 dark:text-green-400">
                Token IDs: {mintedTokenIds.join(', ')}
              </p>
            )}
          </div>
        )
      case 'cancelled':
        return <p className="text-sm text-yellow-600 dark:text-yellow-400">Transaction cancelled</p>
      case 'failed':
        return (
          <p className="text-sm text-red-600 dark:text-red-400">
            Error: {transactionError || 'Transaction failed'}
          </p>
        )
      default:
        return null
    }
  }

  if (!creatorAddress) {
    return (
      <>
        <Header />
        <div className="container mx-auto px-4 py-8">
          <p className="text-sm text-red-600 dark:text-red-400">
            Error: No creator address provided
          </p>
        </div>
      </>
    )
  }

  if (!isCreatorAddressValid) {
    return (
      <>
        <Header />
        <div className="container mx-auto px-4 py-8">
          <p className="text-sm text-red-600 dark:text-red-400">Invalid creator address</p>
        </div>
      </>
    )
  }

  // Network validation
  const isWrongNetwork = chainId !== network.chainId

  // Coinbase Verified attestation schema ID
  const COINBASE_VERIFIED_SCHEMA_ID = network.attestationSchema

  return (
    <>
      <Header />
      <div className="page-container">
        <div className="space-y-16">
          {/* Author Identity Section */}
          {isCreatorAddressValid && (
            <Card className="px-8 gap-6 mb-16">
              {authorLoading ? (
                <p className="text-sm text-muted-foreground">Loading...</p>
              ) : (
                <>
                  <IdentityCard
                    address={creatorAddress as `0x${string}`}
                    chain={network.chain}
                    schemaId={COINBASE_VERIFIED_SCHEMA_ID}
                    className="!p-0 !w-fit"
                  />

                  {/* X Account */}
                  {authorData?.twitter_handle && (
                    <p className="text-sm text-green-600 dark:text-green-400">
                      ✓ @{authorData.twitter_handle}
                    </p>
                  )}
                </>
              )}
            </Card>
          )}

          {!isConnected && (
            <p className="text-sm text-blue-600 dark:text-blue-400">Connect wallet</p>
          )}

          {isConnected && isWrongNetwork && (
            <p className="text-sm text-yellow-600 dark:text-yellow-400">Switch to Base Sepolia</p>
          )}

          {isConnected && !isWrongNetwork && (
            <Card className="px-16 py-24 max-w-4xl mx-auto">
              {isMintPriceLoading && <p className="text-sm text-muted-foreground">Loading...</p>}

              {mintPriceError && (
                <p className="text-sm text-red-600 dark:text-red-400">Contract error</p>
              )}

              {!isMintPriceLoading && !mintPriceError && (
                <>
                  {/* Card Transformation: Show EITHER mint form OR revealing workflow */}
                  {!(transactionStatus === 'success' && mintedTokenIds.length > 0) ? (
                    // MINT FORM STATE
                    <div className="space-y-16">
                      {/* Monumental Quantity Input */}
                      <div className="space-y-4">
                        <input
                          id="quantity"
                          type="number"
                          min="1"
                          max="10"
                          value={quantity}
                          onChange={handleQuantityChange}
                          placeholder="1-10"
                          className="w-full h-24 text-5xl text-center font-bold rounded-none bg-accent shadow-interactive focus-lift focus-darken focus:outline-none transition-all p-6"
                        />
                        {quantity > 10 && (
                          <p className="text-sm text-red-600 dark:text-red-400 text-center">
                            Max 10
                          </p>
                        )}
                      </div>

                      {/* Monumental MINT Button with Gas Sponsorship */}
                      <Transaction
                        calls={mintCalls}
                        chainId={network.chainId}
                        onStatus={handleTransactionStatus}
                        isSponsored={true}
                      >
                        <TransactionButton
                          disabled={
                            !isConnected ||
                            !mintPrice ||
                            transactionStatus === 'pending' ||
                            isWrongNetwork ||
                            quantity > 10
                          }
                          className="w-full h-24 text-6xl font-black inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-none transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground shadow-brutal hover:shadow-brutal-lg active:shadow-brutal-sm font-black tracking-wide border-4 border-foreground"
                          text={transactionStatus === 'pending' ? 'MINTING...' : 'MINT'}
                        />
                      </Transaction>

                      <StatusMessage />
                    </div>
                  ) : (
                    // REVEALING WORKFLOW STATE
                    <div className="space-y-16">
                      {/* Grid of reveal cards and revealed NFTs */}
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {mintedTokenIds.map(tokenId => {
                          const tokenData = tokens.get(tokenId)
                          const isRevealed = tokenData?.status === 'revealed'

                          return isRevealed ? (
                            <NFTCard
                              key={tokenId}
                              contractAddress={CONTRACT_ADDRESS}
                              tokenId={tokenId.toString()}
                            />
                          ) : (
                            <TokenRevealCard
                              key={tokenId}
                              tokenId={tokenId}
                              status={tokenData?.status || 'detected'}
                            />
                          )
                        })}
                      </div>

                      {/* Monumental MINT MORE Button - Show when all revealed */}
                      {allRevealed && (
                        <Button
                          onClick={handleMintMore}
                          variant="primary-action"
                          className="w-full h-24 text-6xl font-black"
                        >
                          MINT MORE
                        </Button>
                      )}
                    </div>
                  )}
                </>
              )}
            </Card>
          )}

          {/* Author's NFT Gallery */}
          {isCreatorAddressValid && (
            <Card className="px-8 gap-6">
              {/* Loading state */}
              {nftLoading && <p className="text-sm text-muted-foreground">Loading...</p>}

              {/* Error state */}
              {!nftLoading && nftError && (
                <p className="text-sm text-red-600 dark:text-red-400">Error</p>
              )}

              {/* Empty state */}
              {!nftLoading && !nftError && nftData && nftData.total === 0 && (
                <p className="text-sm text-muted-foreground">No NFTs</p>
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
                        variant="ghost"
                      >
                        Previous
                      </Button>
                      <p className="text-sm text-muted-foreground">
                        Page {nftPage} of {totalPages}
                      </p>
                      <Button
                        onClick={() => setNftPage(p => p + 1)}
                        disabled={nftPage === totalPages || nftLoading}
                        variant="ghost"
                      >
                        Next
                      </Button>
                    </div>
                  )}
                </>
              )}
            </Card>
          )}
        </div>
      </div>
    </>
  )
}
