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

type LoadingState = 'idle' | 'fetching' | 'linking' | 'signing'

// Coinbase Verified attestation schema ID
const COINBASE_VERIFIED_SCHEMA_ID = network.attestationSchema

const VALID_TABS = ['author', 'collector'] as const
type TabType = (typeof VALID_TABS)[number]

export function ProfilePage() {
  const { isConnected, address } = useAccount()
  const [searchParams, setSearchParams] = useSearchParams()
  const queryClient = useQueryClient()

  // X linking state
  const [twitterHandle, setTwitterHandle] = useState<string | null>(null)
  const [xLoading, setXLoading] = useState<LoadingState>('idle')
  const [xErrorMessage, setXErrorMessage] = useState('')

  // Share dialog state
  const [shareDialogOpen, setShareDialogOpen] = useState(false)
  const [copySuccess, setCopySuccess] = useState(false)

  // Signature hook for X linking
  const { signMessage, data: signature, error: signError } = useSignMessage()

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
      console.log('[ProfilePage] Wallet changed to:', address, '- clearing all query caches')
      queryClient.invalidateQueries()
    }
  }, [address, queryClient])

  // Handle tab switching (creates history entry for back button)
  const handleTabChange = (tab: TabType) => {
    setSearchParams({ tab })
  }

  // Fetch X account status on mount and when address changes
  useEffect(() => {
    if (!address) {
      setTwitterHandle(null)
      return
    }

    const fetchXStatus = async () => {
      try {
        setXLoading('fetching')
        const response = await fetch(`/api/authors/${address}`)

        if (!response.ok) {
          throw new Error('Failed to fetch X status')
        }

        const data = await response.json()
        setTwitterHandle(data.twitter_handle || null)
      } catch (error) {
        console.error('Failed to fetch X status:', error)
      } finally {
        setXLoading('idle')
      }
    }

    fetchXStatus()
  }, [address])

  // Check URL query params for X OAuth callback
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const xLinked = params.get('x_linked')
    const username = params.get('username')
    const error = params.get('error')

    if (xLinked === 'true' && username) {
      setTwitterHandle(username)
      window.history.replaceState(
        {},
        '',
        window.location.pathname +
          window.location.search.replace(/[?&]x_linked=true(&username=[^&]+)?/, '')
      )
    } else if (xLinked === 'false' && error) {
      setXErrorMessage('Failed to link X account')
      window.history.replaceState({}, '', window.location.pathname)
    }
  }, [])

  // Start X OAuth flow when signature is received
  useEffect(() => {
    if (!signature || !address || xLoading !== 'signing') {
      return
    }

    const startOAuth = async () => {
      try {
        setXLoading('linking')
        setXErrorMessage('')

        const message = `Link X account for wallet: ${address}`

        const response = await fetch('/api/authors/x/auth/start', {
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
          throw new Error(data.detail || 'Failed to start X OAuth')
        }

        window.location.href = data.authorization_url
      } catch (error) {
        setXLoading('idle')
        setXErrorMessage('Failed to link X account')
      }
    }

    startOAuth()
  }, [signature, address, xLoading])

  // Handle signature errors
  useEffect(() => {
    if (!signError) return

    if (signError.message.includes('User rejected') || signError.message.includes('User denied')) {
      if (xLoading === 'signing') {
        setXLoading('idle')
        setXErrorMessage('Signature cancelled')
      }
    } else {
      if (xLoading === 'signing') {
        setXLoading('idle')
        setXErrorMessage('Signature failed')
      }
    }
  }, [signError, xLoading])

  // Link X account function
  const linkXAccount = async () => {
    if (!address) return
    setXErrorMessage('')
    try {
      setXLoading('signing')
      const message = `Link X account for wallet: ${address}`
      await signMessage({ message })
    } catch (error) {
      console.error('Signature request failed:', error)
    }
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
    <div className="container mx-auto px-12 py-20 max-w-4xl">
      <div>
        {/* Identity Card Section */}
        <Card className="px-8 gap-6 mb-16">
          <h2 className="text-2xl font-bold">Your Identity</h2>

          <div className="flex flex-wrap gap-8 items-center p-16">
            {/* Left: IdentityCard */}
            <div className="flex-1 min-w-64">
              <IdentityCard
                address={address as `0x${string}`}
                chain={network.chain}
                schemaId={COINBASE_VERIFIED_SCHEMA_ID}
              />
            </div>

            {/* Right: X Account */}
            <div className="flex-1 p-4 min-w-64 max-w-lg space-y-4">
              {xLoading === 'fetching' ? (
                <p className="text-base text-muted-foreground">Loading...</p>
              ) : (
                <div className="flex items-center gap-4">
                  <span className="text-3xl">𝕏</span>

                  {twitterHandle && (
                    <p className="text-base text-green-600 dark:text-green-400 whitespace-nowrap">
                      ✓ @{twitterHandle}
                    </p>
                  )}

                  <Button
                    onClick={linkXAccount}
                    disabled={xLoading === 'signing' || xLoading === 'linking'}
                    variant="secondary"
                    size="lg"
                  >
                    {xLoading === 'signing' || xLoading === 'linking'
                      ? twitterHandle
                        ? 'Rebinding...'
                        : 'Linking...'
                      : twitterHandle
                        ? 'Rebind X'
                        : 'Link X'}
                  </Button>
                </div>
              )}

              {xErrorMessage && (
                <p className="text-sm text-red-600 dark:text-red-400">{xErrorMessage}</p>
              )}
            </div>
          </div>

          {/* Share Button */}
          <Button
            onClick={() => setShareDialogOpen(true)}
            variant="primary-action"
            className="w-full h-24 text-6xl font-black"
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
      </div>
    </div>
  )
}
