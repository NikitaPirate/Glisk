// T044, T045, T046: Imports for wagmi hooks, ABI, and contract address
import { useState, useEffect } from 'react'
import { useAccount, useReadContract, useInfiniteReadContracts } from 'wagmi'
import { Button } from '@/components/ui/button'
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
      const startIndex = pageParam as number
      const balanceNum = Number(balance || 0n)

      // T051: Calculate tokens in batch to avoid over-fetching
      const tokensInBatch = Math.min(TOKENS_PER_PAGE, balanceNum - startIndex)

      if (tokensInBatch <= 0) {
        return []
      }

      return Array.from({ length: tokensInBatch }, (_, i) => ({
        address: CONTRACT_ADDRESS,
        abi: ABI,
        functionName: 'tokenOfOwnerByIndex',
        args: [address!, BigInt(startIndex + i)],
      }))
    }) as any,
    query: {
      enabled: !!address && !!balance && Number(balance) > 0,
      initialPageParam: 0,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      getNextPageParam: (_: any, __: any, lastPageParam: any) => {
        const nextIndex = (lastPageParam as number) + TOKENS_PER_PAGE
        return nextIndex < Number(balance || 0n) ? nextIndex : undefined
      },
    },
  })

  // T052: Extract tokenIds from data.pages using flatMap (filter out failed results)
  // Reverse to show oldest first (blockchain returns newest first via tokenOfOwnerByIndex)
  const tokenIds =
    ((data as any)?.pages
      ?.flatMap((page: any) =>
        page.map((result: any) => (result.status === 'success' ? result.result : null))
      )
      .filter((id: any): id is bigint => id !== null)
      .reverse() as bigint[]) || []

  // T057: Calculate total pages for client-side pagination
  const totalPages = Math.ceil(tokenIds.length / 20)

  // T058: Get tokens for current page
  const currentPageTokens = tokenIds.slice((ownedPage - 1) * 20, ownedPage * 20)

  // T062: Reset pagination when wallet changes
  useEffect(() => {
    if (address) {
      setOwnedPage(1)
    }
  }, [address])

  // Combined loading state
  const isLoading = balanceLoading || tokensLoading

  // Combined error state
  const hasError: boolean = !!balanceError || !!tokensError
  const errorMessage: string = String(
    balanceError?.message || tokensError?.message || 'Failed to load NFTs'
  )

  return (
    <div className="space-y-6">
      <div className="space-y-4 rounded-lg p-6 bg-zinc-50 dark:bg-zinc-900">
        <h2 className="text-xl font-semibold">Your Collected NFTs</h2>
        <p className="text-sm text-muted-foreground">
          NFTs that you own from the GLISK collection. These are tokens currently in your wallet.
        </p>

        {/* T053: Loading state */}
        {isLoading && (
          <div className="p-4 bg-muted rounded">
            <p className="text-foreground">Loading your collection...</p>
          </div>
        )}

        {/* T054: Error state */}
        {/* TypeScript strict mode workaround: 'as any' needed for conditional rendering.
            TypeScript cannot infer ReactNode type from hasError boolean + ternary operator.
            Runtime behavior is correct - this is purely a type inference limitation. */}
        {
          (hasError ? (
            <div className="p-4 bg-red-50 dark:bg-red-950 rounded">
              <p className="text-red-800 dark:text-red-200">Failed to load NFTs: {errorMessage}</p>
              <Button onClick={() => window.location.reload()} className="mt-2" variant="outline">
                Retry
              </Button>
            </div>
          ) : null) as any
        }

        {/* T055: Empty state */}
        {!isLoading && !hasError && Number(balance || 0n) === 0 && (
          <div className="p-4 bg-muted rounded">
            <p className="text-foreground">No NFTs owned</p>
          </div>
        )}

        {/* NFT Grid */}
        {!isLoading && !hasError && balance && Number(balance) > 0 && (
          <>
            <NFTGrid
              tokens={currentPageTokens.map((tokenId: bigint) => ({
                tokenId: tokenId.toString(),
              }))}
            />

            {/* T059, T060, T061: Pagination controls */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between pt-4">
                <Button
                  onClick={() => setOwnedPage(p => p - 1)}
                  disabled={ownedPage === 1 || isLoading}
                  variant="outline"
                >
                  Previous
                </Button>
                <p className="text-sm text-muted-foreground">
                  Page {ownedPage} of {totalPages}
                </p>
                <Button
                  onClick={() => setOwnedPage(p => p + 1)}
                  disabled={ownedPage === totalPages || isLoading}
                  variant="outline"
                >
                  Next
                </Button>
              </div>
            )}

            {/* Load more pages from blockchain if needed */}
            {hasNextPage && tokenIds.length < Number(balance) && (
              <div className="pt-4">
                <Button
                  onClick={() => fetchNextPage()}
                  disabled={isLoading}
                  variant="outline"
                  className="w-full"
                >
                  Load More from Blockchain
                </Button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
