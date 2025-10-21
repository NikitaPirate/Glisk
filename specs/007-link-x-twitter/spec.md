# Feature Specification: X (Twitter) Account Linking for Authors

**Feature Branch**: `007-link-x-twitter`
**Created**: 2025-10-21
**Status**: Draft
**Input**: User description: "link X(twitter) to author's account, add X in nft meta if author has. (don't enter x handler manually, use oauth authorize) out of scope - session persistance eth. we only need auth one time - to ensure user is owner of x account. Find the easiest way to implement this"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - One-Time X Account Verification (Priority: P1)

An author wants to link their X (Twitter) account to their glisk author profile so that their X handle appears in NFT metadata. They navigate to a profile settings page, click "Link X Account" (visible only if they haven't linked yet), complete X's OAuth authorization flow in a popup/redirect, and return to see their X handle displayed in their profile. The system stores the verified X handle permanently but does not maintain ongoing session state. This is a one-time action with no ability to unlink or change the linked account in MVP.

**Why this priority**: Core feature requirement. Without X account linking, authors cannot have their social media presence reflected in NFT metadata. This is the foundation for all other related functionality.

**Independent Test**: Can be fully tested by navigating to author profile settings, clicking "Link X Account", completing OAuth flow, and verifying the X handle appears in the author's profile record in the database and the "Link X Account" button is no longer visible.

**Acceptance Scenarios**:

1. **Given** an author is logged into glisk (wallet connected) and has not linked an X account, **When** they navigate to profile settings, **Then** they see a "Link X Account" button
2. **Given** an author clicks "Link X Account", **When** the OAuth flow completes, **Then** they are redirected to X's OAuth authorization page
3. **Given** the author is on X's OAuth authorization page, **When** they approve the authorization request, **Then** they are redirected back to glisk with an authorization code
4. **Given** the author returns from X OAuth with a valid authorization code, **When** the system exchanges the code for an access token and retrieves the X username, **Then** the X handle is stored in the author's profile record
5. **Given** an author has successfully linked their X account, **When** they view their profile settings, **Then** they see their X handle displayed (e.g., "@username") and the "Link X Account" button is hidden
6. **Given** an author has linked their X account, **When** a new NFT is minted with their prompt, **Then** the NFT metadata includes their X handle

---

### User Story 2 - X Handle in NFT Metadata (Priority: P1)

When an NFT is minted for an author who has linked their X account, the metadata stored on IPFS includes the author's X handle in a standard field. When users view the NFT on marketplaces or block explorers, they can see the author's X handle and potentially visit their X profile.

**Why this priority**: This is the end goal of the feature - surfacing author social media in NFT metadata. Without this, linking X accounts has no user-facing value. Critical for launch.

**Independent Test**: Can be fully tested by minting an NFT for an author with a linked X account, retrieving the metadata from IPFS, and verifying the X handle appears in the metadata JSON (e.g., in an "author" or "creator" object).

**Acceptance Scenarios**:

1. **Given** an author has linked their X account (e.g., "@gliskartist"), **When** an NFT is minted with their prompt, **Then** the metadata JSON includes the X handle in a creator/author field
2. **Given** an NFT's metadata includes an author's X handle, **When** a user views the metadata, **Then** the X handle is visible and formatted as "@username"
3. **Given** an author has not linked their X account, **When** an NFT is minted with their prompt, **Then** the metadata does not include an X handle field (or the field is null/empty)

---

### Edge Cases

- What happens when an author tries to link an X account that is already linked to a different author profile?
  - The system allows multiple authors to link the same X account (no uniqueness constraint). This is acceptable for MVP to simplify implementation.
- What happens when the X OAuth flow fails (user denies access, network error, invalid credentials)?
  - System shows error message and allows author to retry without changing their profile state. The "Link X Account" button remains visible.
- What happens when an author clicks "Link X Account" but already has an X account linked?
  - The "Link X Account" button is hidden for authors who have already linked an account. No re-linking or unlinking functionality in MVP.
- What happens when X changes their API or OAuth flow after initial implementation?
  - System logs errors during OAuth exchange and notifies administrators; authors see generic error message.
- What happens when an author's X account is suspended or deleted after linking?
  - The stored X handle remains in glisk and NFT metadata (historical record); no automatic re-validation occurs.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow authors to initiate X account linking from a profile settings page
- **FR-002**: System MUST show "Link X Account" button only to authors who have not yet linked an X account
- **FR-003**: System MUST hide "Link X Account" button after an author has successfully linked an account (no re-linking in MVP)
- **FR-004**: System MUST use X OAuth 2.0 authorization flow to verify account ownership (no manual handle entry)
- **FR-005**: System MUST exchange OAuth authorization code for access token and retrieve the authenticated user's X username
- **FR-006**: System MUST store the verified X handle in the author's profile record
- **FR-007**: System MUST display the linked X handle in the author's profile settings
- **FR-008**: System MUST include the author's X handle in NFT metadata JSON when the author has a linked account
- **FR-009**: System MUST NOT include X handle in NFT metadata when the author has no linked account
- **FR-010**: System MUST handle OAuth errors gracefully (user denial, network failure, invalid state) and show appropriate error messages
- **FR-011**: System MUST NOT persist X OAuth access tokens or refresh tokens beyond the initial verification flow (one-time verification only)
- **FR-012**: System MUST validate OAuth callback state parameter to prevent CSRF attacks
- **FR-013**: System MUST allow multiple authors to link the same X account (no uniqueness constraint on X handles)

### Key Entities

- **Author Profile**: Represents an author in the glisk system. Key attributes: wallet address (primary identifier), X handle (optional, nullable string in format "@username"), profile creation timestamp, last updated timestamp
- **NFT Metadata**: JSON document stored on IPFS representing an NFT's properties. Includes: token ID, image CID, prompt text, author information (wallet address, X handle if available), mint timestamp

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Authors can complete the X account linking flow (from clicking "Link X Account" to seeing their handle displayed) in under 60 seconds
- **SC-002**: 95% of X OAuth authorization attempts complete successfully without errors (excluding user denials)
- **SC-003**: 100% of NFTs minted for authors with linked X accounts include the X handle in metadata
- **SC-004**: 0% of NFTs minted for authors without linked X accounts include an X handle field (or field is null)
- **SC-005**: System handles OAuth callback validation correctly 100% of the time (no CSRF vulnerabilities)
- **SC-006**: 100% of authors who have linked X accounts see their handle displayed and the "Link X Account" button hidden

## Assumptions

- Authors are already authenticated via wallet connection before accessing profile settings
- X OAuth 2.0 API is stable and follows standard OAuth flows (authorization code grant type)
- The system only needs to verify X account ownership once; no ongoing re-validation or token refresh is required
- X handles are stored as strings in the format "@username" (without the @ symbol is also acceptable, depending on display preferences)
- The system does not need to fetch additional X profile data (follower count, bio, profile image) beyond the username
- NFT metadata schema supports adding optional creator/author fields without breaking existing functionality
- One-time OAuth flow means the system discards access tokens immediately after retrieving the username
- The simplest implementation uses X OAuth 2.0 with minimal scopes (read user profile only)
- For MVP, permanent linking (no unlink/re-link) is acceptable to users and simplifies implementation
- Allowing duplicate X account links across multiple authors is acceptable for MVP (edge case in real-world usage)

## Out of Scope

- **Unlinking X accounts**: Authors cannot remove or disconnect their linked X account in MVP (permanent linking)
- **Re-linking X accounts**: Authors cannot change their linked X account after initial linking in MVP
- Session persistence for X OAuth tokens (explicitly stated as out of scope)
- Ongoing synchronization of X profile data (follower count, bio updates, profile image changes)
- Re-validation of X account ownership after initial linking
- Displaying X profile data beyond the handle (e.g., profile picture, bio, follower count in glisk UI)
- Allowing authors to link multiple social media accounts (Instagram, TikTok, etc.) - only X for this feature
- Automatic unlinking when an author's X account is suspended/deleted
- Admin tools to view or manage author X account links
- Preventing duplicate X account links across multiple authors (no uniqueness enforcement for MVP)
