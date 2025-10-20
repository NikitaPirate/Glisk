import { ConnectButton } from '@rainbow-me/rainbowkit'

export function Header() {
  return (
    <header className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
      <div className="text-xl font-semibold">Glisk NFT</div>
      <ConnectButton />
    </header>
  )
}
