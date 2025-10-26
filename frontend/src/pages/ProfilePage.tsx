import { useEffect } from 'react'
import { useAccount } from 'wagmi'
import { useSearchParams } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { IdentityCard } from '@coinbase/onchainkit/identity'
import { baseSepolia } from 'wagmi/chains'
import { PromptAuthor } from '@/components/PromptAuthor'
import { Collector } from '@/components/Collector'
import { Button } from '@/components/ui/button'

// Coinbase Verified attestation schema ID for Base Sepolia
const COINBASE_VERIFIED_SCHEMA_ID =
  '0xf8b05c79f090979bf4a80270aba232dff11a10d9ca55c4f88de95317970f0de9'

const VALID_TABS = ['author', 'collector'] as const
type TabType = (typeof VALID_TABS)[number]

export function ProfilePage() {
  const { isConnected, address } = useAccount()
  const [searchParams, setSearchParams] = useSearchParams()
  const queryClient = useQueryClient()

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

  // Redirect message if not connected
  if (!isConnected) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-2xl">
        <div className="p-4 bg-blue-50 dark:bg-blue-950 rounded">
          <p className="text-blue-800 dark:text-blue-200">
            Please connect your wallet to access your profile
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold mb-2">Profile</h1>
          <p className="text-muted-foreground">Manage your prompt, X account, and view your NFTs</p>
        </div>

        {/* Identity Card Section */}
        <div className="rounded-lg p-6 bg-zinc-50 dark:bg-zinc-900">
          <h2 className="text-xl font-semibold mb-4">Your Identity</h2>
          <IdentityCard
            address={address as `0x${string}`}
            chain={baseSepolia}
            schemaId={COINBASE_VERIFIED_SCHEMA_ID}
          />
        </div>

        {/* Tab Navigation */}
        <div className="space-y-6">
          <div className="flex space-x-2">
            <Button
              onClick={() => handleTabChange('author')}
              variant={activeTab === 'author' ? 'tab-active' : 'ghost'}
            >
              Prompt Author
            </Button>
            <Button
              onClick={() => handleTabChange('collector')}
              variant={activeTab === 'collector' ? 'tab-active' : 'ghost'}
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
