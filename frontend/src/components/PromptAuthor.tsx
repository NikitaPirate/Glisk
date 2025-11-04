import { useState, useEffect, useCallback } from 'react'
import { useAccount, useSignMessage, useReadContract } from 'wagmi'
import { useQuery } from '@tanstack/react-query'
import { formatEther } from 'viem'
import { Transaction, TransactionButton } from '@coinbase/onchainkit/transaction'
import type { LifecycleStatus } from '@coinbase/onchainkit/transaction'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { NFTGrid } from '@/components/NFTGrid'
import { CONTRACT_ADDRESS, GLISK_NFT_ABI } from '@/lib/contract'
import { network } from '@/lib/wagmi'
import { useEthPrice } from '@/hooks/useEthPrice'

type PromptStatus = 'loading' | 'has_prompt' | 'no_prompt' | 'error'
type SaveStatus = 'idle' | 'signing' | 'saving' | 'success' | 'error' | 'cancelled'
type ClaimStatus = 'idle' | 'pending' | 'success' | 'failed' | 'cancelled'

// T027, T028: TypeScript interfaces for authored NFTs API
interface TokenDTO {
  token_id: number
  status: string
  image_cid: string | null
  metadata_cid: string | null
  image_url: string | null
  generation_attempts: number
  generation_error: string | null
  reveal_tx_hash: string | null
  created_at: string
}

interface TokensResponse {
  tokens: TokenDTO[]
  total: number
  offset: number
  limit: number
}

