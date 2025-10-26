import { Link } from 'react-router-dom'
import { ConnectButton } from '@rainbow-me/rainbowkit'
import { useAccount } from 'wagmi'

export function Header() {
  const { isConnected } = useAccount()

  return (
    <header className="flex items-center justify-between px-6 py-4 border-b border-border">
      <div className="flex items-center gap-6">
        <Link to="/" className="text-xl font-semibold hover:text-foreground/80">
          Glisk NFT
        </Link>
        {isConnected && (
          <Link
            to="/profile?tab=author"
            className="text-sm font-medium text-foreground hover:text-foreground/90"
          >
            Profile
          </Link>
        )}
      </div>
      <ConnectButton />
    </header>
  )
}
