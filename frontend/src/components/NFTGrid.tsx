// NFTGrid reusable component for displaying NFT cards
import { NFTCard } from '@/components/NFTCard'

const CONTRACT_ADDRESS = import.meta.env.VITE_CONTRACT_ADDRESS as `0x${string}`

interface NFTGridProps {
  tokens: { tokenId: string }[]
}

export function NFTGrid({ tokens }: NFTGridProps) {
  if (tokens.length === 0) {
    return null
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-0">
      {tokens.map(token => (
        <NFTCard key={token.tokenId} contractAddress={CONTRACT_ADDRESS} tokenId={token.tokenId} />
      ))}
    </div>
  )
}
