import { useState } from 'react'
import type { Hex } from 'viem'
import { useGliskNFTData } from '@/hooks/useGliskNFTData'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'

interface NFTCardProps {
  contractAddress: Hex
  tokenId: string
}

export function NFTCard({ contractAddress, tokenId }: NFTCardProps) {
  const [isOpen, setIsOpen] = useState(false)
  const nftData = useGliskNFTData(contractAddress, tokenId)

  // Error state
  if ('error' in nftData) {
    return (
      <div className="border rounded-lg p-4 bg-muted">
        <p className="text-sm text-muted-foreground">Failed to load NFT #{tokenId}</p>
      </div>
    )
  }

  // Loading state (metadata still fetching)
  const isLoading = !nftData.imageUrl

  return (
    <>
      {/* Compact card in grid */}
      <div
        onClick={() => setIsOpen(true)}
        className="border rounded-lg overflow-hidden hover:shadow-lg transition-shadow bg-card cursor-pointer group"
      >
        {/* Image */}
        <div className="relative aspect-square bg-muted">
          {isLoading ? (
            <div className="absolute inset-0 flex items-center justify-center">
              <p className="text-sm text-muted-foreground">Loading...</p>
            </div>
          ) : (
            <img
              src={nftData.imageUrl}
              alt={nftData.name || `NFT #${tokenId}`}
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200"
            />
          )}
        </div>

        {/* Title */}
        <div className="p-3">
          <h3 className="font-semibold text-sm truncate">
            {nftData.name || `Glisk NFT #${tokenId}`}
          </h3>
        </div>
      </div>

      {/* Expanded dialog */}
      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>{nftData.name || `Glisk NFT #${tokenId}`}</DialogTitle>
            <DialogDescription className="sr-only">NFT Details</DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            {/* Large image */}
            {nftData.imageUrl && (
              <div className="relative aspect-square bg-muted rounded-lg overflow-hidden">
                <img
                  src={nftData.imageUrl}
                  alt={nftData.name || `NFT #${tokenId}`}
                  className="w-full h-full object-contain"
                />
              </div>
            )}

            {/* Metadata */}
            <div className="space-y-3">
              {/* Token ID */}
              <div>
                <p className="text-sm font-medium text-muted-foreground">Token ID</p>
                <p className="text-base">#{tokenId}</p>
              </div>

              {/* Description */}
              {nftData.description && (
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Description</p>
                  <p className="text-base">{nftData.description}</p>
                </div>
              )}

              {/* Author Address */}
              {nftData.authorAddress && (
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Prompt Author</p>
                  <p className="text-base font-mono text-sm break-all">{nftData.authorAddress}</p>
                </div>
              )}

              {/* Author X Handle */}
              {nftData.authorXHandle && (
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Author X Handle</p>
                  <a
                    href={`https://x.com/${nftData.authorXHandle.replace('@', '')}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-base text-primary hover:underline"
                  >
                    {nftData.authorXHandle}
                  </a>
                </div>
              )}
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  )
}