// T029: Fetch authored tokens from backend API
async function fetchAuthoredTokens(walletAddress: string, page: number): Promise<TokensResponse> {
  const offset = (page - 1) * 20
  const response = await fetch(`/api/authors/${walletAddress}/tokens?offset=${offset}&limit=20`)

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${await response.text()}`)
  }

  return response.json()
}

export function PromptAuthor() {
  const { address } = useAccount()

  // Prompt management state
  const [promptText, setPromptText] = useState('')
  const [promptStatus, setPromptStatus] = useState<PromptStatus>('loading')
  const [saveStatus, setSaveStatus] = useState<SaveStatus>('idle')
  const [promptErrorMessage, setPromptErrorMessage] = useState('')
  const [promptSuccessMessage, setPromptSuccessMessage] = useState('')

  // T031: Pagination state for authored NFTs
  const [authoredPage, setAuthoredPage] = useState(1)

  // T030: useQuery hook for authored NFTs data
  const {
    data: authoredNFTsData,
    error: authoredNFTsError,
    isLoading: authoredNFTsLoading,
  } = useQuery({
    queryKey: ['authored-nfts', address, authoredPage],
    queryFn: () => fetchAuthoredTokens(address!, authoredPage),
    enabled: !!address,
    staleTime: 30000, // 30 seconds cache
  })

  // T032: Calculate total pages for pagination
  const totalPages = Math.ceil((authoredNFTsData?.total || 0) / 20)

  // Signature hook for prompt save
  const { signMessage, data: signature, error: signError } = useSignMessage()

  // Claim transaction state
  const [claimStatus, setClaimStatus] = useState<ClaimStatus>('idle')
  const [claimError, setClaimError] = useState<string | null>(null)

  // Rewards claiming hooks
  const {
    data: claimableBalance,
    isLoading: balanceLoading,
    refetch: refetchBalance,
  } = useReadContract({
    address: CONTRACT_ADDRESS,
    abi: GLISK_NFT_ABI,
    functionName: 'authorClaimable',
    args: address ? [address] : undefined,
    query: { enabled: !!address },
  })

  // ETH/USD price hook
  const { data: ethPriceUsd } = useEthPrice()

  // Handle OnchainKit Transaction lifecycle for claim rewards
  const handleClaimStatus = useCallback(
    (status: LifecycleStatus) => {
      console.log('[Claim] Lifecycle status:', status)
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const statusData = status.statusData as any

      switch (status.statusName) {
        case 'init':
        case 'transactionIdle':
          setClaimStatus('idle')
          setClaimError(null)
          break
        case 'buildingTransaction':
        case 'transactionPending':
          setClaimStatus('pending')
          break
        case 'success':
          setClaimStatus('success')
          setClaimError(null)
          // Refetch balance after successful claim
          refetchBalance()
          break
        case 'error': {
          const errorMessage =
            typeof statusData === 'string'
              ? statusData
              : statusData?.message || statusData?.error?.message || ''
          if (
            errorMessage.includes('User rejected') ||
            errorMessage.includes('User denied') ||
            errorMessage.includes('rejected') ||
            errorMessage.includes('denied')
          ) {
            setClaimStatus('cancelled')
            setClaimError('Transaction cancelled')
          } else {
            setClaimStatus('failed')
            setClaimError(errorMessage || 'Failed to claim rewards')
          }
          break
        }
      }
    },
    [refetchBalance]
  )

  // Prepare contract calls for claim rewards
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const claimCalls: any[] = !address
    ? []
    : [
        {
          address: CONTRACT_ADDRESS,
          abi: GLISK_NFT_ABI,
          functionName: 'claimAuthorRewards',
        },
      ]

  /**
   * Fetch author status on mount and when address changes
   */
  useEffect(() => {
    if (!address) {
      setPromptStatus('no_prompt')
      return
    }

    const fetchAuthorStatus = async () => {
      try {
        setPromptStatus('loading')
        const response = await fetch(`/api/authors/${address}`)

        if (!response.ok) {
          throw new Error('Failed to fetch author status')
        }

        const data = await response.json()
        setPromptStatus(data.has_prompt ? 'has_prompt' : 'no_prompt')
      } catch (error) {
        console.error('Failed to fetch author status:', error)
        setPromptStatus('error')
      }
    }

    fetchAuthorStatus()
  }, [address])

  /**
   * Save prompt when signature is received (for prompt save)
   */
  useEffect(() => {
    if (!signature || !address || saveStatus !== 'signing') {
      return
    }

    const savePrompt = async () => {
      try {
        setSaveStatus('saving')
        setPromptErrorMessage('')

        const message = `Update GLISK prompt for wallet: ${address}`

        const response = await fetch('/api/authors/prompt', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            wallet_address: address,
            prompt_text: promptText,
            message: message,
            signature: signature,
          }),
        })

        const data = await response.json()

        if (!response.ok) {
          throw new Error(data.detail || 'Failed to save prompt')
        }

        // Success
        setSaveStatus('success')
        setPromptSuccessMessage('Prompt saved successfully!')
        setPromptStatus('has_prompt')
        setPromptText('') // Clear input (write-only)

        // Clear success message after 5 seconds
        setTimeout(() => {
          setPromptSuccessMessage('')
          setSaveStatus('idle')
        }, 5000)
      } catch (error) {
        setSaveStatus('error')
        setPromptErrorMessage(
          error instanceof Error ? error.message : 'Failed to save prompt. Please try again.'
        )
      }
    }

    savePrompt()
  }, [signature, address, promptText, saveStatus])

  /**
   * Handle signature errors (rejection, etc.)
   */
  useEffect(() => {
    if (!signError) {
      return
    }

    // Check for user rejection
    if (signError.message.includes('User rejected') || signError.message.includes('User denied')) {
      if (saveStatus === 'signing') {
        setSaveStatus('cancelled')
        setPromptErrorMessage('Signature cancelled. Your prompt was not saved.')
      }
    } else {
      if (saveStatus === 'signing') {
        setSaveStatus('error')
        setPromptErrorMessage('Signature failed. Please try again.')
      }
    }
  }, [signError, saveStatus])

  /**
   * Wallet change detection - clear state when wallet changes
   */
  useEffect(() => {
    if (address) {
      // Clear prompt error messages
      setPromptErrorMessage('')
      setPromptSuccessMessage('')
      setSaveStatus('idle')

      // T042: Reset pagination when wallet changes
      setAuthoredPage(1)
    }
  }, [address])

  /**
   * Handle save prompt button click
   */
  const handleSavePrompt = async () => {
    if (!address) return

    // Validate prompt length
    if (promptText.length < 1 || promptText.length > 1000) {
      setPromptErrorMessage('Prompt must be between 1 and 1000 characters')
      return
    }

    // Clear previous messages
    setPromptErrorMessage('')
    setPromptSuccessMessage('')

    // Request signature
    try {
      setSaveStatus('signing')
      const message = `Update GLISK prompt for wallet: ${address}`
      await signMessage({ message, account: address })
    } catch (error) {
      // Error will be handled by useEffect watching signError
      console.error('Signature request failed:', error)
    }
  }

  return (
    <div className="space-y-16">
      {/* Prompt Editor Section */}
      <Card className="px-8 gap-6">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold">Prompt</h2>
          {promptStatus === 'loading' && (
            <p className="text-sm text-muted-foreground">Loading...</p>
          )}
          {promptStatus === 'has_prompt' && (
            <p className="text-sm text-green-600 dark:text-green-400">✓ Configured</p>
          )}
          {promptStatus === 'no_prompt' && (
            <p className="text-sm text-yellow-600 dark:text-yellow-400">⚠ Not set</p>
          )}
          {promptStatus === 'error' && (
            <p className="text-sm text-red-600 dark:text-red-400">Failed to load status</p>
          )}
        </div>

        <textarea
          id="prompt"
          value={promptText}
          onChange={e => setPromptText(e.target.value)}
          className="w-full min-h-[120px] p-6 rounded-none bg-accent shadow-interactive focus-lift focus-darken focus:outline-none resize-y transition-all"
          maxLength={1001}
        />

        <Button
          onClick={handleSavePrompt}
          disabled={
            !address ||
            promptText.length < 1 ||
            promptText.length > 1000 ||
            saveStatus === 'signing' ||
            saveStatus === 'saving'
          }
          variant="primary-action"
          size="xl"
          className="w-full mt-6"
        >
          {saveStatus === 'signing'
            ? 'Waiting for signature...'
            : saveStatus === 'saving'
              ? 'Saving...'
              : 'Save Prompt'}
        </Button>

        {/* Prompt Status Messages */}
        {saveStatus === 'signing' && (
          <p className="text-sm text-blue-600 dark:text-blue-400">
            Please sign the message in your wallet to continue
          </p>
        )}

        {saveStatus === 'cancelled' && (
          <p className="text-sm text-yellow-600 dark:text-yellow-400">{promptErrorMessage}</p>
        )}

        {saveStatus === 'error' && (
          <p className="text-sm text-red-600 dark:text-red-400">{promptErrorMessage}</p>
        )}

        {saveStatus === 'success' && (
          <p className="text-sm text-green-600 dark:text-green-400">{promptSuccessMessage}</p>
        )}
      </Card>

      {/* Rewards Section */}
      <Card className="px-8 gap-6">
        <h2 className="text-2xl font-bold">Your Rewards</h2>

        {balanceLoading ? (
          <p className="text-sm text-muted-foreground">Loading balance...</p>
        ) : (
          <>
            <div className="space-y-2">
              <div className="text-4xl font-bold">
                {formatEther(typeof claimableBalance === 'bigint' ? claimableBalance : 0n)} ETH
              </div>
              {ethPriceUsd && (
                <div className="text-2xl text-muted-foreground">
                  ≈ $
                  {(
                    parseFloat(
                      formatEther(typeof claimableBalance === 'bigint' ? claimableBalance : 0n)
                    ) * ethPriceUsd
                  ).toFixed(2)}{' '}
                  USD
                </div>
              )}
            </div>

            <Transaction
              calls={claimCalls}
              chainId={network.chainId}
              onStatus={handleClaimStatus}
              isSponsored={true}
            >
              <TransactionButton
                disabled={
                  !address ||
                  !claimableBalance ||
                  claimableBalance === 0n ||
                  claimStatus === 'pending'
                }
                className="w-full h-16 text-2xl font-black bg-[#FFBB00] hover:bg-[#FFBB00] text-black hover:text-black shadow-interactive-lg hover-lift-lg active-press-lg disabled:opacity-50"
                text={claimStatus === 'pending' ? 'Claiming...' : 'Claim Rewards'}
              />
            </Transaction>

            {claimStatus === 'success' && (
              <p className="text-sm text-green-600 dark:text-green-400">
                Rewards claimed successfully!
              </p>
            )}

            {claimStatus === 'cancelled' && (
              <p className="text-sm text-yellow-600 dark:text-yellow-400">
                {claimError || 'Transaction cancelled'}
              </p>
            )}

            {claimStatus === 'failed' && (
              <p className="text-sm text-red-600 dark:text-red-400">
                {claimError || 'Failed to claim rewards. Please try again.'}
              </p>
            )}
          </>
        )}
      </Card>

      {/* T043: Authored NFTs Section */}
      <Card className="px-8 gap-6">
        <h2 className="text-2xl font-bold">Your Authored NFTs</h2>

        {/* T036: Loading state */}
        {authoredNFTsLoading && <p className="text-sm text-muted-foreground">Loading...</p>}

        {/* T037: Error state */}
        {!authoredNFTsLoading && authoredNFTsError && (
          <p className="text-sm text-red-600 dark:text-red-400">Error</p>
        )}

        {/* T038: Empty state */}
        {!authoredNFTsLoading &&
          !authoredNFTsError &&
          authoredNFTsData &&
          authoredNFTsData.total === 0 && <p className="text-sm text-muted-foreground">No NFTs</p>}

        {/* NFT Grid */}
        {!authoredNFTsLoading &&
          !authoredNFTsError &&
          authoredNFTsData &&
          authoredNFTsData.total > 0 && (
            <>
              <NFTGrid
                tokens={authoredNFTsData.tokens.map(token => ({
                  tokenId: token.token_id.toString(),
                }))}
              />

              {/* T039, T040, T041: Pagination controls */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between pt-4">
                  <Button
                    onClick={() => setAuthoredPage(p => p - 1)}
                    disabled={authoredPage === 1 || authoredNFTsLoading}
                    variant="ghost"
                  >
                    Previous
                  </Button>
                  <p className="text-sm text-muted-foreground">
                    Page {authoredPage} of {totalPages}
                  </p>
                  <Button
                    onClick={() => setAuthoredPage(p => p + 1)}
                    disabled={authoredPage === totalPages || authoredNFTsLoading}
                    variant="ghost"
                  >
                    Next
                  </Button>
                </div>
              )}
            </>
          )}
      </Card>
    </div>
  )
}
