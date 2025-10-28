import { useState, useEffect } from 'react'
import type { Hex } from 'viem'
import { Copy, Check } from 'lucide-react'
import { useGliskNFTData } from '@/hooks/useGliskNFTData'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'

interface NFTCardProps {
  contractAddress: Hex
  tokenId: string
}

export function NFTCard({ contractAddress, tokenId }: NFTCardProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [showErrorAfterDelay, setShowErrorAfterDelay] = useState(false)
  const [isCopied, setIsCopied] = useState(false)
  const nftData = useGliskNFTData(contractAddress, tokenId)

  // Grace period: don't show error immediately (give blockchain/IPFS time to sync)
  useEffect(() => {
    const timer = setTimeout(() => {
      setShowErrorAfterDelay(true)
    }, 3000) // 3 second grace period

    return () => clearTimeout(timer)
  }, [])

  // Error state (only show after grace period)
  if ('error' in nftData && showErrorAfterDelay) {
    return (
      <div className="border rounded-lg p-4 bg-muted">
        <p className="text-sm text-muted-foreground">Failed to load NFT #{tokenId}</p>
      </div>
    )
  }

  // If error but still within grace period, show loading
  if ('error' in nftData) {
    return (
      <div className="overflow-hidden shadow-interactive hover-lift transition-shadow bg-card cursor-pointer">
        <div className="relative aspect-square bg-muted">
          <div className="absolute inset-0 flex items-center justify-center">
            <p className="text-sm text-muted-foreground">Loading...</p>
          </div>
        </div>
      </div>
    )
  }

  // Loading state (metadata still fetching)
  const isLoading = !nftData.imageUrl

  // Copy image to clipboard (convert to PNG via Canvas to avoid WebP issues)
  const handleCopyImage = async () => {
    if (!nftData.imageUrl) return

    try {
      // Create temporary image element
      const img = new Image()
      img.crossOrigin = 'anonymous' // Enable CORS
      img.src = nftData.imageUrl

      // Wait for image to load
      await new Promise((resolve, reject) => {
        img.onload = resolve
        img.onerror = reject
      })

      // Draw image on canvas
      const canvas = document.createElement('canvas')
      canvas.width = img.naturalWidth
      canvas.height = img.naturalHeight
      const ctx = canvas.getContext('2d')
      ctx?.drawImage(img, 0, 0)

      // Convert canvas to PNG blob
      const blob = await new Promise<Blob>(resolve => {
        canvas.toBlob(blob => resolve(blob!), 'image/png')
      })

      // Copy PNG to clipboard
      await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })])

      setIsCopied(true)

      setTimeout(() => {
        setIsCopied(false)
      }, 2000)
    } catch (error) {
      console.error('Failed to copy image:', error)
    }
  }

  return (
    <>
      {/* Compact card in grid */}
      <div
        onClick={() => setIsOpen(true)}
        className="overflow-hidden shadow-interactive hover-lift transition-shadow bg-card cursor-pointer group"
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
      </div>

      {/* Expanded dialog */}
      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent className="sm:max-w-4xl">
          <DialogHeader>
            <DialogTitle className="text-3xl">
              {nftData.name || `Glisk NFT #${tokenId}`}
            </DialogTitle>
            <DialogDescription className="sr-only">NFT Details</DialogDescription>
          </DialogHeader>

          <div className="space-y-16">
            {/* Large image */}
            {nftData.imageUrl && (
              <div className="space-y-4">
                <div className="relative aspect-square bg-muted overflow-hidden">
                  <img
                    src={nftData.imageUrl}
                    alt={nftData.name || `NFT #${tokenId}`}
                    className="w-full h-full object-contain"
                  />
                </div>

                {/* Copy Image Button */}
                <Button
                  onClick={handleCopyImage}
                  disabled={isCopied}
                  variant="secondary"
                  size="lg"
                  className="w-full"
                >
                  {isCopied ? (
                    <>
                      <Check className="w-5 h-5" />
                      Copied!
                    </>
                  ) : (
                    <>
                      <Copy className="w-5 h-5" />
                      Copy Image to Clipboard
                    </>
                  )}
                </Button>
              </div>
            )}

            {/* Metadata */}
            <div className="space-y-8">
              {/* Token ID */}
              <div>
                <p className="text-sm font-medium text-muted-foreground mb-2">Token ID</p>
                <p className="text-lg font-mono">#{tokenId}</p>
              </div>

              {/* Description */}
              {nftData.description && (
                <div>
                  <p className="text-sm font-medium text-muted-foreground mb-2">Description</p>
                  <p className="text-base">{nftData.description}</p>
                </div>
              )}

              {/* Author Address */}
              {nftData.authorAddress && (
                <div>
                  <p className="text-sm font-medium text-muted-foreground mb-2">Prompt Author</p>
                  <p className="text-base font-mono break-all">{nftData.authorAddress}</p>
                </div>
              )}

              {/* Author X Handle */}
              {nftData.authorXHandle && (
                <div>
                  <p className="text-sm font-medium text-muted-foreground mb-2">Author X Handle</p>
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
