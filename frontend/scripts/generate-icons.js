#!/usr/bin/env node

/**
 * Generate favicon PNGs from SVG source
 * Requires: npm install -D sharp
 */

import sharp from 'sharp'
import { fileURLToPath } from 'url'
import { dirname, join } from 'path'
import fs from 'fs/promises'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const PUBLIC_DIR = join(__dirname, '..', 'public')
const SVG_SOURCE = join(PUBLIC_DIR, 'favicon.svg')

const ICON_SIZES = [
  { size: 32, name: 'favicon-32x32.png' },
  { size: 180, name: 'apple-touch-icon.png' },
  { size: 192, name: 'android-chrome-192x192.png' },
  { size: 512, name: 'android-chrome-512x512.png' },
]

async function generateIcons() {
  console.log('Generating favicon PNGs from SVG...\n')

  try {
    // Read SVG source
    const svgBuffer = await fs.readFile(SVG_SOURCE)

    // Generate each size
    for (const { size, name } of ICON_SIZES) {
      const outputPath = join(PUBLIC_DIR, name)

      await sharp(svgBuffer).resize(size, size).png().toFile(outputPath)

      console.log(`✓ Generated ${name} (${size}x${size})`)
    }

    console.log('\n✅ All icons generated successfully!')
  } catch (error) {
    console.error('❌ Error generating icons:', error.message)
    process.exit(1)
  }
}

generateIcons()
