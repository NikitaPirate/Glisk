import { createAvatar } from '@dicebear/core'
import { glass } from '@dicebear/collection'

interface WalletAvatarProps {
  address: string
  ensImage?: string | null
  size: number
}

export function WalletAvatar({ address, ensImage, size }: WalletAvatarProps) {
  // If ENS avatar exists, use it
  if (ensImage) {
    return (
      <img src={ensImage} width={size} height={size} alt="Avatar" style={{ display: 'block' }} />
    )
  }

  // Generate Glass avatar from wallet address
  const avatar = createAvatar(glass, {
    seed: address,
    size: size,
  })

  const svg = avatar.toString()

  return (
    <div
      dangerouslySetInnerHTML={{ __html: svg }}
      style={{ width: size, height: size, display: 'block' }}
    />
  )
}
