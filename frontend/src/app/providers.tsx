'use client'

import { ReactNode, useEffect } from 'react'
import { WagmiProvider } from 'wagmi'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RainbowKitProvider, lightTheme, darkTheme } from '@rainbow-me/rainbowkit'
import { OnchainKitProvider } from '@coinbase/onchainkit'
import { AuthKitProvider } from '@farcaster/auth-kit'
import { ThemeProvider } from 'next-themes'
import { sdk } from '@farcaster/miniapp-sdk'

import { config, network } from '@/lib/wagmi'
import { WalletAvatar } from '@/components/WalletAvatar'
import { Toaster } from '@/components/ui/sonner'

import '@rainbow-me/rainbowkit/styles.css'
import '@coinbase/onchainkit/styles.css'
import '@farcaster/auth-kit/styles.css'

const queryClient = new QueryClient()

// Get CDP API Key for OnchainKit
const cdpApiKey = process.env.NEXT_PUBLIC_ONCHAINKIT_API_KEY

// Farcaster Auth Kit configuration
const farcasterConfig = {
  domain: typeof window !== 'undefined' ? window.location.host : '',
  siweUri: typeof window !== 'undefined' ? window.location.origin : '',
  rpcUrl: 'https://mainnet.optimism.io',
  relay: 'https://relay.farcaster.xyz',
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

export function Providers({ children }: { children: ReactNode }) {
  // Signal Farcaster miniapp is ready (dismisses splash screen)
  useEffect(() => {
    sdk.actions.ready()
  }, [])

  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
      <WagmiProvider config={config}>
        <QueryClientProvider client={queryClient}>
          <OnchainKitProvider apiKey={cdpApiKey} chain={network.chain}>
            <RainbowKitProvider theme={gliskTheme} avatar={WalletAvatar}>
              <AuthKitProvider config={farcasterConfig}>
                {children}
                <Toaster />
              </AuthKitProvider>
            </RainbowKitProvider>
          </OnchainKitProvider>
        </QueryClientProvider>
      </WagmiProvider>
    </ThemeProvider>
  )
}
