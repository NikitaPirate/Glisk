# Feature Specification: Author Leaderboard Landing Page

**Feature Branch**: `009-create-a-main`
**Created**: 2025-10-22
**Status**: Draft
**Input**: User description: "Create a main landing page (/) that displays a simple list of NFT prompt authors ranked by their total minted token count"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Discover Top Authors (Priority: P1)

As a visitor to the Glisk platform, I want to see which prompt authors have created the most NFTs, so I can discover popular creators and explore their work.

**Why this priority**: This is the core value proposition of the landing page - discovery. Without this, the page has no purpose. It delivers immediate value by surfacing the most active creators to new visitors.

**Independent Test**: Can be fully tested by loading the landing page and verifying that authors appear in descending order by token count. Delivers standalone value by allowing users to identify top creators without needing any other features.

**Acceptance Scenarios**:

1. **Given** the platform has multiple authors with different token counts, **When** a visitor loads the landing page (/), **Then** they see a list of authors ordered by total minted NFT count from highest to lowest
2. **Given** an author has minted 50 tokens and appears in the leaderboard, **When** the visitor views the list, **Then** they see the author's wallet address and "50 tokens" displayed together
3. **Given** a visitor is viewing the leaderboard, **When** they click on any author entry, **Then** they navigate to that author's profile page showing their NFT collection

---

### User Story 2 - Empty State Experience (Priority: P2)

As a visitor arriving when the platform is new or has no data, I want to see a clear message explaining the current state, so I understand the platform is working correctly and what to expect.

**Why this priority**: Critical for early platform stages and error scenarios, but secondary to the core discovery feature. Provides professional user experience during edge cases.

**Independent Test**: Can be tested independently by clearing the database and loading the landing page. Delivers value by preventing user confusion during no-data scenarios.

**Acceptance Scenarios**:

1. **Given** no authors have minted any tokens yet, **When** a visitor loads the landing page, **Then** they see a message "No authors yet" instead of an empty list
2. **Given** the backend API is temporarily unavailable, **When** a visitor loads the landing page, **Then** they see a "Loading..." message while the system attempts to fetch data

---

### User Story 3 - Loading State Feedback (Priority: P3)

As a visitor waiting for data to load, I want to see a loading indicator, so I know the application is working and haven't encountered an error.

**Why this priority**: Improves perceived performance and user experience, but the feature works without it. Can be added after core functionality is validated.

**Independent Test**: Can be tested independently by throttling network speed and observing the loading state before data appears. Delivers value by improving user confidence during data fetching.

**Acceptance Scenarios**:

1. **Given** the landing page is fetching author data from the backend, **When** the data is still loading, **Then** the visitor sees "Loading..." text displayed
2. **Given** the data fetch completes successfully, **When** the authors are retrieved, **Then** the loading text is replaced with the author list

---

### Edge Cases

- What happens when an author has 0 minted tokens? (Should not appear in leaderboard - only authors with ≥1 token shown)
- How does the system handle authors with identical token counts? (Sort by wallet address alphabetically as secondary sort)
- What happens if the backend API returns more than 50 authors? (Frontend displays only first 50 from API response)
- What happens if a wallet address is invalid or malformed in the database? (Display as-is - validation is backend concern, frontend displays what it receives)
- What happens when network request fails? (Loading state persists with "Loading..." - no error message in MVP)

## Requirements *(mandatory)*

### Functional Requirements

**Backend**:

- **FR-001**: System MUST provide a new API endpoint at GET /api/authors/leaderboard that returns author statistics
- **FR-002**: API MUST return an array of objects, each containing author_address (string) and total_tokens (number)
- **FR-003**: API MUST aggregate token counts by grouping all tokens in the tokens_s0 table by author_address field
- **FR-004**: API MUST sort results by total_tokens in descending order (highest count first)
- **FR-005**: API MUST limit results to a maximum of 50 authors
- **FR-006**: API MUST exclude authors with zero tokens from the response
- **FR-007**: API MUST handle identical token counts by applying secondary sorting by author_address in alphabetical order

**Frontend**:

- **FR-008**: System MUST create a new route at the root path (/) that displays the author leaderboard
- **FR-009**: System MUST fetch author data from GET /api/authors/leaderboard on page load
- **FR-010**: System MUST display each author as a list item showing wallet address and token count
- **FR-011**: Each author list item MUST be clickable and navigate to /{authorAddress} when clicked
- **FR-012**: System MUST display "Loading..." text while data is being fetched
- **FR-013**: System MUST display "No authors yet" when the API returns an empty array
- **FR-014**: System MUST maintain descending order by token count as provided by the API

**Design**:

- **FR-015**: UI MUST use basic Tailwind CSS styling with simple borders separating list items
- **FR-016**: UI MUST NOT include cards, pagination, search, filtering, thumbnails, badges, skeleton loaders, or visual effects beyond basic hover states
- **FR-017**: UI MUST follow the project's "Simplicity First" design principle with minimal styling

### Key Entities

- **Author**: Represents an NFT prompt creator, identified by their wallet address, with an aggregate count of tokens they have minted
- **Token**: Individual NFT minted on the platform, associated with a single author via author_address field in tokens_s0 table

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Visitors can identify the top NFT creator within 3 seconds of landing page load
- **SC-002**: Users can navigate from landing page to any author's profile in one click (100% of author entries are clickable links)
- **SC-003**: Landing page displays correct ranking order with 100% accuracy (verified against database token counts)
- **SC-004**: Page handles zero-data state gracefully with clear messaging (no broken UI or empty screens)
- **SC-005**: API response time for leaderboard endpoint is under 500ms for datasets up to 50 authors
- **SC-006**: Landing page serves as effective discovery mechanism - establishes baseline for future tracking of author profile navigation rate from leaderboard

## Assumptions

- The existing profile page route (/{authorAddress}) from feature 008 is fully functional and requires no modifications
- The tokens_s0 table has an author_address column that reliably identifies the prompt author
- Wallet addresses in the database are valid Ethereum addresses (validation handled during token creation)
- The backend API framework (FastAPI) supports adding new GET endpoints without architectural changes
- The frontend router (react-router-dom) can handle adding a new root route without conflicts
- 50 authors is sufficient for MVP scope - pagination can be added in future iterations if needed
- Basic hover states are acceptable styling for clickable list items (no complex interactions required)
- "Loading..." text is sufficient user feedback during data fetching (no spinner or skeleton required for MVP)
- Network errors are rare enough that showing persistent "Loading..." is acceptable in MVP (error handling can be enhanced later)

## Dependencies

- Backend database must have tokens_s0 table with author_address field populated
- Frontend must have existing routing infrastructure from feature 008 (react-router-dom)
- Frontend must have Tailwind CSS configured for styling
- Existing profile page at /{authorAddress} must handle navigation from external links

## Out of Scope

The following are explicitly excluded from this feature:

- Card-based layouts or fancy UI components
- Pagination controls or infinite scroll
- Search functionality or filtering options
- Author profile thumbnails or NFT preview images
- Badge/ranking icons (e.g., "TOP 1" badges)
- Skeleton loading animations
- Visual effects beyond basic CSS hover states (no transitions, animations, or effects)
- Error state handling beyond "Loading..." (no error messages or retry buttons)
- Author profile information beyond wallet address and token count
- Real-time updates to leaderboard (static data on page load)
- Export or sharing functionality
- Analytics tracking of user interactions
