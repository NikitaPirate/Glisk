import { getDefaultConfig } from '@rainbow-me/rainbowkit'
import { baseSepolia } from 'wagmi/chains'

// Get WalletConnect Project ID from https://cloud.walletconnect.com
// For MVP, using a demo project ID. Replace with your own in production.
const projectId = import.meta.env.VITE_WALLETCONNECT_PROJECT_ID || 'YOUR_PROJECT_ID'

export const config = getDefaultConfig({
  appName: 'Glisk NFT',
  projectId,
  chains: [baseSepolia],
  ssr: false, // Not using server-side rendering
})
