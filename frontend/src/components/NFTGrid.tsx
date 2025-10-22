// T033: NFTGrid reusable component for displaying NFT cards
// T034: Import OnchainKit NFT components
import { NFTCard } from '@coinbase/onchainkit/nft'
import { NFTMedia, NFTTitle } from '@coinbase/onchainkit/nft/view'
import { useGliskNFTData } from '@/hooks/useGliskNFTData'

const CONTRACT_ADDRESS = import.meta.env.VITE_CONTRACT_ADDRESS as `0x${string}`

interface NFTGridProps {
  tokens: { tokenId: string }[]
}

export function NFTGrid({ tokens }: NFTGridProps) {
  if (tokens.length === 0) {
    return null
  }

  return (
    // T035: Map over tokens array and render NFTCard components
    // Using custom useGliskNFTData hook to fetch metadata from IPFS via Pinata gateway
    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
      {tokens.map(token => (
        <NFTCard
          key={token.tokenId}
          contractAddress={CONTRACT_ADDRESS}
          tokenId={token.tokenId}
          useNFTData={useGliskNFTData}
          className="cursor-default pointer-events-none [&>*]:pointer-events-auto [&_svg[data-testid='ock-defaultNFTSvg']]:hidden"
        >
          <NFTMedia />
          <NFTTitle />
        </NFTCard>
      ))}
    </div>
  )
}
