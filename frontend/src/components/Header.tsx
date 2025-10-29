import { Link, NavLink } from 'react-router-dom'
import { ConnectButton } from '@rainbow-me/rainbowkit'
import { useAccount } from 'wagmi'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

export function Header() {
  const { isConnected } = useAccount()

  return (
    <header className="container mx-auto px-4 sm:px-12 max-w-4xl py-6">
      <Card className="sm:px-8 px-2">
        <div className="flex items-center sm:gap-6 gap-4">
          <Link to="/" className="hidden sm:block transition-transform hover:scale-105">
            <img src="/full_logo.svg" alt="Glisk" className="h-24" />
          </Link>
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
          <ConnectButton />
        </div>
      </Card>
    </header>
  )
}
