import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { WagmiProvider } from 'wagmi'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RainbowKitProvider } from '@rainbow-me/rainbowkit'
import { OnchainKitProvider } from '@coinbase/onchainkit'
import { baseSepolia } from 'wagmi/chains'

import { config } from './lib/wagmi'
import './index.css'
import '@rainbow-me/rainbowkit/styles.css'
import '@coinbase/onchainkit/styles.css'
import App from './App.tsx'

const queryClient = new QueryClient()

// Get CDP API Key for OnchainKit
const cdpApiKey = import.meta.env.VITE_ONCHAINKIT_API_KEY

// Coinbase Verified attestation schema ID for Base Sepolia
const COINBASE_VERIFIED_SCHEMA_ID =
  '0xf8b05c79f090979bf4a80270aba232dff11a10d9ca55c4f88de95317970f0de9'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <WagmiProvider config={config}>
      <QueryClientProvider client={queryClient}>
        <OnchainKitProvider
          apiKey={cdpApiKey}
          chain={baseSepolia}
          schemaId={COINBASE_VERIFIED_SCHEMA_ID}
          config={{
            appearance: {
              mode: 'light',
            },
          }}
        >
          <RainbowKitProvider>
            <App />
          </RainbowKitProvider>
        </OnchainKitProvider>
      </QueryClientProvider>
    </WagmiProvider>
  </StrictMode>
)
