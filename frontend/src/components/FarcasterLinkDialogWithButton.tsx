import { useState } from 'react'
import { SignInButton } from '@farcaster/auth-kit'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import { Alert, AlertDescription } from '@/components/ui/alert'

interface FarcasterLinkDialogProps {
  open: boolean
  onClose: () => void
  walletAddress: string
  walletMessage: string
  walletSignature: string
  onSuccess: (username: string, fid: number) => void
  onError: (error: string) => void
}

export function FarcasterLinkDialogWithButton({
  open,
  onClose,
  walletAddress,
  walletMessage,
  walletSignature,
  onSuccess,
  onError,
}: FarcasterLinkDialogProps) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleFarcasterSuccess = async (res: any) => {
    // Extract message and signature from the correct location
    const message = res.signatureParams?.message || res.message
    const signature = res.signatureParams?.signature || res.signature

    if (!message || !signature || !res.fid || !res.username) {
      const errorMsg = 'Invalid Farcaster response'
      console.error('[FarcasterLinkDialogWithButton]', errorMsg, res)
      setError(errorMsg)
      onError(errorMsg)
      return
    }

    // User successfully signed in with Farcaster
    // Now send both signatures to backend
    setLoading(true)
    setError(null)

    try {
      const response = await fetch('/api/authors/farcaster/link', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          wallet_address: walletAddress,
          wallet_message: walletMessage,
          wallet_signature: walletSignature,
          farcaster_message: message, // Use extracted message
          farcaster_signature: signature, // Use extracted signature
          fid: res.fid,
          username: res.username,
        }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        console.error('[FarcasterLinkDialogWithButton] Backend error:', errorData)
        throw new Error(errorData.detail || 'Failed to link Farcaster account')
      }

      const data = await response.json()

      // Call parent's onSuccess callback
      onSuccess(data.username, data.fid)

      // Close dialog
      onClose()
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to link Farcaster account'
      console.error('[FarcasterLinkDialogWithButton] Link failed:', err)
      setError(errorMessage)
      onError(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  const handleClose = () => {
    // Clean up state when closing
    setError(null)
    setLoading(false)
    onClose()
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Link Farcaster Account</DialogTitle>
          <DialogDescription>
            Sign in with your Farcaster account to link it to your wallet.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-4 py-4">
          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {loading ? (
            <div className="flex items-center justify-center py-8">
              <div className="text-sm text-muted-foreground">Linking Farcaster account...</div>
            </div>
          ) : (
            <div className="flex justify-center">
              <SignInButton
                onSuccess={handleFarcasterSuccess}
                onError={(error: any) => {
                  const errorMessage =
                    error?.message || error?.toString() || 'Farcaster sign-in failed'
                  setError(errorMessage)
                  onError(errorMessage)
                }}
              />
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
