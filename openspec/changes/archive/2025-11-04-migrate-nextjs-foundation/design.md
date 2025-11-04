# Technical Design: Next.js Foundation Migration

## Context

Current frontend uses Vite + React Router with client-side rendering. This works but lacks:
- Proper SEO for NFT sharing on social platforms
- Optimal performance patterns (SSR, streaming, code splitting)
- Modern routing DX (nested layouts, server components)

Next.js 15 App Router addresses these needs while maintaining our simplicity-first philosophy.

**Key Constraint**: We're only migrating the foundation, not attempting a complete all-at-once migration. Edge cases and complex features will be handled iteratively after the foundation is validated.

## Goals / Non-Goals

**Goals:**
- Replace Vite build system with Next.js 15
- Migrate core routing structure (/, /[creatorAddress], /profile)
- Maintain wallet connection and Web3 functionality
- Keep backend API unchanged (no Next.js API routes)
- Enable future SEO improvements and server components

**Non-Goals:**
- Migrating every single component perfectly upfront
- Server-side rendering complex wallet interactions (keep client-side)
- Next.js API routes (backend stays FastAPI)
- Automated testing (manual testing for MVP)
- Performance optimization (future work)

## Decisions

### 1. Next.js 15 App Router (Not Pages Router)

**Decision**: Use App Router (`app/` directory) instead of legacy Pages Router.

**Rationale**:
- App Router is the future of Next.js and recommended default
- Server components enable better performance patterns
- Better nested layouts support (providers, headers, footers)
- Simpler data fetching patterns for future improvements

**Trade-offs**:
- Requires explicit 'use client' directives for wallet components
- Slightly steeper learning curve vs Vite
- Accepted: More declarative, better DX long-term

### 2. Client-Side Web3 Components Only

**Decision**: All wallet/Web3 interactions remain client-side with 'use client' directive.

**Rationale**:
- RainbowKit and wagmi require browser APIs (window.ethereum)
- Server-side rendering wallet state adds complexity without clear benefit
- Current client-side approach works well for our use case

**Implementation**:
- Create client provider components (`providers.tsx`)
- Wrap app in providers at layout level
- Page components can be server or client as needed

### 3. Environment Variable Prefix Migration

**Decision**: Migrate from `VITE_` to `NEXT_PUBLIC_` prefix.

**Mapping**:
```
VITE_NETWORK → NEXT_PUBLIC_NETWORK
VITE_BACKEND_URL → NEXT_PUBLIC_BACKEND_URL
VITE_ALCHEMY_API_KEY → NEXT_PUBLIC_ALCHEMY_API_KEY
VITE_WALLET_CONNECT_PROJECT_ID → NEXT_PUBLIC_WALLET_CONNECT_PROJECT_ID
```

**Rationale**:
- Next.js convention for client-exposed variables
- Maintains same security model (public variables only)
- Clear migration path with find-replace

### 4. Incremental Component Migration Strategy

**Decision**: Don't attempt to migrate/fix all components in this proposal.

**Approach**:
1. Migrate foundation (layout, routing, providers)
2. Copy existing page components as-is
3. Debug and fix issues iteratively post-migration
4. Refactor for server components later (optional)

**Rationale**:
- Large codebase makes comprehensive upfront migration risky
- Better to validate foundation quickly and iterate
- Aligns with seasonal MVP philosophy
- Real-world testing reveals edge cases better than planning

### 5. No Next.js API Routes

**Decision**: Backend stays FastAPI, no Next.js API routes.

**Rationale**:
- Backend already works well
- Python better for blockchain/AI integration
- Avoid dual API mental model
- Next.js purely for frontend rendering

**Future Option**: Could add Next.js API routes for specific use cases (e.g., OG image generation) but not required for foundation.

### 6. Keep Existing Deployment Flow

**Decision**: Minimal changes to deployment (Vercel or static export).

**Options Considered**:
- **Vercel deployment**: Full Next.js features (SSR, Edge functions)
- **Static export**: Compatible with any host but loses SSR benefits

**Recommended**: Start with Vercel for simplicity, can export static later if needed.

## Risks / Trade-offs

### Risk: Breaking Existing Features During Migration

**Likelihood**: Medium
**Impact**: High
**Mitigation**:
- Keep old Vite code until new stack validated
- Manual testing checklist for core flows
- Can revert commits if critical issues found
- Foundation-only scope reduces blast radius

### Risk: 'use client' Directive Confusion

**Likelihood**: Medium
**Impact**: Low
**Mitigation**:
- Document which components need 'use client' (wallet, state, browser APIs)
- Use server components by default, add 'use client' when errors occur
- Simple rule: If it uses useState/useEffect/wagmi hooks → 'use client'

### Risk: Environment Variable Migration Bugs

**Likelihood**: Low
**Impact**: Medium
**Mitigation**:
- Create .env.example with all NEXT_PUBLIC_ variables
- Find-replace VITE_ in code before testing
- Validate all environment variables load correctly during local testing

### Trade-off: Increased Bundle Size

Next.js has larger runtime than Vite. Accepted because:
- Better code splitting can offset this
- SEO and performance benefits outweigh size increase
- Can optimize later with server components

### Trade-off: More Complex Mental Model

Next.js App Router has server/client component split. Accepted because:
- Only affects developers, not users
- Better DX long-term with clearer data flow
- Enables future optimizations

## Migration Plan

### Phase 1: Setup (Tasks 1.1-1.6)
1. Install Next.js and dependencies
2. Create basic config files
3. Setup Tailwind and TypeScript
4. No code execution yet (just configuration)

### Phase 2: Foundation Structure (Tasks 2.1-2.6)
1. Create app directory with root layout
2. Setup providers (wallet, theme, query)
3. Create stub pages for core routes
4. Verify routing works

### Phase 3: Web3 Integration (Tasks 3.1-3.5)
1. Port wallet configuration
2. Test wallet connection flow
3. Verify contract interaction patterns

### Phase 4: Component Foundation (Tasks 4.1-4.4)
1. Migrate layout components
2. Port shadcn/ui setup
3. Test theme and UI components

### Phase 5: Validation (Tasks 5.1-6.5)
1. Local development testing
2. Production build verification
3. Manual browser testing
4. Document any issues for post-migration fixes

### Rollback Plan
If critical issues found:
1. Revert Next.js commits
2. Restore Vite configuration
3. Document blockers for future attempt

## Open Questions

1. **Deployment target**: Vercel (SSR) vs static export (Netlify/Cloudflare Pages)?
   - **Recommendation**: Start with Vercel, can change later

2. **Image optimization**: Use Next.js Image component or keep native img tags?
   - **Recommendation**: Defer to post-migration (not foundation concern)

3. **Metadata strategy**: Static metadata vs generateMetadata for dynamic NFT pages?
   - **Recommendation**: Start with static, add dynamic later for NFT previews

4. **Styling approach**: Keep all Tailwind or explore CSS modules for complex components?
   - **Recommendation**: Keep Tailwind for consistency
