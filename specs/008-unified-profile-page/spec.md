# Feature Specification: Unified Profile Page with Author & Collector Tabs

**Feature Branch**: `008-unified-profile-page`
**Created**: 2025-10-22
**Status**: Draft
**Input**: User description: "Unified Profile Page with Author & Collector Tabs - Refactor two separate pages (`/creator-dashboard` and `/profile-settings`) into a single unified `/profile` page with two tabs to consolidate author functionality and add NFT collection display."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Navigate to Unified Profile Page (Priority: P1)

A user with a connected wallet clicks a "Profile" button in the header and is taken to `/profile` with the "Prompt Author" tab active by default. They see their prompt management UI and X account linking section consolidated in a single view.

**Why this priority**: This establishes the foundation for the unified profile experience. Without this navigation and routing working correctly, all other functionality is inaccessible. Critical for the entire feature to function.

**Independent Test**: Can be fully tested by connecting a wallet, clicking the Profile button, and verifying the browser navigates to `/profile?tab=author` and displays the correct tab content.

**Acceptance Scenarios**:

1. **Given** a user has a wallet connected, **When** they click the "Profile" button in the header, **Then** they are navigated to `/profile?tab=author`
2. **Given** a user navigates to `/profile` without a query parameter, **When** the page loads, **Then** the URL updates to `/profile?tab=author` and the Prompt Author tab is active
3. **Given** a user is on `/profile?tab=author`, **When** the page loads, **Then** they see the prompt management UI and X account linking section
4. **Given** a user does not have a wallet connected, **When** they navigate to `/profile`, **Then** they see a message indicating wallet connection is required

---

### User Story 2 - View Authored NFTs in Prompt Author Tab (Priority: P1)

A user views their Prompt Author tab and sees a list of NFTs where their wallet address is registered as the prompt author. The NFTs are displayed in a paginated grid showing 20 items per page with basic pagination controls.

**Why this priority**: This is the primary new functionality that adds value beyond the consolidation of existing pages. Authors need to see which NFTs have been created using their prompts. Core deliverable for this feature.

**Independent Test**: Can be fully tested by connecting a wallet that has authored NFTs, navigating to the Prompt Author tab, and verifying that authored NFTs appear in the list with correct pagination when more than 20 exist.

**Acceptance Scenarios**:

1. **Given** a user's wallet has authored 5 NFTs, **When** they view the Prompt Author tab, **Then** they see all 5 NFTs displayed
2. **Given** a user's wallet has authored 25 NFTs, **When** they view the Prompt Author tab, **Then** they see 20 NFTs on page 1 with pagination controls
3. **Given** a user is on page 1 of authored NFTs with 25 total, **When** they click the next page control, **Then** they see the remaining 5 NFTs on page 2
4. **Given** a user's wallet has not authored any NFTs, **When** they view the Prompt Author tab, **Then** they see no NFTs displayed (no error)
5. **Given** a user switches wallets, **When** they view the Prompt Author tab, **Then** the NFT list updates to show NFTs authored by the new wallet without requiring page refresh

---

### User Story 3 - View Owned NFTs in Collector Tab (Priority: P1)

A user switches to the "Collector" tab and sees a paginated grid of NFTs they own, fetched directly from the blockchain using ERC721Enumerable functions. NFTs are displayed using thirdweb v5 components showing media, name, and other metadata.

**Why this priority**: This completes the dual-view functionality that distinguishes this feature. Users need to see both NFTs they've authored and NFTs they own. Core deliverable alongside authored NFTs view.

**Independent Test**: Can be fully tested by connecting a wallet that owns NFTs, switching to the Collector tab, and verifying that owned NFTs appear correctly with pagination for collections larger than 20 tokens.

**Acceptance Scenarios**:

1. **Given** a user clicks the "Collector" tab, **When** the tab loads, **Then** the URL updates to `/profile?tab=collector`
2. **Given** a user's wallet owns 3 NFTs, **When** they view the Collector tab, **Then** they see all 3 NFTs displayed using thirdweb components
3. **Given** a user's wallet owns 30 NFTs, **When** they view the Collector tab, **Then** they see 20 NFTs on page 1 with pagination controls
4. **Given** a user is on page 1 of owned NFTs with 30 total, **When** they click the next page control, **Then** they see the remaining 10 NFTs on page 2
5. **Given** a user does not own any NFTs, **When** they view the Collector tab, **Then** they see no NFTs displayed (no error)
6. **Given** a user switches wallets, **When** they view the Collector tab, **Then** the NFT list updates to show NFTs owned by the new wallet without requiring page refresh

