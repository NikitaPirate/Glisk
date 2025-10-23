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

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <WagmiProvider config={config}>
      <QueryClientProvider client={queryClient}>
        <OnchainKitProvider
          apiKey={cdpApiKey}
          chain={baseSepolia}
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
