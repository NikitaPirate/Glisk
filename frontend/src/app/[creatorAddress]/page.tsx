import type { Metadata } from 'next'
import { CreatorMintPageClient } from './ClientPage'

// Force dynamic rendering to avoid build-time env variable requirements
export const dynamic = 'force-dynamic'

export async function generateMetadata({
  params,
}: {
  params: Promise<{ creatorAddress: string }>
}): Promise<Metadata> {
  const { creatorAddress } = await params

  // Format address for display (0x1234...5678)
  const shortAddress = `${creatorAddress.slice(0, 6)}...${creatorAddress.slice(-4)}`

  // Create mini app embed configuration
  const miniappEmbed = {
    version: '1',
    imageUrl: 'https://glisk.xyz/app-icon.png',
    button: {
      title: 'MINT',
      action: {
        type: 'launch_miniapp',
        name: 'Glisk',
        url: `https://glisk.xyz/${creatorAddress}`,
        splashImageUrl: 'https://glisk.xyz/app-icon.png',
        splashBackgroundColor: '#000000',
      },
    },
  }

  // Create backward-compatible frame embed
  const frameEmbed = {
    ...miniappEmbed,
    button: {
      ...miniappEmbed.button,
      action: {
        ...miniappEmbed.button.action,
        type: 'launch_frame',
      },
    },
  }

  return {
    title: `Mint from ${shortAddress} - Glisk`,
    description: `Discover and mint AI-generated NFTs from creator ${shortAddress} on Base blockchain`,
    openGraph: {
      title: `${shortAddress}'s AI NFTs`,
      description: 'Mint unique AI-generated NFTs on Base',
      images: ['https://glisk.xyz/app-icon.png'],
    },
    other: {
      'fc:miniapp': JSON.stringify(miniappEmbed),
      'fc:frame': JSON.stringify(frameEmbed),
    },
  }
}

export default async function CreatorMintPage({
  params,
}: {
  params: Promise<{ creatorAddress: string }>
}) {
  const { creatorAddress } = await params
  return <CreatorMintPageClient creatorAddress={creatorAddress} />
}
