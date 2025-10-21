import { useState, useEffect } from 'react'
import { useAccount, useSignMessage } from 'wagmi'
import { Button } from '@/components/ui/button'

// API base URL (configurable via environment variable)
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

type LoadingState = 'idle' | 'fetching' | 'linking' | 'signing'

export function ProfileSettings() {
  const { address, isConnected } = useAccount()
  const [twitterHandle, setTwitterHandle] = useState<string | null>(null)
  const [loading, setLoading] = useState<LoadingState>('idle')
  const [errorMessage, setErrorMessage] = useState('')
  const [successMessage, setSuccessMessage] = useState('')

  // Signature hook
  const { signMessage, data: signature, error: signError } = useSignMessage()

  /**
   * Fetch author status on mount and when address changes
   */
  useEffect(() => {
    if (!address) {
      setTwitterHandle(null)
      return
    }

    const fetchAuthorStatus = async () => {
      try {
        setLoading('fetching')
        const response = await fetch(`${API_BASE_URL}/api/authors/${address}`)

        if (!response.ok) {
          throw new Error('Failed to fetch author status')
        }

        const data = await response.json()
        setTwitterHandle(data.twitter_handle || null)
      } catch (error) {
        console.error('Failed to fetch author status:', error)
        setErrorMessage('Failed to load profile information')
      } finally {
        setLoading('idle')
      }
    }

    fetchAuthorStatus()
  }, [address])

  /**
   * Check URL query params for OAuth callback
   */
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const xLinked = params.get('x_linked')
    const username = params.get('username')
    const error = params.get('error')

    if (xLinked === 'true' && username) {
      // Success case
      setTwitterHandle(username)
      setSuccessMessage(`X account @${username} linked successfully!`)

      // Clear query params
      window.history.replaceState({}, '', window.location.pathname)

      // Clear success message after 5 seconds
      setTimeout(() => {
        setSuccessMessage('')
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

      setErrorMessage(errorMsg)

      // Clear query params
      window.history.replaceState({}, '', window.location.pathname)
    }
  }, [])

  /**
   * Start OAuth flow when signature is received
   */
  useEffect(() => {
    if (!signature || !address || loading !== 'signing') {
      return
    }

    const startOAuth = async () => {
      try {
        setLoading('linking')
        setErrorMessage('')

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
        setLoading('idle')
        setErrorMessage(
          error instanceof Error ? error.message : 'Failed to link X account. Please try again.'
        )
      }
    }

    startOAuth()
  }, [signature, address, loading])

  /**
   * Handle signature errors (rejection, etc.)
   */
  useEffect(() => {
    if (!signError) {
      return
    }

    // Check for user rejection
    if (signError.message.includes('User rejected') || signError.message.includes('User denied')) {
      setLoading('idle')
      setErrorMessage('Signature cancelled. X account was not linked.')
    } else {
      setLoading('idle')
      setErrorMessage('Signature failed. Please try again.')
    }
  }, [signError])

  /**
   * Handle link X account button click
   */
  const linkXAccount = async () => {
    if (!address) return

    // Clear previous messages
    setErrorMessage('')
    setSuccessMessage('')

    try {
      setLoading('signing')
      const message = `Link X account for wallet: ${address}`
      await signMessage({ message })
    } catch (error) {
      // Error will be handled by useEffect watching signError
      console.error('Signature request failed:', error)
    }
  }

  // Redirect message if not connected
  if (!isConnected) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-2xl">
        <div className="p-4 bg-blue-50 border border-blue-200 rounded">
          <p className="text-blue-800">Please connect your wallet to access Profile Settings</p>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-2xl">
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold mb-2">Profile Settings</h1>
          <p className="text-gray-600">Manage your profile and connected accounts</p>
        </div>

        {/* X Account Linking Section */}
        <div className="space-y-4 border border-gray-200 rounded-lg p-6 bg-white">
          <h2 className="text-xl font-semibold">X (Twitter) Account</h2>
          <p className="text-sm text-gray-600">
            Link your X account to display your handle in NFT metadata. This helps collectors
            discover you on X.
          </p>

          {/* Loading State */}
          {loading === 'fetching' && (
            <div className="p-3 bg-gray-50 border border-gray-200 rounded">
              <p className="text-sm text-gray-700">Loading profile...</p>
            </div>
          )}

          {/* Twitter Handle Display (if linked) */}
          {loading !== 'fetching' && twitterHandle && (
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
          {loading !== 'fetching' && !twitterHandle && (
            <div className="space-y-3">
              <Button
                onClick={linkXAccount}
                disabled={loading === 'signing' || loading === 'linking'}
                className="w-full max-w-xs"
              >
                {loading === 'signing'
                  ? 'Waiting for signature...'
                  : loading === 'linking'
                    ? 'Redirecting to X...'
                    : 'Link X Account'}
              </Button>
              <p className="text-xs text-gray-500">
                You'll be redirected to X to authorize the connection. We only request permission to
                read your profile information.
              </p>
            </div>
          )}

          {/* Status Messages */}
          {loading === 'signing' && (
            <div className="p-4 bg-blue-50 border border-blue-200 rounded">
              <p className="text-blue-800">Please sign the message in your wallet to continue</p>
            </div>
          )}

          {loading === 'linking' && (
            <div className="p-4 bg-blue-50 border border-blue-200 rounded">
              <p className="text-blue-800">Redirecting to X for authorization...</p>
            </div>
          )}

          {errorMessage && (
            <div className="p-4 bg-red-50 border border-red-200 rounded">
              <p className="text-red-800">{errorMessage}</p>
            </div>
          )}

          {successMessage && (
            <div className="p-4 bg-green-50 border border-green-200 rounded">
              <p className="text-green-800">{successMessage}</p>
            </div>
          )}
        </div>

        {/* Security Notice */}
        <div className="text-sm text-gray-500 border-l-4 border-gray-300 pl-4">
          <p className="font-medium text-gray-700">Privacy Notice</p>
          <p className="mt-1">
            We only request permission to read your X profile information (username). We do not
            request permission to post on your behalf or access your private messages. Once linked,
            your X handle cannot be changed or removed in this version.
          </p>
        </div>
      </div>
    </div>
  )
}
