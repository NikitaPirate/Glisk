import { useEffect } from 'react'
import { useAccount } from 'wagmi'
import { useSearchParams } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { PromptAuthor } from '@/components/PromptAuthor'
import { Collector } from '@/components/Collector'
import { Button } from '@/components/ui/button'

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
        <div className="p-4 bg-blue-50 border border-blue-200 rounded">
          <p className="text-blue-800">Please connect your wallet to access your profile</p>
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
          <p className="text-gray-600">Manage your prompt, X account, and view your NFTs</p>
        </div>

        {/* Tab Navigation */}
        <div className="border-b border-gray-200">
          <div className="flex space-x-1">
            <Button
              onClick={() => handleTabChange('author')}
              variant={activeTab === 'author' ? 'default' : 'ghost'}
              className={`rounded-b-none ${
                activeTab === 'author'
                  ? 'border-b-2 border-blue-500'
                  : 'border-b-2 border-transparent'
              }`}
            >
              Prompt Author
            </Button>
            <Button
              onClick={() => handleTabChange('collector')}
              variant={activeTab === 'collector' ? 'default' : 'ghost'}
              className={`rounded-b-none ${
                activeTab === 'collector'
                  ? 'border-b-2 border-blue-500'
                  : 'border-b-2 border-transparent'
              }`}
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
