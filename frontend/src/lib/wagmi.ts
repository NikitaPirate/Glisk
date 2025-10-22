import { http } from 'wagmi'
import { baseSepolia } from 'wagmi/chains'
import { getDefaultConfig } from '@rainbow-me/rainbowkit'

// Get WalletConnect Project ID from https://cloud.walletconnect.com
const projectId = import.meta.env.VITE_WALLETCONNECT_PROJECT_ID || 'YOUR_PROJECT_ID'

// Get CDP API Key from Coinbase Developer Platform
const cdpApiKey = import.meta.env.VITE_ONCHAINKIT_API_KEY

// Configure CDP RPC transport for reliable blockchain reads (50 req/sec vs public 10 req/sec)
const cdpRpcUrl = `https://api.developer.coinbase.com/rpc/v1/base-sepolia/${cdpApiKey}`

console.log('[Wagmi Config] Using CDP RPC:', cdpRpcUrl.replace(cdpApiKey || '', '***'))

export const config = getDefaultConfig({
  appName: 'Glisk NFT',
  projectId,
  chains: [baseSepolia],
  transports: {
    [baseSepolia.id]: http(cdpRpcUrl),
  },
  ssr: false,
})
