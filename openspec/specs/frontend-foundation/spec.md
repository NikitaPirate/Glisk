# frontend-foundation Specification

## Purpose
TBD - created by archiving change migrate-nextjs-foundation. Update Purpose after archive.
## Requirements
### Requirement: Next.js Application Structure

The frontend application SHALL be built with Next.js 15 App Router using modern React patterns.

#### Scenario: App directory structure exists
- **WHEN** developer opens the frontend codebase
- **THEN** the `app/` directory contains the following structure:
  - `layout.tsx` (root layout with providers)
  - `page.tsx` (home page)
  - `[creatorAddress]/page.tsx` (dynamic creator pages)
  - `profile/page.tsx` (user profile page)

#### Scenario: TypeScript configuration supports Next.js
- **WHEN** developer runs `npm run dev` or `npm run build`
- **THEN** TypeScript compiles successfully with Next.js path aliases and server/client component types

### Requirement: Web3 Provider Configuration

The application SHALL integrate RainbowKit and wagmi for Ethereum wallet connectivity.

#### Scenario: Wallet providers configured correctly
- **WHEN** application loads in the browser
- **THEN** RainbowKit and wagmi providers wrap the app with proper configuration for Base network
- **AND** wallet connection UI is available to users

#### Scenario: Client-side Web3 components
- **WHEN** components use wallet hooks (useAccount, useWriteContract, etc.)
- **THEN** these components have 'use client' directive to run in browser
- **AND** wallet state persists across page navigation

#### Scenario: Contract ABIs and addresses available
- **WHEN** application needs to interact with smart contracts
- **THEN** contract ABIs and addresses are accessible from imported modules
- **AND** network configuration determines correct contract address (Sepolia vs Mainnet)

### Requirement: Routing and Navigation

The application SHALL implement file-based routing using Next.js App Router conventions.

#### Scenario: Core routes are accessible
- **WHEN** user navigates to `/`
- **THEN** home page displays NFT feed or landing content

#### Scenario: Dynamic creator pages
- **WHEN** user navigates to `/{creatorAddress}` with valid Ethereum address
- **THEN** creator profile page displays with their NFTs and stats

#### Scenario: Authenticated profile page
- **WHEN** authenticated user navigates to `/profile`
- **THEN** their own profile management page displays

#### Scenario: Navigation between pages
- **WHEN** user clicks navigation links or uses browser back/forward
- **THEN** page transitions occur without full reload (SPA behavior)
- **AND** wallet connection state persists

### Requirement: Styling and Theming

The application SHALL use Tailwind CSS for styling with shadcn/ui component library and theme support.

#### Scenario: Tailwind CSS configured
- **WHEN** developer uses Tailwind utility classes in components
- **THEN** styles are applied correctly in development and production builds

#### Scenario: Dark mode support
- **WHEN** user toggles theme preference
- **THEN** application switches between light and dark mode
- **AND** theme preference persists across sessions

#### Scenario: shadcn/ui components available
- **WHEN** developer imports shadcn/ui components (Button, Dialog, etc.)
- **THEN** components render with consistent styling and accessibility features

### Requirement: Environment Configuration

The application SHALL load configuration from environment variables following Next.js conventions.

#### Scenario: Public environment variables accessible
- **WHEN** application needs runtime configuration (network, API keys, backend URL)
- **THEN** variables prefixed with `NEXT_PUBLIC_` are accessible in client code
- **AND** variables are loaded from `.env.local` in development

#### Scenario: Required variables validated
- **WHEN** application starts without required environment variables
- **THEN** clear error message indicates which variables are missing

#### Scenario: Network configuration
- **WHEN** `NEXT_PUBLIC_NETWORK` is set to `BASE_MAINNET` or `BASE_SEPOLIA`
- **THEN** application uses correct RPC endpoints and contract addresses for that network

### Requirement: Build and Development

The application SHALL provide reliable development and production build processes.

#### Scenario: Development server runs locally
- **WHEN** developer runs `npm run dev`
- **THEN** Next.js development server starts on configured port
- **AND** hot module replacement works for code changes
- **AND** wallet connection and Web3 features function correctly

#### Scenario: Production build succeeds
- **WHEN** developer runs `npm run build`
- **THEN** build completes without errors
- **AND** optimized static assets and server bundles are generated
- **AND** wallet polyfills are included for browser compatibility

#### Scenario: Type checking passes
- **WHEN** developer runs TypeScript compiler or Next.js build
- **THEN** no type errors are reported in foundation code

### Requirement: Backend API Integration

The application SHALL communicate with FastAPI backend without requiring Next.js API routes.

#### Scenario: API calls to backend
- **WHEN** frontend needs to fetch data (NFT metadata, user profiles, etc.)
- **THEN** requests are made directly to FastAPI backend URL
- **AND** CORS is configured properly on backend for frontend origin

#### Scenario: Backend URL configuration
- **WHEN** `NEXT_PUBLIC_BACKEND_URL` environment variable is set
- **THEN** all API calls use this base URL
- **AND** URL works for both development (localhost) and production (deployed backend)

### Requirement: Layout and Providers

The application SHALL organize shared layout elements and React context providers efficiently.

#### Scenario: Root layout with providers
- **WHEN** any page renders
- **THEN** root layout wraps content with:
  - RainbowKit provider (wallet UI)
  - wagmi provider (Web3 state)
  - React Query provider (data fetching)
  - Theme provider (dark mode)
- **AND** providers are marked with 'use client' directive

#### Scenario: Shared header and navigation
- **WHEN** any page renders
- **THEN** common header component displays with navigation links
- **AND** wallet connection button is visible and functional
- **AND** theme toggle is available

#### Scenario: Responsive layout
- **WHEN** application is viewed on mobile, tablet, or desktop
- **THEN** layout adapts appropriately with responsive design patterns
- **AND** navigation collapses to mobile menu on small screens

### Requirement: Migration from Vite

The migration SHALL maintain feature parity with existing Vite-based frontend for foundation functionality.

#### Scenario: Environment variable migration
- **WHEN** environment variables are migrated from VITE_ to NEXT_PUBLIC_ prefix
- **THEN** all functionality that depended on environment variables works identically

#### Scenario: Wallet connection behavior preserved
- **WHEN** user connects wallet, switches accounts, or disconnects
- **THEN** behavior is identical to previous Vite implementation

#### Scenario: Routing URLs unchanged
- **WHEN** user navigates to existing URLs (/, /{address}, /profile)
- **THEN** same content displays as in previous implementation
- **AND** browser history and deep linking work correctly
