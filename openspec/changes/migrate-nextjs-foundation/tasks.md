# Implementation Tasks

## 1. Setup & Configuration
- [x] 1.1 Install Next.js 15 and core dependencies
- [x] 1.2 Create `next.config.js` with TypeScript, Tailwind, and wallet polyfills
- [x] 1.3 Migrate `tsconfig.json` for Next.js paths and server/client components
- [x] 1.4 Port Tailwind CSS config (tailwind.config.js, globals.css)
- [x] 1.5 Update environment variables (VITE_ → NEXT_PUBLIC_)
- [x] 1.6 Configure ESLint and Prettier for Next.js

## 2. App Structure & Routing
- [x] 2.1 Create `app/` directory with root layout
- [x] 2.2 Setup providers layout (RainbowKit, wagmi, React Query, theme)
- [x] 2.3 Create root page (`app/page.tsx`)
- [x] 2.4 Create dynamic creator page (`app/[creatorAddress]/page.tsx`)
- [x] 2.5 Create profile page (`app/profile/page.tsx`)
- [x] 2.6 Setup metadata configuration for SEO

## 3. Web3 & Wallet Integration
- [x] 3.1 Port RainbowKit configuration for Next.js client component
- [x] 3.2 Migrate wagmi config with proper chains and transports
- [x] 3.3 Setup wallet providers in layout with 'use client' directives
- [x] 3.4 Port contract ABIs and addresses
- [x] 3.5 Verify wallet connection flow works

## 4. Component Migration (Foundation Only)
- [x] 4.1 Port layout components (Header, Footer, Navigation)
- [x] 4.2 Migrate shadcn/ui component library setup
- [x] 4.3 Port theme provider and dark mode toggle
- [x] 4.4 Migrate common UI components (Button, Dialog, Toaster)

## 5. Build & Deployment
- [x] 5.1 Verify `npm run dev` works locally
- [x] 5.2 Test production build (`npm run build`)
- [x] 5.3 Update deployment scripts if needed
- [x] 5.4 Document environment variable migration

## 6. Validation
- [x] 6.1 Test wallet connection flow
- [x] 6.2 Verify routing to all foundation pages
- [x] 6.3 Test API calls to backend (unchanged)
- [x] 6.4 Check responsive design and dark mode
- [x] 6.5 Manual browser testing (Chrome, Safari, mobile)

## 7. Docker Deployment Configuration (Post-Migration Fix)
- [x] 7.1 Update Dockerfile from Vite to Next.js standalone mode
- [x] 7.2 Update docker-compose.yml with NEXT_PUBLIC_ variables
- [x] 7.3 Update Traefik/NPM port configuration (80 → 3000)
- [x] 7.4 Add output: 'standalone' to next.config.ts
- [x] 7.5 Update .env.example documentation
- [x] 7.6 Create pre-deployment security checklist
- [x] 7.7 Verify no hardcoded secrets in code
