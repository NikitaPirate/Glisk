import { Link, NavLink } from 'react-router-dom'
import { ConnectButton } from '@rainbow-me/rainbowkit'
import { useAccount } from 'wagmi'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

export function Header() {
  const { isConnected } = useAccount()

  return (
    <header className="container mx-auto px-4 sm:px-12 max-w-4xl py-6">
      <Card className="px-8">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-6">
            <Link to="/" className="transition-transform hover:scale-105">
              <img src="/full_logo.svg" alt="Glisk" className="h-24" />
            </Link>
            <NavLink to="/">
              {({ isActive }) => (
                <Button variant={isActive ? 'tab-active' : 'ghost'} size="sm">
                  Home
                </Button>
              )}
            </NavLink>
            {isConnected && (
              <NavLink to="/profile?tab=author">
                {({ isActive }) => (
                  <Button variant={isActive ? 'tab-active' : 'ghost'} size="sm">
                    Profile
                  </Button>
                )}
              </NavLink>
            )}
          </div>
          <ConnectButton />
        </div>
      </Card>
    </header>
  )
}
