interface TokenRevealCardProps {
  tokenId: number
  status: string
  imageUrl: string | null
}

/**
 * TokenRevealCard - Displays NFT token during reveal process
 *
 * Shows shimmer skeleton loader while token is being generated/uploaded/revealed.
 * Displays final image when status reaches 'revealed'.
 *
 * Status flow: detected → generating → uploading → ready → revealed
 */
export function TokenRevealCard({ tokenId, status, imageUrl }: TokenRevealCardProps) {
  const isRevealed = status === 'revealed'

  // Status message mapping
  const getStatusMessage = () => {
    switch (status) {
      case 'detected':
        return 'Detected...'
      case 'generating':
        return 'Generating image...'
      case 'uploading':
        return 'Uploading to IPFS...'
      case 'ready':
        return 'Revealing on-chain...'
      case 'revealed':
        return '✓ Revealed'
      case 'failed':
        return '✗ Failed'
      default:
        return 'Processing...'
    }
  }

  return (
    <div className="overflow-hidden bg-zinc-50 dark:bg-zinc-900 rounded-lg">
      {/* Image or Skeleton */}
      <div className="relative aspect-square bg-muted">
        {isRevealed && imageUrl ? (
          // Final revealed state - show image
          <img src={imageUrl} alt={`NFT #${tokenId}`} className="w-full h-full object-cover" />
        ) : (
          // Loading state - shimmer skeleton
          <div className="absolute inset-0 shimmer-skeleton flex items-center justify-center">
            <div className="text-center space-y-2">
              <div className="text-4xl font-bold text-muted-foreground">#{tokenId}</div>
              <div className="text-sm text-muted-foreground">{getStatusMessage()}</div>
            </div>
          </div>
        )}
      </div>

      {/* Footer with status */}
      <div className="p-4 bg-muted">
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium text-foreground">Glisk NFT #{tokenId}</p>
          <span
            className={`text-xs px-2 py-1 rounded ${
              isRevealed
                ? 'bg-green-100 text-green-700'
                : status === 'failed'
                  ? 'bg-red-100 text-red-700'
                  : 'bg-blue-100 text-blue-700'
            }`}
          >
            {getStatusMessage()}
          </span>
        </div>
      </div>

      <style>{`
        @keyframes shimmer {
          0% {
            background-position: -200% 0;
          }
          100% {
            background-position: 200% 0;
          }
        }

        .shimmer-skeleton {
          background: linear-gradient(
            90deg,
            #f0f0f0 0%,
            #e0e0e0 50%,
            #f0f0f0 100%
          );
          background-size: 200% 100%;
          animation: shimmer 2s infinite;
        }
      `}</style>
    </div>
  )
}
