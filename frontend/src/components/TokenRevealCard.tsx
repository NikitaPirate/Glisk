interface TokenRevealCardProps {
  tokenId: number
  status: string
}

/**
 * TokenRevealCard - Displays NFT token during reveal process
 *
 * Shows shimmer skeleton loader while token is being generated/uploaded/revealed.
 * Once revealed, replaced by NFTCard component.
 *
 * Status flow: detected → generating → uploading → ready
 */
export function TokenRevealCard({ tokenId, status }: TokenRevealCardProps) {
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
      case 'failed':
        return '✗ Failed'
      default:
        return 'Processing...'
    }
  }

  return (
    <div className="overflow-hidden bg-card shadow-interactive">
      {/* Shimmer skeleton loader */}
      <div className="relative aspect-square bg-muted">
        <div className="absolute inset-0 shimmer-skeleton flex items-center justify-center">
          <div className="text-center space-y-2">
            <div className="text-4xl font-bold text-muted-foreground">#{tokenId}</div>
            <div className="text-sm text-muted-foreground">{getStatusMessage()}</div>
          </div>
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
            oklch(0.98 0.02 201) 0%,
            oklch(0.85 0.1 201) 50%,
            oklch(0.98 0.02 201) 100%
          );
          background-size: 200% 100%;
          animation: shimmer 2s infinite;
        }

        @media (prefers-color-scheme: dark) {
          .shimmer-skeleton {
            background: linear-gradient(
              90deg,
              oklch(0.18 0.04 215) 0%,
              oklch(0.48 0.1 209) 50%,
              oklch(0.18 0.04 215) 100%
            );
          }
        }
      `}</style>
    </div>
  )
}
