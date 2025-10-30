import { Link, NavLink } from 'react-router-dom'
import { ConnectButton } from '@rainbow-me/rainbowkit'
import { useAccount } from 'wagmi'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { HelpDialog } from '@/components/HelpDialog'

export function Header() {
  const { isConnected } = useAccount()

  return (
    <header className="container mx-auto px-4 sm:px-12 max-w-4xl py-6">
      <Card className="sm:px-8 px-4">
        <div className="flex flex-wrap sm:flex-nowrap items-center justify-between sm:justify-start">
          {/* Logo - visible on all screens */}
          <Link to="/" className="order-1 transition-transform hover:scale-105 sm:mr-4">
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
            <NavLink to="/">
              {({ isActive }) => (
                <Button variant={isActive ? 'tab-active' : 'ghost'} size="lg">
                  Home
                </Button>
              )}
            </NavLink>

            {isConnected && (
              <NavLink to="/profile?tab=author">
                {({ isActive }) => (
                  <Button variant={isActive ? 'tab-active' : 'ghost'} size="lg">
                    Profile
                  </Button>
                )}
              </NavLink>
            )}

            <HelpDialog />
          </div>
        </div>
      </Card>
    </header>
  )
}
