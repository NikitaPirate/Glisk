'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useAccount } from 'wagmi'
import { useConnectModal } from '@rainbow-me/rainbowkit'
import { Button } from '@/components/ui/button'

export default function BottomNav() {
  const pathname = usePathname()
  const { isConnected } = useAccount()
  const { openConnectModal } = useConnectModal()

  const isHomePage = pathname === '/'
  const isProfilePage = pathname?.startsWith('/profile')
  // Info doesn't have a dedicated page (it's a dialog), so no active state

  const handleProfileClick = (e: React.MouseEvent) => {
    if (!isConnected && openConnectModal) {
      e.preventDefault()
      openConnectModal()
    }
  }

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 sm:hidden bg-card border-t border-border shadow-interactive">
      <div className="container mx-auto px-16">
        <div className="flex items-center justify-around h-16 pb-safe">
          {/* Home Button */}
          <Link href="/" className="flex-1">
            <Button
              variant={isHomePage ? 'tab-active' : 'ghost'}
              // className="w-full h-12 text-base font-medium"
            >
              Home
            </Button>
          </Link>

          {/* Profile Button */}
          <Link href="/profile?tab=author" onClick={handleProfileClick} className="flex-1">
            <Button
              variant={isProfilePage ? 'tab-active' : 'ghost'}
              // className="w-full h-12 text-base font-medium"
            >
              Profile
            </Button>
          </Link>

          {/* Info Button (opens dialog in header) */}
          <Button
            variant="ghost"
            // className="flex-1 h-12 text-base font-medium"
            onClick={() => {
              // Trigger the help dialog from HeaderNext
              // We'll dispatch a custom event that HeaderNext will listen to
              window.dispatchEvent(new CustomEvent('openHelpDialog'))
            }}
          >
            Info
          </Button>
        </div>
      </div>
    </nav>
  )
}
