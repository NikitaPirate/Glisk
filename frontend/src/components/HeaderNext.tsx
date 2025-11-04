'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { ConnectButton, useConnectModal } from '@rainbow-me/rainbowkit'
import { useAccount } from 'wagmi'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { HelpDialog } from '@/components/HelpDialog'
import { useMiniApp } from '@/hooks/useMiniApp'
import { cn } from '@/lib/utils'

export function Header() {
  const { isConnected } = useAccount()
  const { openConnectModal } = useConnectModal()
  const { isMiniApp } = useMiniApp()
  const pathname = usePathname()

  const handleProfileClick = (e: React.MouseEvent) => {
    if (!isConnected && openConnectModal) {
      e.preventDefault()
      openConnectModal()
    }
  }

  return (
    <header className="container mx-auto px-4 sm:px-12 max-w-4xl py-6">
      <Card className="sm:px-8 px-4">
        <div className="flex flex-wrap sm:flex-nowrap items-center justify-between sm:justify-start">
          {/* Logo - expands in Mini App, normal size in browser */}
          <Link
            href="/"
            className={cn(
              'order-1 transition-transform hover:scale-105',
              isMiniApp ? 'flex-1 flex justify-center' : 'sm:mr-4'
            )}
          >
            <img src="/full_logo.svg" alt="Glisk" className="h-16 sm:h-24" />
          </Link>

          {/* ConnectButton - hidden in Mini App context, visible in browser */}
          {!isMiniApp && (
            <div className="order-2 sm:order-[10] sm:ml-auto">
              <ConnectButton />
            </div>
          )}

          {/* Navigation buttons - hidden on mobile, visible on desktop */}
          <div className="order-4 sm:order-2 hidden sm:flex items-center justify-center gap-6 sm:gap-8 w-full sm:w-auto">
            <Link href="/">
              <Button variant={pathname === '/' ? 'tab-active' : 'ghost'} size="lg">
                Home
              </Button>
            </Link>

            <Link href="/profile?tab=author" onClick={handleProfileClick}>
              <Button variant={pathname === '/profile' ? 'tab-active' : 'ghost'} size="lg">
                Profile
              </Button>
            </Link>

            <HelpDialog />
          </div>
        </div>
      </Card>
    </header>
  )
}
