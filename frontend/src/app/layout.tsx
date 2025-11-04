import type { Metadata } from 'next'
import { Providers } from './providers'
import BottomNav from '@/components/BottomNav'
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
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="pb-16 sm:pb-0">
        <Providers>
          {children}
          <BottomNav />
        </Providers>
      </body>
    </html>
  )
}
