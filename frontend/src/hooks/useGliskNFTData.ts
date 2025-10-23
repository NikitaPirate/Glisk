import { useEffect, useState } from 'react'
import { useReadContract } from 'wagmi'
import type { Hex } from 'viem'
import { GLISK_NFT_ABI } from '@/lib/contract'

// Extended NFT data with author information
export type NFTData = {
  name?: string
  description?: string
  imageUrl?: string
  authorXHandle?: string // From metadata attributes
  authorAddress?: Hex // From tokenPromptAuthor contract mapping
}

export type NFTError = {
  code: string
  error: string
  message: string
}

const PINATA_GATEWAY = import.meta.env.VITE_PINATA_GATEWAY || 'gateway.pinata.cloud'
const PINATA_GATEWAY_TOKEN = import.meta.env.VITE_PINATA_GATEWAY_TOKEN

/**
 * Hook for fetching Glisk NFT data including author information
 * - Reads tokenURI from contract and fetches metadata from IPFS
 * - Extracts author X handle from metadata attributes
 * - Reads prompt author address from contract
 */
export function useGliskNFTData(contractAddress: Hex, tokenId?: string): NFTData | NFTError {
  const [metadata, setMetadata] = useState<NFTData | NFTError | null>(null)

  // Read tokenURI from contract
  const {
    data: tokenUri,
    isError: tokenUriError,
    isLoading: tokenUriLoading,
  } = useReadContract({
    address: contractAddress,
    abi: GLISK_NFT_ABI,
    functionName: 'tokenURI',
    args: tokenId ? [BigInt(tokenId)] : undefined,
    query: { enabled: !!tokenId },
  })

  // Read prompt author address from contract
  const { data: authorAddress } = useReadContract({
    address: contractAddress,
    abi: GLISK_NFT_ABI,
    functionName: 'tokenPromptAuthor',
    args: tokenId ? [BigInt(tokenId)] : undefined,
    query: { enabled: !!tokenId },
  })

  useEffect(() => {
    if (tokenUriLoading) return

    if (tokenUriError || !tokenUri) {
      setMetadata({
        code: 'TmBUIHN01',
        error: 'Failed to read tokenURI',
        message: 'Cannot fetch token metadata from blockchain',
      })
      return
    }

    // Fetch metadata from IPFS
    async function fetchMetadata() {
      try {
        const metadataUrl = ipfsToGateway(tokenUri as string)
        const response = await fetch(metadataUrl)

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`)
        }

        const json = await response.json()

        // Extract author X handle from attributes
        const authorXHandle = json.attributes?.find(
          (attr: { trait_type: string; value: string }) => attr.trait_type === 'Author X Handle'
        )?.value

        setMetadata({
          name: json.name || `Glisk NFT #${tokenId}`,
          description: json.description,
          imageUrl: json.image ? ipfsToGateway(json.image) : undefined,
          authorXHandle,
          authorAddress: authorAddress as Hex | undefined,
        })
      } catch (err) {
        console.error('IPFS metadata fetch error:', err)
        setMetadata({
          code: 'TmBUIHN03',
          error: 'Failed to fetch metadata from IPFS',
          message: err instanceof Error ? err.message : 'Unknown error',
        })
      }
    }

    fetchMetadata()
  }, [tokenUri, tokenUriLoading, tokenUriError, tokenId, authorAddress])

  return (
    metadata || {
      code: 'TmBUIHN00',
      error: 'Loading',
      message: 'Loading NFT metadata...',
    }
  )
}

/**
 * Convert IPFS URI to Pinata gateway URL with optional gateway token
 * Supports: ipfs://CID, ipfs://ipfs/CID, https://...
 */
function ipfsToGateway(uri: string): string {
  let gatewayUrl: string

  if (uri.startsWith('http://') || uri.startsWith('https://')) {
    // Already HTTP - check if it's an IPFS gateway URL
    const match = uri.match(/\/ipfs\/([a-zA-Z0-9]+)/)
    if (match) {
      gatewayUrl = `https://${PINATA_GATEWAY}/ipfs/${match[1]}`
    } else {
      return uri
    }
  } else if (uri.startsWith('ipfs://')) {
    const cid = uri.replace('ipfs://', '').replace('ipfs/', '')
    gatewayUrl = `https://${PINATA_GATEWAY}/ipfs/${cid}`
  } else {
    // Assume bare CID
    gatewayUrl = `https://${PINATA_GATEWAY}/ipfs/${uri}`
  }

  // Add gateway token if configured
  if (PINATA_GATEWAY_TOKEN) {
    gatewayUrl += `?pinataGatewayToken=${PINATA_GATEWAY_TOKEN}`
  }

  return gatewayUrl
}
