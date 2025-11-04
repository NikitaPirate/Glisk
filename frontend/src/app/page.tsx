import type { Metadata } from 'next'
import HomePageClient from './HomePageClient'

export const metadata: Metadata = {
  title: 'Glisk NFT - AI-Generated NFT Minting Platform',
  description: 'Discover and mint unique AI-generated NFTs on Base blockchain',
  openGraph: {
    title: 'Glisk NFT',
    description: 'Create unique AI-generated NFTs on Base blockchain',
    images: ['https://glisk.xyz/app-icon.png'],
  },
  other: {
    'fc:miniapp': JSON.stringify({
      version: '1',
      imageUrl: 'https://glisk.xyz/app-icon.png',
      button: {
        title: 'Open Glisk',
        action: {
          type: 'launch_miniapp',
          name: 'Glisk',
          url: 'https://glisk.xyz',
          splashImageUrl: 'https://glisk.xyz/app-icon.png',
          splashBackgroundColor: '#000000',
        },
      },
    }),
  },
}

export default function HomePage() {
  return <HomePageClient />
}
