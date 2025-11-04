import type { Metadata } from 'next'
import { Providers } from './providers'
import '@/index.css'

export const metadata: Metadata = {
  title: 'Glisk NFT - AI-Generated NFT Minting Platform',
  description: 'Create unique AI-generated NFTs on Base blockchain',
  icons: {
    icon: '/favicon.svg',
    apple: '/apple-touch-icon.png',
  },
  openGraph: {
    title: 'Glisk NFT',
    description: 'Create unique AI-generated NFTs on Base blockchain',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Glisk NFT',
    description: 'Create unique AI-generated NFTs on Base blockchain',
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

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
