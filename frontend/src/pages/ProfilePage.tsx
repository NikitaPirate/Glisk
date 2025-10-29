import { useEffect, useState } from 'react'
import { useAccount, useSignMessage } from 'wagmi'
import { useSearchParams } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { IdentityCard } from '@coinbase/onchainkit/identity'
import { PromptAuthor } from '@/components/PromptAuthor'
import { Collector } from '@/components/Collector'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { network } from '@/lib/wagmi'
import { FarcasterLinkDialogWithButton as FarcasterLinkDialog } from '@/components/FarcasterLinkDialogWithButton'
import { toast } from 'sonner'

type LoadingState = 'idle' | 'fetching' | 'linking' | 'signing'
type SocialProvider = 'x'

interface ProviderConfig {
  id: SocialProvider
  displayName: string
  icon: string
  apiEndpoint: string
  messageTemplate: (address: string) => string
  responseUrlField: string
  callbackParams: {
    linked: string
    username: string
    error: string
  }
}

const SOCIAL_PROVIDERS: Record<SocialProvider, ProviderConfig> = {
  x: {
    id: 'x',
    displayName: 'X',
    icon: '𝕏',
    apiEndpoint: '/api/authors/x/auth/start',
    messageTemplate: addr => `Link X account for wallet: ${addr}`,
    responseUrlField: 'authorization_url',
    callbackParams: { linked: 'x_linked', username: 'username', error: 'error' },
  },
}

// Coinbase Verified attestation schema ID
const COINBASE_VERIFIED_SCHEMA_ID = network.attestationSchema

const VALID_TABS = ['author', 'collector'] as const
type TabType = (typeof VALID_TABS)[number]

