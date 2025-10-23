import { useState, useEffect, useRef } from 'react'

interface TokenData {
  token_id: number
  status: string
  image_url: string | null
  image_cid: string | null
  metadata_cid: string | null
  reveal_tx_hash: string | null
}

interface UseTokenPollingResult {
  tokens: Map<number, TokenData>
  isPolling: boolean
  allRevealed: boolean
  error: string | null
}

const POLLING_INTERVAL = 2000 // 2 seconds
const POLLING_TIMEOUT = 5 * 60 * 1000 // 5 minutes

/**
 * useTokenPolling - Poll API for token status updates
 *
 * Fetches token data from GET /api/authors/{wallet}/tokens every 2 seconds
 * until all tokens are revealed or timeout (5 minutes).
 *
 * @param tokenIds - Array of token IDs to track (from BatchMinted event)
 * @param walletAddress - Author wallet address (checksummed)
 * @param enabled - Whether to start polling (default: false)
 * @returns Object with tokens Map, polling status, and allRevealed flag
 */
export function useTokenPolling(
  tokenIds: number[],
  walletAddress: string | undefined,
  enabled: boolean = false
): UseTokenPollingResult {
  const [tokens, setTokens] = useState<Map<number, TokenData>>(new Map())
  const [isPolling, setIsPolling] = useState(false)
  const [allRevealed, setAllRevealed] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const startTimeRef = useRef<number>(Date.now())
  const intervalRef = useRef<NodeJS.Timeout | null>(null)

  useEffect(() => {
    // Reset state when tokenIds or wallet changes
    setTokens(new Map())
    setAllRevealed(false)
    setError(null)
    startTimeRef.current = Date.now()
  }, [tokenIds, walletAddress])

  useEffect(() => {
    if (!enabled || !walletAddress || tokenIds.length === 0) {
      setIsPolling(false)
      return
    }

    const fetchTokens = async () => {
      try {
        // Check timeout (5 minutes)
        const elapsed = Date.now() - startTimeRef.current
        if (elapsed > POLLING_TIMEOUT) {
          setIsPolling(false)
          setError('Timeout: Tokens took too long to reveal. Please check your profile later.')
          if (intervalRef.current) {
            clearInterval(intervalRef.current)
            intervalRef.current = null
          }
          return
        }

        // Fetch tokens from API
        const response = await fetch(`/api/authors/${walletAddress}/tokens?limit=100`)

        if (!response.ok) {
          throw new Error(`API error: ${response.status}`)
        }

        const data = await response.json()
        const fetchedTokens = data.tokens as TokenData[]

        // Filter only tokens we're tracking
        const tokenMap = new Map<number, TokenData>()
        const tokenIdSet = new Set(tokenIds)

        for (const token of fetchedTokens) {
          if (tokenIdSet.has(token.token_id)) {
            tokenMap.set(token.token_id, token)
          }
        }

        setTokens(tokenMap)

        // Check if all tokens are revealed
        const allTokensRevealed =
          tokenMap.size === tokenIds.length &&
          Array.from(tokenMap.values()).every(t => t.status === 'revealed')

        if (allTokensRevealed) {
          setAllRevealed(true)
          setIsPolling(false)
          if (intervalRef.current) {
            clearInterval(intervalRef.current)
            intervalRef.current = null
          }
        }
      } catch (err) {
        console.error('Token polling error:', err)
        setError(err instanceof Error ? err.message : 'Failed to fetch tokens')
      }
    }

    // Start polling
    setIsPolling(true)
    fetchTokens() // Immediate first fetch

    intervalRef.current = setInterval(fetchTokens, POLLING_INTERVAL)

    // Cleanup
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }
  }, [enabled, walletAddress, tokenIds])

  return { tokens, isPolling, allRevealed, error }
}
