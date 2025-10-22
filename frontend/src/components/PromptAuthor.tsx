import { useState, useEffect } from 'react'
import { useAccount, useSignMessage } from 'wagmi'
import { useQuery } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { NFTGrid } from '@/components/NFTGrid'

// API base URL (configurable via environment variable)
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

type PromptStatus = 'loading' | 'has_prompt' | 'no_prompt' | 'error'
type SaveStatus = 'idle' | 'signing' | 'saving' | 'success' | 'error' | 'cancelled'
type LoadingState = 'idle' | 'fetching' | 'linking' | 'signing'

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
  const response = await fetch(
    `${API_BASE_URL}/api/authors/${walletAddress}/tokens?offset=${offset}&limit=20`
  )

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

  // X linking state
  const [twitterHandle, setTwitterHandle] = useState<string | null>(null)
  const [xLoading, setXLoading] = useState<LoadingState>('idle')
  const [xErrorMessage, setXErrorMessage] = useState('')
  const [xSuccessMessage, setXSuccessMessage] = useState('')

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

  // Signature hook (shared by both prompt and X linking)
  const { signMessage, data: signature, error: signError } = useSignMessage()

  /**
   * Fetch author status on mount and when address changes
   */
  useEffect(() => {
    if (!address) {
      setPromptStatus('no_prompt')
      setTwitterHandle(null)
      return
    }

    const fetchAuthorStatus = async () => {
      try {
        setPromptStatus('loading')
        setXLoading('fetching')
        const response = await fetch(`${API_BASE_URL}/api/authors/${address}`)

        if (!response.ok) {
          throw new Error('Failed to fetch author status')
        }

        const data = await response.json()
        setPromptStatus(data.has_prompt ? 'has_prompt' : 'no_prompt')
        setTwitterHandle(data.twitter_handle || null)
      } catch (error) {
        console.error('Failed to fetch author status:', error)
        setPromptStatus('error')
        setXErrorMessage('Failed to load profile information')
      } finally {
        setXLoading('idle')
      }
    }

    fetchAuthorStatus()
  }, [address])

  /**
   * Check URL query params for X OAuth callback
   */
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const xLinked = params.get('x_linked')
    const username = params.get('username')
    const error = params.get('error')

    if (xLinked === 'true' && username) {
      // Success case
      setTwitterHandle(username)
      setXSuccessMessage(`X account @${username} linked successfully!`)

      // Clear query params
      window.history.replaceState(
        {},
        '',
        window.location.pathname +
          window.location.search.replace(/[?&]x_linked=true(&username=[^&]+)?/, '')
      )

      // Clear success message after 5 seconds
      setTimeout(() => {
        setXSuccessMessage('')
      }, 5000)
    } else if (xLinked === 'false' && error) {
      // Error case
      let errorMsg = 'Failed to link X account'

      switch (error) {
        case 'user_denied':
          errorMsg = 'Authorization cancelled. You can try again by clicking "Link X Account".'
          break
        case 'state_mismatch':
          errorMsg = 'Security verification failed. Please try again.'
          break
        case 'token_exchange_failed':
          errorMsg = 'Failed to communicate with X. Please try again.'
          break
        case 'expired':
          errorMsg = 'Authorization expired. Please try again.'
          break
        default:
          errorMsg = `Failed to link X account: ${error}`
      }

      setXErrorMessage(errorMsg)

      // Clear query params
      window.history.replaceState({}, '', window.location.pathname)
    }
  }, [])

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
   * Start X OAuth flow when signature is received (for X linking)
   */
  useEffect(() => {
    if (!signature || !address || xLoading !== 'signing') {
      return
    }

    const startOAuth = async () => {
      try {
        setXLoading('linking')
        setXErrorMessage('')

        const message = `Link X account for wallet: ${address}`

        const response = await fetch(`${API_BASE_URL}/api/authors/x/auth/start`, {
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
          if (response.status === 409) {
            throw new Error('X account already linked. Cannot re-link in this version.')
          }
          throw new Error(data.detail || 'Failed to start X OAuth flow')
        }

        // Redirect to X authorization page
        window.location.href = data.authorization_url
      } catch (error) {
        setXLoading('idle')
        setXErrorMessage(
          error instanceof Error ? error.message : 'Failed to link X account. Please try again.'
        )
      }
    }

    startOAuth()
  }, [signature, address, xLoading])

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
      if (xLoading === 'signing') {
        setXLoading('idle')
        setXErrorMessage('Signature cancelled. X account was not linked.')
      }
    } else {
      if (saveStatus === 'signing') {
        setSaveStatus('error')
        setPromptErrorMessage('Signature failed. Please try again.')
      }
      if (xLoading === 'signing') {
        setXLoading('idle')
        setXErrorMessage('Signature failed. Please try again.')
      }
    }
  }, [signError, saveStatus, xLoading])

  /**
   * Wallet change detection - clear state when wallet changes
   */
  useEffect(() => {
    if (address) {
      // Clear prompt error messages
      setPromptErrorMessage('')
      setPromptSuccessMessage('')
      setSaveStatus('idle')

      // Clear X error messages
      setXErrorMessage('')
      setXSuccessMessage('')

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
      await signMessage({ message })
    } catch (error) {
      // Error will be handled by useEffect watching signError
      console.error('Signature request failed:', error)
    }
  }

  /**
   * Handle link X account button click
   */
  const linkXAccount = async () => {
    if (!address) return

    // Clear previous messages
    setXErrorMessage('')
    setXSuccessMessage('')

    try {
      setXLoading('signing')
      const message = `Link X account for wallet: ${address}`
      await signMessage({ message })
    } catch (error) {
      // Error will be handled by useEffect watching signError
      console.error('Signature request failed:', error)
    }
  }

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

  return (
    <div className="space-y-6">
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
          onClick={handleSavePrompt}
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

        {/* Prompt Status Messages */}
        {saveStatus === 'signing' && (
          <div className="p-4 bg-blue-50 border border-blue-200 rounded">
            <p className="text-blue-800">Please sign the message in your wallet to continue</p>
          </div>
        )}

        {saveStatus === 'cancelled' && (
          <div className="p-4 bg-yellow-50 border border-yellow-200 rounded">
            <p className="text-yellow-800">{promptErrorMessage}</p>
          </div>
        )}

        {saveStatus === 'error' && (
          <div className="p-4 bg-red-50 border border-red-200 rounded">
            <p className="text-red-800">{promptErrorMessage}</p>
          </div>
        )}

        {saveStatus === 'success' && (
          <div className="p-4 bg-green-50 border border-green-200 rounded">
            <p className="text-green-800">{promptSuccessMessage}</p>
          </div>
        )}
      </div>

      {/* X Account Linking Section */}
      <div className="space-y-4 border border-gray-200 rounded-lg p-6 bg-white">
        <h2 className="text-xl font-semibold">X (Twitter) Account</h2>
        <p className="text-sm text-gray-600">
          Link your X account to display your handle in NFT metadata. This helps collectors discover
          you on X.
        </p>

        {/* Loading State */}
        {xLoading === 'fetching' && (
          <div className="p-3 bg-gray-50 border border-gray-200 rounded">
            <p className="text-sm text-gray-700">Loading profile...</p>
          </div>
        )}

        {/* Twitter Handle Display (if linked) */}
        {xLoading !== 'fetching' && twitterHandle && (
          <div className="space-y-3">
            <div className="p-4 bg-green-50 border border-green-200 rounded">
              <p className="text-sm font-medium text-green-800">✓ Linked: @{twitterHandle}</p>
            </div>
            <p className="text-xs text-gray-500">
              Your X handle is included in NFT metadata for all tokens minted with your wallet.
            </p>
          </div>
        )}

        {/* Link Button (if not linked) */}
        {xLoading !== 'fetching' && !twitterHandle && (
          <div className="space-y-3">
            <Button
              onClick={linkXAccount}
              disabled={xLoading === 'signing' || xLoading === 'linking'}
              className="w-full max-w-xs"
            >
              {xLoading === 'signing'
                ? 'Waiting for signature...'
                : xLoading === 'linking'
                  ? 'Redirecting to X...'
                  : 'Link X Account'}
            </Button>
            <p className="text-xs text-gray-500">
              You'll be redirected to X to authorize the connection. We only request permission to
              read your profile information.
            </p>
          </div>
        )}

        {/* X Status Messages */}
        {xLoading === 'signing' && (
          <div className="p-4 bg-blue-50 border border-blue-200 rounded">
            <p className="text-blue-800">Please sign the message in your wallet to continue</p>
          </div>
        )}

        {xLoading === 'linking' && (
          <div className="p-4 bg-blue-50 border border-blue-200 rounded">
            <p className="text-blue-800">Redirecting to X for authorization...</p>
          </div>
        )}

        {xErrorMessage && (
          <div className="p-4 bg-red-50 border border-red-200 rounded">
            <p className="text-red-800">{xErrorMessage}</p>
          </div>
        )}

        {xSuccessMessage && (
          <div className="p-4 bg-green-50 border border-green-200 rounded">
            <p className="text-green-800">{xSuccessMessage}</p>
          </div>
        )}
      </div>

      {/* T043: Authored NFTs Section */}
      <div className="space-y-4 border border-gray-200 rounded-lg p-6 bg-white">
        <h2 className="text-xl font-semibold">Your Authored NFTs</h2>
        <p className="text-sm text-gray-600">
          NFTs where you provided the AI generation prompt. These are tokens minted with your wallet
          address as the prompt author.
        </p>

        {/* T036: Loading state */}
        {authoredNFTsLoading && (
          <div className="p-4 bg-gray-50 border border-gray-200 rounded">
            <p className="text-gray-700">Loading...</p>
          </div>
        )}

        {/* T037: Error state */}
        {!authoredNFTsLoading && authoredNFTsError && (
          <div className="p-4 bg-red-50 border border-red-200 rounded">
            <p className="text-red-800">Failed to load NFTs. Please try again.</p>
          </div>
        )}

        {/* T038: Empty state */}
        {!authoredNFTsLoading &&
          !authoredNFTsError &&
          authoredNFTsData &&
          authoredNFTsData.total === 0 && (
            <div className="p-4 bg-gray-50 border border-gray-200 rounded">
              <p className="text-gray-700">No authored NFTs yet.</p>
            </div>
          )}

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
                    variant="outline"
                  >
                    Previous
                  </Button>
                  <p className="text-sm text-gray-600">
                    Page {authoredPage} of {totalPages}
                  </p>
                  <Button
                    onClick={() => setAuthoredPage(p => p + 1)}
                    disabled={authoredPage === totalPages || authoredNFTsLoading}
                    variant="outline"
                  >
                    Next
                  </Button>
                </div>
              )}
            </>
          )}
      </div>

      {/* Security Notice */}
      <div className="text-sm text-gray-500 border-l-4 border-gray-300 pl-4">
        <p className="font-medium text-gray-700">Security & Privacy Notice</p>
        <p className="mt-1">
          Your prompt is stored securely and only used for image generation. It is never exposed via
          API responses. For X linking, we only request permission to read your profile information
          (username). We do not request permission to post on your behalf or access your private
          messages.
        </p>
      </div>
    </div>
  )
}
