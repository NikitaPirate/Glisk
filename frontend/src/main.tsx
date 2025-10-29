import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { WagmiProvider } from 'wagmi'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RainbowKitProvider, lightTheme, darkTheme } from '@rainbow-me/rainbowkit'
import { OnchainKitProvider } from '@coinbase/onchainkit'
import { AuthKitProvider } from '@farcaster/auth-kit'

import { config, network } from './lib/wagmi'
import { WalletAvatar } from './components/WalletAvatar'
import './index.css'
import '@rainbow-me/rainbowkit/styles.css'
import '@coinbase/onchainkit/styles.css'
import '@farcaster/auth-kit/styles.css'
import App from './App.tsx'

const queryClient = new QueryClient()

// Get CDP API Key for OnchainKit
const cdpApiKey = import.meta.env.VITE_ONCHAINKIT_API_KEY

// Farcaster Auth Kit configuration
const farcasterConfig = {
  domain: window.location.host,
  siweUri: window.location.origin, // Use origin (no path/query) for SIWE validation
  rpcUrl: 'https://mainnet.optimism.io',
  relay: 'https://relay.farcaster.xyz', // Explicit relay URL for clarity
}

// Glisk custom theme using CSS variables from design system
const createGliskTheme = (baseTheme: typeof lightTheme) => {
  return {
    ...baseTheme({
      borderRadius: 'small', // Sharp corners (2px) matching Glisk design
    }),
    colors: {
      ...baseTheme({ borderRadius: 'small' }).colors,
      accentColor: 'var(--color-primary)', // #FFBB00 yellow
      accentColorForeground: 'var(--color-primary-foreground)', // black
      modalBackground: 'var(--color-card)', // cyan-50/950
      modalBorder: 'var(--color-border)', // cyan-400/600
      modalText: 'var(--color-foreground)', // zinc-950/50
      modalTextSecondary: 'var(--color-muted-foreground)', // cyan-600/400
    },
    shadows: {
      connectButton: '4px 4px 0px 0px rgb(var(--shadow-color))',
      dialog: '6px 6px 0px 0px rgb(var(--shadow-color))',
      profileDetailsAction: '2px 2px 0px 0px rgb(var(--shadow-color))',
      selectedOption: '2px 2px 0px 0px rgb(var(--shadow-color))',
      selectedWallet: '2px 2px 0px 0px rgb(var(--shadow-color))',
      walletLogo: 'none',
    },
  }
}

const gliskTheme = {
  lightMode: createGliskTheme(lightTheme),
  darkMode: createGliskTheme(darkTheme),
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <WagmiProvider config={config}>
      <QueryClientProvider client={queryClient}>
        <OnchainKitProvider apiKey={cdpApiKey} chain={network.chain}>
          <RainbowKitProvider theme={gliskTheme} avatar={WalletAvatar}>
            <AuthKitProvider config={farcasterConfig}>
              <App />
            </AuthKitProvider>
          </RainbowKitProvider>
        </OnchainKitProvider>
      </QueryClientProvider>
    </WagmiProvider>
  </StrictMode>
)
