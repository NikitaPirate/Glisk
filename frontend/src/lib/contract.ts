import { isAddress } from 'viem'
import gliskNFTAbiFile from './glisk-nft-abi.json'

// Contract configuration from environment variables
export const CONTRACT_ADDRESS = import.meta.env.VITE_CONTRACT_ADDRESS as `0x${string}`
export const CHAIN_ID = parseInt(import.meta.env.VITE_CHAIN_ID || '84532', 10)

// Export ABI for contract interactions (unwrap .abi property)
export const GLISK_NFT_ABI = gliskNFTAbiFile.abi

/**
 * Validate configuration on module load
 * Ensures contract address and chain ID are valid before app starts
 * This prevents runtime errors from invalid configuration
 */
if (!CONTRACT_ADDRESS) {
  throw new Error(
    'VITE_CONTRACT_ADDRESS is not defined in environment variables. ' +
      'Please create a .env file with VITE_CONTRACT_ADDRESS=0x...'
  )
}

if (!isAddress(CONTRACT_ADDRESS)) {
  throw new Error(
    `Invalid contract address: ${CONTRACT_ADDRESS}\n` +
      'Address must be a valid checksummed Ethereum address (40 hex characters).\n' +
      'Please check VITE_CONTRACT_ADDRESS in your .env file.'
  )
}

if (!CHAIN_ID) {
  throw new Error('VITE_CHAIN_ID is not defined in environment variables')
}
