'use client'

import { useState, useEffect } from 'react'
import { RiInfoI } from 'react-icons/ri'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'

export function HelpDialog() {
  const [open, setOpen] = useState(false)

  useEffect(() => {
    const handleOpenDialog = () => setOpen(true)
    window.addEventListener('openHelpDialog', handleOpenDialog)
    return () => window.removeEventListener('openHelpDialog', handleOpenDialog)
  }, [])

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="lg">
          <RiInfoI className="h-5 w-5" />
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle className="text-xl font-bold">ABOUT GLISK Season 0</DialogTitle>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Collection Description */}
          <div>
            <p className="text-sm text-muted-foreground">
              An experimental NFT collection where prompt authors set AI generation parameters, and
              collectors mint unique variations.
            </p>
          </div>

          {/* Page Descriptions */}
          <div className="space-y-4">
            <div>
              <h3 className="font-semibold text-sm mb-1">Profile Page</h3>
              <p className="text-sm text-muted-foreground">
                Create your own AI image prompts and share them with the world.
              </p>
            </div>

            <div>
              <h3 className="font-semibold text-sm mb-1">Author Page</h3>
              <p className="text-sm text-muted-foreground">
                Mint NFTs using any creator's AI prompt.
              </p>
            </div>
          </div>

          {/* Social Links */}
          <div className="flex items-center justify-center gap-6 pt-2 border-t">
            <a
              href="https://x.com/NikitaPirate"
              target="_blank"
              rel="noopener noreferrer"
              className="text-muted-foreground hover:text-foreground transition-colors"
              aria-label="Nikita on X"
            >
              <svg
                className="h-5 w-5"
                viewBox="0 0 24 24"
                fill="currentColor"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
              </svg>
            </a>

            <a
              href="https://x.com/getglisk"
              target="_blank"
              rel="noopener noreferrer"
              className="text-muted-foreground hover:text-foreground transition-colors"
              aria-label="Glisk on X"
            >
              <svg
                className="h-5 w-5"
                viewBox="0 0 24 24"
                fill="currentColor"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
              </svg>
            </a>

            <a
              href="https://farcaster.xyz/nikita-k"
              target="_blank"
              rel="noopener noreferrer"
              className="text-muted-foreground hover:text-foreground transition-colors"
              aria-label="Nikita on Farcaster"
            >
              <img
                src="/images/farcaster.svg"
                alt="Farcaster"
                className="h-5 w-5 opacity-60 hover:opacity-100 transition-opacity"
                style={{ filter: 'brightness(0) saturate(100%) invert(var(--invert-amount, 0.5))' }}
              />
            </a>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
