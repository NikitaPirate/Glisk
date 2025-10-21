import { useState, useEffect } from 'react'
import {
  useAccount,
  useSignMessage,
  useReadContract,
  useWriteContract,
  useWaitForTransactionReceipt,
} from 'wagmi'
import { formatEther } from 'viem'
import { Button } from '@/components/ui/button'
import { CONTRACT_ADDRESS, GLISK_NFT_ABI } from '@/lib/contract'

// API base URL (configurable via environment variable)
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

type PromptStatus = 'loading' | 'has_prompt' | 'no_prompt' | 'error'
type SaveStatus = 'idle' | 'signing' | 'saving' | 'success' | 'error' | 'cancelled'

export function CreatorDashboard() {
  const { address, isConnected } = useAccount()
  const [promptText, setPromptText] = useState('')
  const [promptStatus, setPromptStatus] = useState<PromptStatus>('loading')
  const [saveStatus, setSaveStatus] = useState<SaveStatus>('idle')
  const [errorMessage, setErrorMessage] = useState('')
  const [successMessage, setSuccessMessage] = useState('')

  // Signature hook
  const { signMessage, data: signature, error: signError } = useSignMessage()

  // Rewards claiming hooks
  const {
    data: claimableWei,
    isLoading: isLoadingBalance,
    error: balanceError,
    refetch: refetchBalance,
  } = useReadContract({
    address: CONTRACT_ADDRESS,
    abi: GLISK_NFT_ABI,
    functionName: 'authorClaimable',
    args: address ? [address] : undefined,
  })

  const {
    writeContract,
    data: claimTxHash,
    error: claimError,
    isPending: isClaimPending,
  } = useWriteContract()

  const { isLoading: isConfirming, isSuccess: isClaimSuccess } = useWaitForTransactionReceipt({
    hash: claimTxHash,
  })

  /**
   * Fetch author prompt status on mount and when address changes
   */
  useEffect(() => {
    if (!address) {
      setPromptStatus('no_prompt')
      return
    }

    const fetchPromptStatus = async () => {
      try {
        setPromptStatus('loading')
        const response = await fetch(`${API_BASE_URL}/api/authors/${address}`)

        if (!response.ok) {
          throw new Error('Failed to fetch author status')
        }

        const data = await response.json()
        setPromptStatus(data.has_prompt ? 'has_prompt' : 'no_prompt')
      } catch (error) {
        console.error('Failed to fetch prompt status:', error)
        setPromptStatus('error')
      }
    }

    fetchPromptStatus()
  }, [address])

  /**
   * Save prompt when signature is received
   */
  useEffect(() => {
    if (!signature || !address || saveStatus !== 'signing') {
      return
    }

    const savePrompt = async () => {
      try {
        setSaveStatus('saving')
        setErrorMessage('')

        const message = `Update GLISK prompt for wallet: ${address}`

        const response = await fetch(`${API_BASE_URL}/api/authors/prompt`, {
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
        setSuccessMessage('Prompt saved successfully!')
        setPromptStatus('has_prompt')
        setPromptText('') // Clear input (write-only)

        // Clear success message after 5 seconds
        setTimeout(() => {
          setSuccessMessage('')
          setSaveStatus('idle')
        }, 5000)
      } catch (error) {
        setSaveStatus('error')
        setErrorMessage(
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
      setSaveStatus('cancelled')
      setErrorMessage('Signature cancelled. Your prompt was not saved.')
    } else {
      setSaveStatus('error')
      setErrorMessage('Signature failed. Please try again.')
    }
  }, [signError])

  /**
   * Handle save button click
   */
  const handleSave = async () => {
    if (!address) return

    // Validate prompt length
    if (promptText.length < 1 || promptText.length > 1000) {
      setErrorMessage('Prompt must be between 1 and 1000 characters')
      return
    }

    // Clear previous messages
    setErrorMessage('')
    setSuccessMessage('')

    // Request signature
    try {
      setSaveStatus('signing')
      const message = `Update GLISK prompt for wallet: ${address}`
      await signMessage({ message })
    } catch (error) {
      // Error will be handled by useEffect watching signError
      console.error('Signature request failed:', error)
    }
  }

  /**
   * Handle claim rewards button click
   */
  const handleClaim = () => {
    writeContract({
      address: CONTRACT_ADDRESS,
      abi: GLISK_NFT_ABI,
      functionName: 'claimAuthorRewards',
    })
  }

  /**
   * Refetch balance after successful claim
   */
  useEffect(() => {
    if (isClaimSuccess) {
      refetchBalance()
    }
  }, [isClaimSuccess, refetchBalance])

  /**
   * Wallet change detection - reload data when address changes
   * Clears previous state and refetches both prompt status and balance
   */
  useEffect(() => {
    if (address) {
      // Clear any previous error messages when wallet changes
      setErrorMessage('')
      setSuccessMessage('')
      setSaveStatus('idle')

      // Refetch balance for new wallet
      refetchBalance()
    }
  }, [address, refetchBalance])

  /**
   * Character counter display
   */
  const charCount = promptText.length
  const charCountColor =
    charCount === 0
      ? 'text-gray-500'
      : charCount > 1000
        ? 'text-red-600'
        : charCount > 900
          ? 'text-yellow-600'
          : 'text-gray-700'

  // Redirect message if not connected
  if (!isConnected) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-2xl">
        <div className="p-4 bg-blue-50 border border-blue-200 rounded">
          <p className="text-blue-800">
            Please connect your wallet to access the Creator Dashboard
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-2xl">
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold mb-2">Creator Dashboard</h1>
          <p className="text-gray-600">Manage your AI generation prompt and claim rewards</p>
        </div>

        {/* Prompt Status Indicator */}
        <div>
          {promptStatus === 'loading' && (
            <div className="p-3 bg-gray-50 border border-gray-200 rounded inline-block">
              <p className="text-sm text-gray-700">Loading status...</p>
            </div>
          )}
          {promptStatus === 'has_prompt' && (
            <div className="p-3 bg-green-50 border border-green-200 rounded inline-block">
              <p className="text-sm text-green-800">✓ Prompt configured</p>
            </div>
          )}
          {promptStatus === 'no_prompt' && (
            <div className="p-3 bg-yellow-50 border border-yellow-200 rounded inline-block">
              <p className="text-sm text-yellow-800">⚠ No prompt set</p>
            </div>
          )}
          {promptStatus === 'error' && (
            <div className="p-3 bg-red-50 border border-red-200 rounded inline-block">
              <p className="text-sm text-red-800">Failed to load status</p>
            </div>
          )}
        </div>

        {/* Prompt Editor Section */}
        <div className="space-y-4 border border-gray-200 rounded-lg p-6 bg-white">
          <h2 className="text-xl font-semibold">AI Generation Prompt</h2>
          <p className="text-sm text-gray-600">
            Set your AI generation prompt for NFTs minted with your wallet address. This prompt
            controls how AI generates images for your tokens.
          </p>

          <div className="space-y-2">
            <label htmlFor="prompt" className="block text-sm font-medium text-gray-700">
              Prompt Text (1-1000 characters):
            </label>
            <textarea
              id="prompt"
              value={promptText}
              onChange={e => setPromptText(e.target.value)}
              placeholder="e.g., Surreal neon landscapes with futuristic architecture"
              className="w-full min-h-[120px] px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-y"
              maxLength={1001} // Allow typing to 1001 to show validation error
            />
            <div className="flex justify-between items-center">
              <p className={`text-sm ${charCountColor}`}>
                {charCount} / 1000 characters
                {charCount > 1000 && ' (exceeds limit)'}
                {charCount === 0 && ' (minimum 1 character)'}
              </p>
            </div>
          </div>

          <Button
            onClick={handleSave}
            disabled={
              !address ||
              promptText.length < 1 ||
              promptText.length > 1000 ||
              saveStatus === 'signing' ||
              saveStatus === 'saving'
            }
            className="w-full max-w-xs"
          >
            {saveStatus === 'signing'
              ? 'Waiting for signature...'
              : saveStatus === 'saving'
                ? 'Saving...'
                : 'Save Prompt'}
          </Button>

          {/* Status Messages */}
          {saveStatus === 'signing' && (
            <div className="p-4 bg-blue-50 border border-blue-200 rounded">
              <p className="text-blue-800">Please sign the message in your wallet to continue</p>
            </div>
          )}

          {saveStatus === 'cancelled' && (
            <div className="p-4 bg-yellow-50 border border-yellow-200 rounded">
              <p className="text-yellow-800">{errorMessage}</p>
            </div>
          )}

          {saveStatus === 'error' && (
            <div className="p-4 bg-red-50 border border-red-200 rounded">
              <p className="text-red-800">{errorMessage}</p>
            </div>
          )}

          {saveStatus === 'success' && (
            <div className="p-4 bg-green-50 border border-green-200 rounded">
              <p className="text-green-800">{successMessage}</p>
            </div>
          )}
        </div>

        {/* Rewards Claiming Section */}
        <div className="space-y-4 border border-gray-200 rounded-lg p-6 bg-white">
          <h2 className="text-xl font-semibold">Creator Rewards</h2>
          <p className="text-sm text-gray-600">
            Claim accumulated ETH rewards from NFTs minted with your wallet as the prompt author.
            You earn 50% of each mint price.
          </p>

          {/* Balance Display */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700">Claimable Balance:</label>
            {isLoadingBalance ? (
              <p className="text-2xl font-bold text-gray-700">Loading...</p>
            ) : balanceError ? (
              <div className="space-y-2">
                <div className="p-3 bg-red-50 border border-red-200 rounded">
                  <p className="text-sm text-red-800 mb-2">
                    Failed to load balance. The RPC endpoint may be unavailable or experiencing high
                    traffic.
                  </p>
                  <Button
                    onClick={() => refetchBalance()}
                    variant="outline"
                    size="sm"
                    className="text-xs"
                  >
                    Retry
                  </Button>
                </div>
                <p className="text-sm text-gray-500">
                  If this issue persists, try switching to a different RPC endpoint in your wallet
                  settings.
                </p>
              </div>
            ) : (
              <p className="text-2xl font-bold text-gray-900">
                {claimableWei ? formatEther(claimableWei as bigint) : '0.00'} ETH
              </p>
            )}
          </div>

          {/* Claim Button */}
          <Button
            onClick={handleClaim}
            disabled={
              !address ||
              isLoadingBalance ||
              !claimableWei ||
              (claimableWei as bigint) === 0n ||
              isClaimPending ||
              isConfirming
            }
            className="w-full max-w-xs"
          >
            {isClaimPending
              ? 'Waiting for wallet...'
              : isConfirming
                ? 'Confirming transaction...'
                : 'Claim Rewards'}
          </Button>

          {/* Transaction Status Messages */}
          {isClaimPending && (
            <div className="p-4 bg-blue-50 border border-blue-200 rounded">
              <p className="text-blue-800">Please approve the transaction in your wallet</p>
            </div>
          )}

          {isConfirming && (
            <div className="p-4 bg-blue-50 border border-blue-200 rounded">
              <p className="text-blue-800">
                Transaction submitted. Waiting for confirmation...
                {claimTxHash && (
                  <span className="block mt-1 text-xs font-mono break-all">Tx: {claimTxHash}</span>
                )}
              </p>
            </div>
          )}

          {isClaimSuccess && (
            <div className="p-4 bg-green-50 border border-green-200 rounded">
              <p className="text-green-800">
                ✓ Rewards claimed successfully! ETH has been transferred to your wallet.
              </p>
            </div>
          )}

          {claimError && (
            <div className="p-4 bg-red-50 border border-red-200 rounded">
              <p className="text-red-800">
                {claimError.message.includes('User rejected') ||
                claimError.message.includes('User denied')
                  ? 'Transaction cancelled. Your rewards were not claimed.'
                  : claimError.message.includes('insufficient funds')
                    ? 'Insufficient ETH for gas fees. Please add ETH to your wallet and try again.'
                    : `Claim failed: ${claimError.message}`}
              </p>
            </div>
          )}

          {/* Balance Status */}
          {!isLoadingBalance && claimableWei !== undefined && (claimableWei as bigint) === 0n && (
            <div className="p-3 bg-gray-50 border border-gray-200 rounded">
              <p className="text-sm text-gray-700">
                No rewards to claim. Mint NFTs with your wallet as the prompt author to earn
                rewards.
              </p>
            </div>
          )}
        </div>

        {/* Security Notice */}
        <div className="text-sm text-gray-500 border-l-4 border-gray-300 pl-4">
          <p className="font-medium text-gray-700">Security Notice</p>
          <p className="mt-1">
            Your prompt is stored securely and only used for image generation. It is never exposed
            via API responses. Wallet signature verification ensures only you can update your
            prompt.
          </p>
        </div>
      </div>
    </div>
  )
}