export function ProfilePage() {
  const { isConnected, address } = useAccount()
  const [searchParams, setSearchParams] = useSearchParams()
  const queryClient = useQueryClient()

  // Social auth state (unified for all providers)
  const [activeProvider, setActiveProvider] = useState<SocialProvider | null>(null)
  const [socialAuth, setSocialAuth] = useState<
    Record<
      SocialProvider,
      {
        handle: string | null
        loading: LoadingState
        error: string
      }
    >
  >({
    x: { handle: null, loading: 'idle', error: '' },
  })

  // Farcaster auth state (separate from OAuth providers)
  const [farcasterAuth, setFarcasterAuth] = useState<{
    handle: string | null
    loading: LoadingState
    error: string
  }>({
    handle: null,
    loading: 'idle',
    error: '',
  })
  const [farcasterDialogOpen, setFarcasterDialogOpen] = useState(false)
  const [farcasterWalletSig, setFarcasterWalletSig] = useState<{
    address: string
    message: string
    signature: string
  } | null>(null)

  // Share dialog state
  const [shareDialogOpen, setShareDialogOpen] = useState(false)
  const [copySuccess, setCopySuccess] = useState(false)

  // Signature hook for social account linking
  const {
    signMessage,
    signMessageAsync,
    data: signature,
    error: signError,
    reset: resetSignature,
  } = useSignMessage()

  // Get active tab from URL query param, validate and fallback to 'author'
  const tabParam = searchParams.get('tab')
  const activeTab: TabType = VALID_TABS.includes(tabParam as TabType)
    ? (tabParam as TabType)
    : 'author'

  // Set default tab=author when no query param (replace: true prevents back button loop)
  useEffect(() => {
    if (!tabParam) {
      setSearchParams({ tab: 'author' }, { replace: true })
    }
  }, [tabParam, setSearchParams])

  // T065: Invalidate all query caches when wallet address changes
  useEffect(() => {
    if (address) {
      queryClient.invalidateQueries()
    }
  }, [address, queryClient])

  // Handle tab switching (creates history entry for back button)
  const handleTabChange = (tab: TabType) => {
    setSearchParams({ tab })
  }

  // Fetch social account handles on mount and when address changes
  useEffect(() => {
    if (!address) {
      setSocialAuth({
        x: { handle: null, loading: 'idle', error: '' },
      })
      setFarcasterAuth({ handle: null, loading: 'idle', error: '' })
      return
    }

    const fetchAccountStatus = async () => {
      try {
        setSocialAuth(prev => ({
          x: { ...prev.x, loading: 'fetching' },
        }))
        setFarcasterAuth(prev => ({ ...prev, loading: 'fetching' }))

        const response = await fetch(`/api/authors/${address}`)

        if (!response.ok) {
          throw new Error('Failed to fetch account status')
        }

        const data = await response.json()
        setSocialAuth(prev => ({
          x: { ...prev.x, handle: data.twitter_handle || null, loading: 'idle' },
        }))
        setFarcasterAuth(prev => ({
          ...prev,
          handle: data.farcaster_handle || null,
          loading: 'idle',
        }))
      } catch (error) {
        console.error('Failed to fetch account status:', error)
        setSocialAuth(prev => ({
          x: { ...prev.x, loading: 'idle' },
        }))
        setFarcasterAuth(prev => ({ ...prev, loading: 'idle' }))
      }
    }

    fetchAccountStatus()
  }, [address])

  // Check URL query params for social auth callbacks (unified for all providers)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    let hasCallback = false

    Object.values(SOCIAL_PROVIDERS).forEach(provider => {
      const config = provider.callbackParams
      const linked = params.get(config.linked)
      const username = params.get(config.username)
      const error = params.get(config.error)

      if (linked === 'true' && username) {
        setSocialAuth(prev => ({
          ...prev,
          [provider.id]: { ...prev[provider.id], handle: username },
        }))
        hasCallback = true
      } else if (linked === 'false' && error) {
        setSocialAuth(prev => ({
          ...prev,
          [provider.id]: {
            ...prev[provider.id],
            error: `Failed to link ${provider.displayName} account`,
          },
        }))
        hasCallback = true
      }
    })

    // Clean callback params from URL
    if (hasCallback) {
      const cleanUrl = window.location.pathname + '?tab=' + (params.get('tab') || 'author')
      window.history.replaceState({}, '', cleanUrl)
    }
  }, [])

  // Start social auth flow when signature is received (unified for all providers)
  useEffect(() => {
    if (!signature || !address || !activeProvider) return

    const provider = SOCIAL_PROVIDERS[activeProvider]
    const auth = socialAuth[activeProvider]

    if (auth.loading !== 'signing') return

    const startAuth = async () => {
      try {
        setSocialAuth(prev => ({
          ...prev,
          [activeProvider]: { ...prev[activeProvider], loading: 'linking', error: '' },
        }))

        const message = provider.messageTemplate(address)

        const response = await fetch(provider.apiEndpoint, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            wallet_address: address,
            message: message,
            signature: signature,
          }),
        })

        const data = await response.json()

        if (!response.ok) {
          throw new Error(data.detail || `Failed to start ${provider.displayName} auth`)
        }

        window.location.href = data[provider.responseUrlField]
      } catch (error) {
        setSocialAuth(prev => ({
          ...prev,
          [activeProvider]: {
            ...prev[activeProvider],
            loading: 'idle',
            error: `Failed to link ${provider.displayName} account`,
          },
        }))
        console.error(`${provider.displayName} linking failed:`, error)
      } finally {
        setActiveProvider(null)
      }
    }

    startAuth()
  }, [signature, address, activeProvider, socialAuth])

  // Handle signature errors (unified for all providers)
  useEffect(() => {
    if (!signError || !activeProvider) return

    const errorMsg =
      signError.message.includes('User rejected') || signError.message.includes('User denied')
        ? 'Signature cancelled'
        : 'Signature failed'

    setSocialAuth(prev => ({
      ...prev,
      [activeProvider]: {
        ...prev[activeProvider],
        loading: 'idle',
        error: errorMsg,
      },
    }))
    setActiveProvider(null)
  }, [signError, activeProvider])

  // Link social account (unified for all providers)
  const linkSocialAccount = async (providerId: SocialProvider) => {
    if (!address) return

    const provider = SOCIAL_PROVIDERS[providerId]

    setSocialAuth(prev => ({
      ...prev,
      [providerId]: { ...prev[providerId], error: '' },
    }))

    try {
      setActiveProvider(providerId)
      setSocialAuth(prev => ({
        ...prev,
        [providerId]: { ...prev[providerId], loading: 'signing' },
      }))

      const message = provider.messageTemplate(address)
      await signMessage({ message })
    } catch (error) {
      console.error('Signature request failed:', error)
      setActiveProvider(null)
      setSocialAuth(prev => ({
        ...prev,
        [providerId]: { ...prev[providerId], loading: 'idle' },
      }))
    }
  }

  // Link Farcaster account (separate flow with Auth Kit dialog)
  const linkFarcasterAccount = async () => {
    if (!address) return

    setFarcasterAuth(prev => ({ ...prev, error: '' }))

    try {
      setFarcasterAuth(prev => ({ ...prev, loading: 'signing' }))

      const message = `Link Farcaster account for wallet: ${address}`

      // Request wallet signature (async version returns result directly)
      const walletSignature = await signMessageAsync({ message })

      // Save wallet signature data
      setFarcasterWalletSig({
        address,
        message,
        signature: walletSignature,
      })

      // Open Farcaster dialog
      setFarcasterDialogOpen(true)
      setFarcasterAuth(prev => ({ ...prev, loading: 'idle' }))
    } catch (error) {
      setFarcasterAuth(prev => ({ ...prev, loading: 'idle' }))
    }
  }

  // Handle Farcaster link success
  const handleFarcasterSuccess = (username: string, _fid: number) => {
    setFarcasterAuth(prev => ({
      ...prev,
      handle: username,
      loading: 'idle',
      error: '',
    }))
    setFarcasterWalletSig(null)
    resetSignature()

    toast.success(`Farcaster linked: @${username}`)
  }

  // Handle Farcaster link error
  const handleFarcasterError = (error: string) => {
    setFarcasterAuth(prev => ({
      ...prev,
      loading: 'idle',
      error,
    }))
  }

  // Redirect message if not connected
  if (!isConnected) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-2xl">
        <p className="text-sm text-blue-600 dark:text-blue-400">
          Please connect your wallet to access your profile
        </p>
      </div>
    )
  }

  return (
    <div className="page-container">
      <div>
        {/* Identity Card Section */}
        <Card className="px-8 gap-6 mb-16">
          <h2 className="text-2xl font-bold">Your Identity</h2>

          {/* Identity & Social Accounts - Full width responsive layout */}
          <div className="w-full max-w-4xl space-y-8 p-4 sm:p-12">
            {/* Identity Card */}
            <IdentityCard
              address={address as `0x${string}`}
              chain={network.chain}
              schemaId={COINBASE_VERIFIED_SCHEMA_ID}
              className="!p-0 !w-fit"
            />

            {/* Social Accounts - Responsive flex layout */}
            {Object.values(SOCIAL_PROVIDERS).map(provider => {
              const auth = socialAuth[provider.id]
              return (
                <div key={provider.id}>
                  {auth.loading === 'fetching' ? (
                    <p className="text-base text-muted-foreground">Loading...</p>
                  ) : (
                    <div
                      className={
                        auth.handle
                          ? 'flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-8'
                          : 'flex flex-row items-center gap-4 sm:gap-8'
                      }
                    >
                      {/* Icon + Handle/Error Container */}
                      <div className="flex items-center gap-4">
                        {/* Icon */}
                        <span className="text-3xl">{provider.icon}</span>

                        {/* Handle/Error */}
                        <div>
                          {auth.handle && (
                            <p className="text-base text-green-600 dark:text-green-400">
                              ✓ @{auth.handle}
                            </p>
                          )}
                          {auth.error && (
                            <p className="text-sm text-red-600 dark:text-red-400">{auth.error}</p>
                          )}
                        </div>
                      </div>

                      {/* Button */}
                      <Button
                        onClick={() => linkSocialAccount(provider.id)}
                        disabled={auth.loading === 'signing' || auth.loading === 'linking'}
                        variant="secondary"
                        size="lg"
                        className={auth.handle ? 'w-full sm:w-auto' : ''}
                      >
                        {auth.loading === 'signing' || auth.loading === 'linking'
                          ? auth.handle
                            ? 'Rebinding...'
                            : 'Linking...'
                          : auth.handle
                            ? `Rebind ${provider.displayName}`
                            : `Link ${provider.displayName}`}
                      </Button>
                    </div>
                  )}
                </div>
              )
            })}

            {/* Farcaster Account (separate Auth Kit flow) */}
            <div>
              {farcasterAuth.loading === 'fetching' ? (
                <p className="text-base text-muted-foreground">Loading...</p>
              ) : (
                <div
                  className={
                    farcasterAuth.handle
                      ? 'flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-8'
                      : 'flex flex-row items-center gap-4 sm:gap-8'
                  }
                >
                  {/* Icon + Handle/Error Container */}
                  <div className="flex items-center gap-4">
                    {/* Icon */}
                    <img
                      src="/images/farcaster.svg"
                      alt="Farcaster"
                      className="w-[30px] h-[30px]"
                    />

                    {/* Handle/Error */}
                    <div>
                      {farcasterAuth.handle && (
                        <p className="text-base text-green-600 dark:text-green-400">
                          ✓ @{farcasterAuth.handle}
                        </p>
                      )}
                      {farcasterAuth.error && (
                        <p className="text-sm text-red-600 dark:text-red-400">
                          {farcasterAuth.error}
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Button */}
                  <Button
                    onClick={linkFarcasterAccount}
                    disabled={
                      farcasterAuth.loading === 'signing' || farcasterAuth.loading === 'linking'
                    }
                    variant="secondary"
                    size="lg"
                    className={farcasterAuth.handle ? 'w-full sm:w-auto' : ''}
                  >
                    {farcasterAuth.loading === 'signing' || farcasterAuth.loading === 'linking'
                      ? farcasterAuth.handle
                        ? 'Rebinding...'
                        : 'Linking...'
                      : farcasterAuth.handle
                        ? 'Rebind Farcaster'
                        : 'Link Farcaster'}
                  </Button>
                </div>
              )}
            </div>
          </div>

          {/* Share Button */}
          <Button
            onClick={() => setShareDialogOpen(true)}
            variant="primary-action"
            className="w-full h-24 text-6xl font-black mt-8"
          >
            SHARE
          </Button>
        </Card>

        {/* Share Dialog */}
        <Dialog open={shareDialogOpen} onOpenChange={setShareDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Share Your Prompt</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 pt-4">
              {/* Share to X */}
              <Button
                onClick={() => {
                  const tweetText =
                    'My AI prompt is live on @getglisk! Check it out and mint some NFTs ✨'
                  const shareUrl = `https://glisk.xyz/${address}`
                  const twitterUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(
                    tweetText
                  )}&url=${encodeURIComponent(shareUrl)}`
                  window.open(twitterUrl, '_blank')
                  setShareDialogOpen(false)
                }}
                variant="primary-action"
                className="w-full h-16 text-2xl font-bold"
              >
                Share to X
              </Button>

              {/* Copy Link */}
              <Button
                onClick={() => {
                  const shareUrl = `https://glisk.xyz/${address}`
                  navigator.clipboard.writeText(shareUrl)
                  setCopySuccess(true)
                  setTimeout(() => setCopySuccess(false), 2000)
                }}
                variant="secondary"
                className="w-full h-16 text-2xl font-bold"
              >
                {copySuccess ? 'Copied!' : 'Copy Link'}
              </Button>
            </div>
          </DialogContent>
        </Dialog>

        {/* Tab Navigation */}
        <div className="mb-16">
          <div className="grid grid-cols-2 gap-4">
            <Button
              onClick={() => handleTabChange('author')}
              variant={activeTab === 'author' ? 'tab-active' : 'ghost'}
              className="w-full"
            >
              Prompt Author
            </Button>
            <Button
              onClick={() => handleTabChange('collector')}
              variant={activeTab === 'collector' ? 'tab-active' : 'ghost'}
              className="w-full"
            >
              Collector
            </Button>
          </div>
        </div>

        {/* Tab Content */}
        <div>{activeTab === 'author' ? <PromptAuthor /> : <Collector />}</div>

        {/* Farcaster Link Dialog */}
        {farcasterWalletSig && (
          <FarcasterLinkDialog
            open={farcasterDialogOpen}
            onClose={() => setFarcasterDialogOpen(false)}
            walletAddress={farcasterWalletSig.address}
            walletMessage={farcasterWalletSig.message}
            walletSignature={farcasterWalletSig.signature}
            onSuccess={handleFarcasterSuccess}
            onError={handleFarcasterError}
          />
        )}
      </div>
    </div>
  )
}
