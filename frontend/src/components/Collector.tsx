// T044, T045, T046: Imports for wagmi hooks, ABI, and contract address
import { useState, useEffect } from 'react'
import { useAccount, useReadContract, useInfiniteReadContracts } from 'wagmi'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { NFTGrid } from '@/components/NFTGrid'
import { CONTRACT_ADDRESS, GLISK_NFT_ABI } from '@/lib/contract'

const TOKENS_PER_PAGE = 20
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const ABI = GLISK_NFT_ABI as any

export function Collector() {
  // T047: Get current wallet address
  const { address } = useAccount()

  // T056: Pagination state for owned NFTs (client-side)
  const [ownedPage, setOwnedPage] = useState(1)

  // T048: Get balance of NFTs owned by address
  const {
    data: balance,
    isLoading: balanceLoading,
    error: balanceError,
  } = useReadContract({
    address: CONTRACT_ADDRESS,
    abi: ABI,
    functionName: 'balanceOf',
    args: address ? [address] : undefined,
    query: {
      enabled: !!address,
    },
  })

  // T049, T050, T051: Implement useInfiniteReadContracts with pagination
  // Fetch backwards from end to show newest NFTs first
  const {
    data,
    error: tokensError,
    isLoading: tokensLoading,
    fetchNextPage,
    hasNextPage,
  } = useInfiniteReadContracts({
    cacheKey: `owned-nfts-${address}`,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    contracts: ((pageParam: any) => {
      const offsetFromEnd = pageParam as number
      const balanceNum = Number(balance || 0n)

      // Calculate actual start index (counting backwards from end)
      const endIndex = balanceNum - offsetFromEnd
      const startIndex = Math.max(0, endIndex - TOKENS_PER_PAGE)

      // T051: Calculate tokens in batch to avoid over-fetching
      const tokensInBatch = endIndex - startIndex

      if (tokensInBatch <= 0) {
        return []
      }

      // Fetch backwards: start from highest index in range
      return Array.from({ length: tokensInBatch }, (_, i) => ({
        address: CONTRACT_ADDRESS,
        abi: ABI,
        functionName: 'tokenOfOwnerByIndex',
        args: [address!, BigInt(endIndex - 1 - i)],
      }))
    }) as any,
    query: {
      enabled: !!address && !!balance && Number(balance) > 0,
      initialPageParam: 0,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      getNextPageParam: (_: any, __: any, lastPageParam: any) => {
        const nextOffsetFromEnd = (lastPageParam as number) + TOKENS_PER_PAGE
        return nextOffsetFromEnd < Number(balance || 0n) ? nextOffsetFromEnd : undefined
      },
    },
  })

  // T052: Extract tokenIds from data.pages using flatMap (filter out failed results)
  // Tokens are already in newest-first order (we fetch backwards from end)
  const tokenIds =
    ((data as any)?.pages
      ?.flatMap((page: any) =>
        page.map((result: any) => (result.status === 'success' ? result.result : null))
      )
      .filter((id: any): id is bigint => id !== null) as bigint[]) || []

  // T057: Calculate total pages for client-side pagination
  const totalPages = Math.ceil(tokenIds.length / 20)

  // T058: Get tokens for current page
  const currentPageTokens = tokenIds.slice((ownedPage - 1) * 20, ownedPage * 20)

  // Combined loading state
  const isLoading = balanceLoading || tokensLoading

  // T062: Reset pagination when wallet changes
  useEffect(() => {
    if (address) {
      setOwnedPage(1)
    }
  }, [address])

  // Auto-load more NFTs when user reaches last page of loaded tokens
  useEffect(() => {
    if (!hasNextPage || isLoading) return

    // If user is on last page of loaded tokens, fetch more
    if (ownedPage === totalPages && hasNextPage) {
      fetchNextPage()
    }
  }, [ownedPage, totalPages, hasNextPage, fetchNextPage, isLoading])

  // Combined error state
  const hasError: boolean = !!balanceError || !!tokensError
  const errorMessage: string = String(
    balanceError?.message || tokensError?.message || 'Failed to load NFTs'
  )

  return (
    <div className="space-y-6">
      <Card className="px-8 gap-6">
        <h2 className="text-2xl font-bold">Your Collected NFTs</h2>

        {/* T053: Loading state */}
        {isLoading && <p className="text-sm text-muted-foreground">Loading...</p>}

        {/* T054: Error state */}
        {
          (hasError ? (
            <div className="space-y-2">
              <p className="text-sm text-red-600 dark:text-red-400">
                Failed to load NFTs: {errorMessage}
              </p>
              <Button onClick={() => window.location.reload()} size="sm" variant="ghost">
                Retry
              </Button>
            </div>
          ) : null) as any
        }

        {/* T055: Empty state */}
        {!isLoading && !hasError && Number(balance || 0n) === 0 && (
          <p className="text-sm text-muted-foreground">No NFTs</p>
        )}

        {/* NFT Grid */}
        {!isLoading && !hasError && balance && Number(balance) > 0 && (
          <>
            <NFTGrid
              tokens={currentPageTokens.map((tokenId: bigint) => ({
                tokenId: tokenId.toString(),
              }))}
            />

            {/* T059, T060, T061: Pagination controls with auto-loading */}
            {(totalPages > 1 || hasNextPage) && (
              <div className="flex items-center justify-between pt-4">
                <Button
                  onClick={() => setOwnedPage(p => p - 1)}
                  disabled={ownedPage === 1 || isLoading}
                  variant="ghost"
                >
                  Previous
                </Button>
                <p className="text-sm text-muted-foreground">
                  Page {ownedPage} · {currentPageTokens.length} NFTs
                  {tokensLoading && hasNextPage && ' (loading more...)'}
                </p>
                <Button
                  onClick={() => setOwnedPage(p => p + 1)}
                  disabled={ownedPage * 20 >= Number(balance || 0n) || isLoading}
                  variant="ghost"
                >
                  Next
                </Button>
              </div>
            )}
          </>
        )}
      </Card>
    </div>
  )
}
