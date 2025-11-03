import { http } from 'wagmi'
import { base, baseSepolia } from 'wagmi/chains'
import { getDefaultConfig } from '@rainbow-me/rainbowkit'

// Network configuration mapping
const NETWORK_CONFIG = {
  BASE_SEPOLIA: {
    chain: baseSepolia,
    chainId: 84532,
    cdpRpc: 'base-sepolia',
    attestationSchema: '0xf8b05c79f090979bf4a80270aba232dff11a10d9ca55c4f88de95317970f0de9',
  },
  BASE_MAINNET: {
    chain: base,
    chainId: 8453,
    cdpRpc: 'base',
    attestationSchema: '0xf8b05c79f090979bf4a80270aba232dff11a10d9ca55c4f88de95317970f0de9',
  },
} as const

// Get network from environment (defaults to BASE_MAINNET for production)
const networkKey = (process.env.NEXT_PUBLIC_NETWORK ||
  'BASE_MAINNET') as keyof typeof NETWORK_CONFIG
export const network = NETWORK_CONFIG[networkKey]

// Get WalletConnect Project ID from https://cloud.walletconnect.com
const projectId = process.env.NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID || 'YOUR_PROJECT_ID'

// Get CDP API Key from Coinbase Developer Platform
const cdpApiKey = process.env.NEXT_PUBLIC_ONCHAINKIT_API_KEY

// Configure CDP RPC transport for reliable blockchain reads (50 req/sec vs public 10 req/sec)
const cdpRpcUrl = `https://api.developer.coinbase.com/rpc/v1/${network.cdpRpc}/${cdpApiKey}`

console.log('[Wagmi Config] Network:', networkKey)
console.log('[Wagmi Config] Chain ID:', network.chainId)
console.log('[Wagmi Config] Using CDP RPC:', cdpRpcUrl.replace(cdpApiKey || '', '***'))

export const config = getDefaultConfig({
  appName: 'Glisk NFT',
  projectId,
  chains: [network.chain],
  transports: {
    [network.chainId]: http(cdpRpcUrl),
  },
  ssr: true,
})