---

### User Story 4 - Tab Switching Preserves State (Priority: P2)

A user switches between the Prompt Author and Collector tabs multiple times, and each tab retains its pagination state and loaded data until the wallet changes.

**Why this priority**: This enhances user experience by avoiding unnecessary data refetching and maintaining context when navigating between tabs. Important for usability but not critical for core functionality.

**Independent Test**: Can be fully tested by navigating to page 2 on the Prompt Author tab, switching to the Collector tab, then switching back, and verifying the Prompt Author tab is still on page 2.

**Acceptance Scenarios**:

1. **Given** a user is on page 2 of the Prompt Author tab, **When** they switch to the Collector tab and back, **Then** they return to page 2 of the Prompt Author tab
2. **Given** a user has loaded data in both tabs, **When** they switch between tabs, **Then** no new API or blockchain requests are made unless the wallet changes
3. **Given** a user switches wallets while on a specific tab and page, **When** the wallet changes, **Then** the current tab refreshes its data and resets to page 1

---

### Edge Cases

- What happens when a user navigates to `/profile` with an invalid tab query parameter (e.g., `?tab=invalid`)?
  - System defaults to the Prompt Author tab (`?tab=author`) and updates the URL
- What happens when the backend API for authored NFTs returns an error?
  - User sees an error state in the Prompt Author tab's NFT section; prompt management and X linking sections remain functional
- What happens when blockchain read calls fail (e.g., RPC endpoint unavailable)?
  - User sees an error state in the Collector tab with a retry button; other tabs remain functional
- What happens when a user has exactly 20 authored/owned NFTs?
  - Pagination controls are hidden (single page view)
- What happens when a user's wallet owns 0 NFTs but has authored 10 NFTs?
  - Prompt Author tab shows 10 NFTs, Collector tab shows no NFTs (both are valid states)
- What happens when a user rapidly switches between tabs?
  - System debounces or cancels in-flight requests to prevent race conditions; latest tab selection wins
- What happens when pagination controls are clicked while data is loading?
  - Pagination controls are disabled during loading to prevent double requests

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a single `/profile` route accessible from a "Profile" button in the header
- **FR-002**: System MUST support tab navigation via query parameters (`?tab=author` or `?tab=collector`)
- **FR-003**: System MUST default to the Prompt Author tab when no query parameter is provided or when an invalid tab parameter is given
- **FR-004**: System MUST update the browser URL when users switch between tabs without triggering a full page reload
- **FR-005**: Prompt Author tab MUST display the prompt management UI (textarea, save button, status indicators)
- **FR-006**: Prompt Author tab MUST display the X account linking section (link button, linked status, OAuth flow)
- **FR-007**: Prompt Author tab MUST display a paginated list of NFTs where the connected wallet is the prompt author
- **FR-008**: Prompt Author tab MUST fetch authored NFTs from a backend API endpoint that queries tokens by author wallet address
- **FR-009**: Collector tab MUST display a paginated list of NFTs owned by the connected wallet address
- **FR-010**: Collector tab MUST fetch owned NFTs directly from the blockchain using ERC721Enumerable methods (balanceOf, tokenOfOwnerByIndex)
- **FR-011**: System MUST display 20 NFTs per page in both tabs
- **FR-012**: System MUST provide pagination controls (next/previous or page numbers) for NFT lists exceeding 20 items
- **FR-013**: System MUST use thirdweb v5 React components for rendering NFT media, names, and metadata in both tabs
- **FR-014**: System MUST refresh NFT data in the active tab when the connected wallet address changes
- **FR-015**: System MUST reset pagination to page 1 when the connected wallet address changes
- **FR-016**: System MUST require wallet connection to access the profile page
- **FR-017**: System MUST hide pagination controls when NFT count is 20 or fewer
- **FR-018**: System MUST disable pagination controls while data is loading to prevent duplicate requests
- **FR-019**: System MUST handle backend API errors gracefully in the Prompt Author tab without breaking other sections
- **FR-020**: System MUST handle blockchain read errors gracefully in the Collector tab with retry functionality
- **FR-021**: System MUST use minimal styling (bare HTML elements, basic spacing, no decorative elements) as this is a functional prototype

