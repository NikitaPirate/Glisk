import { Link, NavLink } from 'react-router-dom'
import { ConnectButton } from '@rainbow-me/rainbowkit'
import { useAccount } from 'wagmi'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

export function Header() {
  const { isConnected } = useAccount()

  return (
    <header className="py-6">
      <div className="container mx-auto px-12 max-w-4xl">
        <Card className="px-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-6">
              <Link
                to="/"
                className="text-xl font-semibold text-foreground hover:text-foreground/80 transition-transform hover:scale-105"
              >
                Glisk NFT
              </Link>
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
      </div>
    </header>
  )
}
