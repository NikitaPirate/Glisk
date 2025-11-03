# Migrate Frontend Foundation to Next.js

## Why

The current Vite + React setup is reaching limitations for our NFT platform's growing needs:

1. **SEO & Social Sharing**: NFT preview cards need proper meta tags for Twitter/Farcaster sharing
2. **Performance**: Large NFT collections need better code splitting and optimized loading
3. **Routing**: Next.js App Router provides better DX than React Router for complex nested layouts
4. **Farcaster Integration**: Better SSR support for miniapp context initialization

We're migrating just the **foundation** (build system, routing, basic structure) without attempting to migrate all features upfront. This allows us to validate the new stack quickly and handle edge cases iteratively.

## What Changes

**Foundation Migration (Scope of This Proposal)**:
- Replace Vite with Next.js 15 App Router
- Migrate core routing structure (`/`, `/[creatorAddress]`, `/profile`)
- Port wallet connection setup (RainbowKit + wagmi)
- Migrate Tailwind CSS configuration and shadcn/ui setup
- Port environment configuration and TypeScript setup
- Maintain existing API patterns (backend stays FastAPI, no Next.js API routes)

**Explicitly Out of Scope** (Handle Post-Migration):
- Individual page components (migrate/debug as needed)
- Complex state management patterns
- Edge case handling and debugging
- Performance optimization
- Testing strategy

**Non-Breaking for Backend**:
- Backend API remains unchanged
- No changes to smart contracts or blockchain integration
- Environment variables maintained (just prefixed differently)

## Impact

**Affected Specs**:
- `frontend-foundation` (new capability being created)

**Affected Code**:
- `frontend/` directory (complete restructure)
- `package.json` (dependency changes)
- Build and deployment scripts
- Environment variable naming (VITE_ → NEXT_PUBLIC_)

**Migration Strategy**:
1. Create new `frontend/` structure with Next.js
2. Migrate foundation components first (layout, providers, wallet connection)
3. Copy existing page code and debug/fix issues iteratively
4. Delete old Vite config once migration validated

**Risk Mitigation**:
- Keep old `frontend/` code until new stack is validated
- Backend API unchanged (reduces integration risk)
- Foundation-only scope allows quick validation
- Can rollback by reverting commits if critical issues found
