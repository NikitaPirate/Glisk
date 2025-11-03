'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { ConnectButton } from '@rainbow-me/rainbowkit'
import { useAccount } from 'wagmi'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { HelpDialog } from '@/components/HelpDialog'

export function Header() {
  const { isConnected } = useAccount()
  const pathname = usePathname()

  return (
    <header className="container mx-auto px-4 sm:px-12 max-w-4xl py-6">
      <Card className="sm:px-8 px-4">
        <div className="flex flex-wrap sm:flex-nowrap items-center justify-between sm:justify-start">
          {/* Logo - visible on all screens */}
          <Link href="/" className="order-1 transition-transform hover:scale-105 sm:mr-4">
            <img src="/full_logo.svg" alt="Glisk" className="h-16 sm:h-24" />
          </Link>

          {/* ConnectButton - top row on mobile, pushed right on desktop */}
          <div className="order-2 sm:order-[10] sm:ml-auto">
            <ConnectButton />
          </div>

          {/* Force line break on mobile with vertical spacing */}
          <div className="order-3 sm:hidden basis-full h-6"></div>

          {/* Navigation buttons - spread on mobile, compact on desktop */}
          <div className="order-4 sm:order-2 flex items-center justify-center gap-6 sm:gap-8 w-full sm:w-auto">
            <Link href="/">
              <Button variant={pathname === '/' ? 'tab-active' : 'ghost'} size="lg">
                Home
              </Button>
            </Link>

            {isConnected && (
              <Link href="/profile?tab=author">
                <Button variant={pathname === '/profile' ? 'tab-active' : 'ghost'} size="lg">
                  Profile
                </Button>
              </Link>
            )}

            <HelpDialog />
          </div>
        </div>
      </Card>
    </header>
  )
}
