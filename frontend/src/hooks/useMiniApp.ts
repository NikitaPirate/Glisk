'use client'

import { useState, useEffect } from 'react'
import { sdk } from '@farcaster/miniapp-sdk'

/**
 * Detect if the app is running in a Mini App context
 * (Base App, Warpcast, or any Farcaster Mini App)
 *
 * @returns isMiniApp - true if running in Mini App, false otherwise, null during detection
 */
export function useMiniApp() {
  const [isMiniApp, setIsMiniApp] = useState<boolean | null>(null)

  useEffect(() => {
    sdk.isInMiniApp().then(result => {
      setIsMiniApp(result)
    })
  }, [])

  return { isMiniApp }
}
