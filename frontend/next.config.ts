import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  // Enable standalone output for Docker deployment
  output: 'standalone',

  // Enable React strict mode for better error detection
  reactStrictMode: true,

  // TypeScript configuration
  typescript: {
    // Fail build on type errors
    ignoreBuildErrors: false,
  },

  // ESLint configuration
  eslint: {
    // Fail build on lint errors
    ignoreDuringBuilds: false,
  },

  // Webpack configuration for wallet polyfills
  webpack: config => {
    config.externals.push('pino-pretty', 'lokijs', 'encoding')
    config.resolve.fallback = {
      ...config.resolve.fallback,
      fs: false,
      net: false,
      tls: false,
    }
    return config
  },

  // Environment variables validation (optional, adds runtime checks)
  experimental: {
    // Enable server actions if needed in the future
    serverActions: {
      bodySizeLimit: '2mb',
    },
  },

  // Image optimization configuration
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**.mypinata.cloud',
      },
      {
        protocol: 'https',
        hostname: 'gateway.pinata.cloud',
      },
      {
        protocol: 'https',
        hostname: '**.ipfs.dweb.link',
      },
    ],
  },

  // Configure rewrites for API proxy (dev and production)
  async rewrites() {
    // In next.config.ts, NEXT_PUBLIC_ vars might not be available
    // Use direct process.env access or BACKEND_URL (without NEXT_PUBLIC_ prefix)
    const backendUrl =
      process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

    console.log('[Next.js Config] Backend URL:', backendUrl)

    return [
      {
        source: '/api/:path*',
        destination: `${backendUrl}/api/:path*`,
      },
      {
        source: '/webhooks/:path*',
        destination: `${backendUrl}/webhooks/:path*`,
      },
    ]
  },
}

export default nextConfig
