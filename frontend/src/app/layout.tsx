import type { Metadata } from 'next'
import { Providers } from './providers'
import '@/index.css'

export const metadata: Metadata = {
  title: 'Glisk NFT - AI-Generated NFT Minting Platform',
  description: 'Create unique AI-generated NFTs on Base blockchain',
  icons: {
    icon: '/favicon.ico',
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