### Key Entities

- **Profile Page**: Unified page accessible at `/profile` that consolidates author functionality and displays NFT collections. Includes tab navigation, prompt management, X account linking, and NFT lists.
- **Tab State**: Current active tab (Prompt Author or Collector) tracked via URL query parameter. Determines which content is visible and which data sources are queried.
- **Authored NFTs**: Collection of NFT tokens where the connected wallet's address matches the author_id field in the database. Fetched from backend API with pagination support.
- **Owned NFTs**: Collection of NFT tokens owned by the connected wallet's address, determined by on-chain ownership records. Fetched from blockchain using ERC721Enumerable with pagination support.
- **Pagination State**: Current page number and total pages for each tab's NFT list. Reset to page 1 when wallet changes, preserved when switching between tabs.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can navigate from header to profile page in under 1 second (single click, instant routing)
- **SC-002**: Tab switching updates URL and content in under 500ms (no full page reload)
- **SC-003**: Authored NFTs load and display within 2 seconds of tab activation
- **SC-004**: Owned NFTs load and display within 3 seconds of tab activation (blockchain reads may be slower)
- **SC-005**: Pagination controls function correctly 100% of the time (no duplicate requests, correct page numbers)
- **SC-006**: Wallet changes trigger data refresh in under 3 seconds for the active tab
- **SC-007**: System handles up to 1000 authored NFTs per wallet without performance degradation (50 pages of pagination)
- **SC-008**: System handles up to 1000 owned NFTs per wallet without performance degradation (50 pages of pagination)
- **SC-009**: 100% of existing prompt management functionality works identically after consolidation
- **SC-010**: 100% of existing X account linking functionality works identically after consolidation

## Assumptions

- Users are already familiar with connecting their wallet via the existing header component
- The backend database contains an author_id field (wallet address) for NFT tokens that can be queried
- The smart contract implements ERC721Enumerable interface with balanceOf and tokenOfOwnerByIndex functions
- thirdweb v5 SDK is already integrated in the frontend project and configured for the correct blockchain network
- The existing prompt management and X linking functionality can be directly moved to the new page without requiring refactoring
- The Header component can be updated to replace separate "Creator Dashboard" and "Profile Settings" buttons with a single "Profile" button
- Minimal design means absolutely no CSS classes beyond basic utility classes for spacing (if any)
- Performance for blockchain reads (owned NFTs) may be slower than backend API reads (authored NFTs) due to RPC latency
- Users understand the distinction between "authored" (created the prompt) and "owned" (owns the NFT) without detailed explanatory text
- Pagination using basic HTML controls (buttons) is acceptable for this prototype
- Error states can be displayed as plain text without styling or icons
- Empty states (no NFTs) can be represented by empty space or a single line of text

## Out of Scope

- Polished UI/UX design including colors, typography, spacing, layout grids, and visual hierarchy (next spec)
- User-facing help text, tooltips, empty state messaging, and explanatory copy (next spec)
- Filtering NFTs by status, date, or other attributes
- Sorting NFTs by different criteria (date minted, token ID, rarity)
- Individual NFT detail pages showing full metadata and transaction history
- Export functionality to download NFT lists or generate reports
- Share functionality to share profile or NFT collections on social media
- Analytics dashboard showing statistics about authored/owned NFTs over time
- Rewards claiming UI in the profile page (remains in separate location if exists)
- Mobile-responsive design optimization (basic responsiveness from existing components is acceptable)
- Loading skeletons or animated loaders (basic "Loading..." text is acceptable)
- Infinite scroll pagination (only basic page-based pagination)
- Real-time updates when new NFTs are minted or transferred (manual refresh required)
- Tab state persistence in browser session storage
- Deep linking to specific tab and page (e.g., `/profile?tab=collector&page=3`)
