import { Link } from 'react-router-dom'
import { ConnectButton } from '@rainbow-me/rainbowkit'
import { useAccount } from 'wagmi'

export function Header() {
  const { isConnected } = useAccount()

  return (
    <header className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
      <div className="flex items-center gap-6">
        <Link to="/" className="text-xl font-semibold hover:text-gray-700">
          Glisk NFT
        </Link>
        {isConnected && (
          <Link
            to="/creator-dashboard"
            className="text-sm font-medium text-gray-700 hover:text-gray-900"
          >
            Creator Dashboard
          </Link>
        )}
      </div>
      <ConnectButton />
    </header>
  )
}
