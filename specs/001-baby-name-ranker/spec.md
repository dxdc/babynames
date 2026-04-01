# Feature Specification: Baby Name Discovery & Ranking App

**Feature Branch**: `001-baby-name-ranker`  
**Created**: 2026-03-31  
**Status**: Draft  
**Input**: User description: "An app to help parents, family, friends rate baby names from a giant database, with filters based on statistics, name origin, popularity globally or in particular parts of the world, culture/language groups. Some parents want names that are NOT too popular or were more common in different eras. Helps narrow down possible names to a manageable dataset. Existing code from sample apps available. Make it prettier, easier to save/store progress, do multiple ranking iterations with different filters, favourite names. Dive into name details: origin, popularity by region, language, year, meanings, and etymology."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Browse and Filter Names (Priority: P1)

A parent opens the app and sees the full name database. They apply filters to narrow the list: selecting a cultural origin (e.g. Celtic), a popularity range (e.g. "uncommon" — outside the top 500), and a time period preference (e.g. names that peaked in the 1920s–1950s). The filtered list updates in real time. They can further sort by alphabetical order, popularity trend, or origin. Crucially, "inverse popularity" filtering lets parents find names that are NOT too common — a key use case for parents wanting something distinctive.

**Why this priority**: Filtering is the core mechanism that makes a database of tens of thousands of names usable. Without it, users cannot narrow choices to a manageable set. Every other feature depends on having a curated subset to work with.

**Independent Test**: Can be fully tested by loading the app, applying multiple filter combinations, and verifying the result set updates correctly. Delivers immediate value by turning an overwhelming list into a curated shortlist.

**Acceptance Scenarios**:

1. **Given** the full name database is loaded, **When** a user selects origin filter "Celtic" and popularity filter "outside top 500 globally", **Then** only names matching both criteria are displayed
2. **Given** filters are applied, **When** the user removes one filter, **Then** the results expand to include names matching the remaining filters
3. **Given** no filters are applied, **When** the user views the name list, **Then** all names in the database are browsable with pagination or infinite scroll
4. **Given** filter criteria match zero names, **When** the results are empty, **Then** the user sees a clear message suggesting they broaden their filters
5. **Given** a user wants uncommon names, **When** they set the popularity filter to "outside top 1000", **Then** only names ranked below 1000 in the selected region are shown

---

### User Story 2 - Rank Names Through Pairwise Comparison (Priority: P1)

A parent starts a ranking round from their filtered shortlist. Names are presented in pairs (head-to-head), and the user picks which they prefer. Rankings accumulate across rounds — running a second round with different filters feeds additional data into the same overall leaderboard, refining it further rather than creating a separate one. The leaderboard is a living, evolving view of the user's preferences that gets sharper with each round.

**Why this priority**: Pairwise ranking is the primary decision-making mechanism — it transforms subjective preference into a quantified order. Equal priority to filtering because both are needed for the core loop.

**Independent Test**: Can be fully tested by selecting a set of names, completing 20+ pairwise comparisons, and verifying the leaderboard reflects choices accurately. Running a second session with different filters produces an independent leaderboard.

**Acceptance Scenarios**:

1. **Given** a filtered shortlist of at least 2 names, **When** the user starts a ranking session, **Then** names are presented in pairs for comparison
2. **Given** a ranking session is in progress, **When** the user selects a preferred name from a pair, **Then** the ranking scores update and a new pair is presented
3. **Given** the user completes a ranking round with one filter set, **When** they start another round with different filters, **Then** new comparisons feed into the same cumulative leaderboard, refining the overall ranking
4. **Given** a leaderboard with accumulated data from multiple rounds, **When** the user views it, **Then** the system indicates ranking confidence (e.g. names with many comparisons are more settled than those with few)

---

### User Story 3 - Explore Name Details (Priority: P2)

A user taps on any name (in search results, leaderboard, or favourites) and sees a detailed profile: the name's meaning(s), etymology, linguistic origin, cultural significance, historical popularity trends by region and decade, variant spellings across languages, and notable namesakes. Popularity data is shown visually so users can see whether a name is trending up or down.

**Why this priority**: Name details provide the depth needed for informed decisions. Users need to understand a name's story before committing. Slightly lower than filtering and ranking because the core loop works without deep detail.

**Independent Test**: Can be fully tested by navigating to any name's detail view and verifying all data sections are populated with accurate information. Charts display correctly and respond to region/time range selection.

**Acceptance Scenarios**:

1. **Given** a name appears in any list, **When** the user taps the name, **Then** a detailed profile view opens showing meaning, origin, etymology, and popularity data
2. **Given** a name detail view is open, **When** the user selects a specific region, **Then** the popularity chart updates to show that region's data
3. **Given** a name has multiple meanings or origins, **When** the detail view loads, **Then** all known meanings and origins are displayed with their cultural context
4. **Given** a name detail view, **When** the user selects different decades or year ranges, **Then** popularity trends update to reflect the selected time period

---

### User Story 4 - Favourite and Save Names (Priority: P2)

A user marks names as favourites from any screen (search, ranking, detail view). Favourites persist across sessions and can be viewed in a dedicated list. The user can add personal notes to favourited names (e.g. "Grandma's middle name", "Partner loves this one"). Favourites can be used as the input set for a new ranking session.

**Why this priority**: Persistence and favourites bridge the gap between casual browsing and committed decision-making. Important for the iterative workflow but dependent on the core browse/rank loop existing first.

**Independent Test**: Can be fully tested by favouriting names from different screens, closing and reopening the app, and verifying favourites persist with any notes attached.

**Acceptance Scenarios**:

1. **Given** any name is visible on screen, **When** the user taps the favourite button, **Then** the name is added to their favourites list and the button state changes to indicate it is favourited
2. **Given** names are favourited, **When** the user navigates to the favourites list, **Then** all favourited names appear with their notes and the date added
3. **Given** the favourites list, **When** the user starts a ranking session from favourites, **Then** only favourited names are used in the pairwise comparisons
4. **Given** a favourited name, **When** the user adds or edits a note, **Then** the note persists and is visible wherever the name appears

---

### User Story 5 - Collaborative Rating (Priority: P3)

Both parents (or other family/friends) contribute to the ranking. Each participant runs their own ranking sessions independently. A combined view shows where preferences overlap — names that both parents ranked highly are highlighted as strong candidates. Disagreements are visible too, prompting discussion.

**Why this priority**: Collaborative features add significant value for the real-world use case (two parents deciding together) but require the single-user experience to be solid first.

**Independent Test**: Can be fully tested by two users independently ranking the same set of names and then viewing the combined results. Overlap and divergence are clearly displayed.

**Acceptance Scenarios**:

1. **Given** two participants have completed independent ranking sessions on overlapping name sets, **When** they view the combined results, **Then** names ranked highly by both are highlighted as "strong matches"
2. **Given** combined results are displayed, **When** a name is ranked highly by one participant but low by the other, **Then** it is flagged as a "discussion point" with both scores visible
3. **Given** a user wants to invite a collaborator, **When** they share the session, **Then** the collaborator can join and run their own rankings without seeing the inviter's results first

---

### User Story 6 - Save and Resume Progress (Priority: P2)

A user's entire state — filters, ranking sessions, favourites, notes — persists automatically on the server, tied to their account. They can close the app and return days later — on any device — to find everything as they left it. Authentication is handled via the existing Authentik instance (SSO), so users sign in once and their data syncs everywhere.

**Why this priority**: Data persistence is essential for an app used over weeks/months of decision-making. Without it, users lose work and abandon the product.

**Independent Test**: Can be fully tested by creating filters, running a partial ranking session, favouriting names, closing the app completely, and reopening to verify all state is restored.

**Acceptance Scenarios**:

1. **Given** a user has active ranking sessions and favourites, **When** they close and reopen the app, **Then** all sessions, favourites, filters, and notes are exactly as they left them
2. **Given** a user is mid-ranking, **When** they navigate away and return, **Then** the ranking session resumes from where they left off
3. **Given** a user signs in on a new device, **When** they authenticate, **Then** all their ranking sessions, favourites, and notes are available immediately

---

### Edge Cases

- What happens when a name exists in the database with conflicting data from multiple sources (e.g. different origins listed)? Display all known origins with their sources, letting the user see the full picture.
- How does the system handle names with non-Latin characters (e.g. Chinese, Arabic, Hebrew names)? Names display in their original script alongside a romanised/transliterated version where available.
- What happens when a user tries to rank fewer than 2 names? The system informs the user that at least 2 names are needed and suggests broadening filters.
- How does the system handle names that are culturally identical but spelled differently across regions (e.g. Mohammed/Muhammad/Mohamed)? Variant spellings are linked and can be viewed as a group or individually.
- What happens when popularity data is unavailable for a specific region or time period? The system clearly indicates "No data available" rather than showing zeros or estimates.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a searchable, filterable database of baby names spanning multiple cultures and languages
- **FR-002**: System MUST allow filtering by: name origin/culture, popularity rank (global and regional), time period/era, language/script, gender association, and name length
- **FR-003**: System MUST support "inverse popularity" filtering — allowing users to find names that are NOT in the top N most popular, enabling discovery of uncommon or era-specific names
- **FR-004**: System MUST present names in pairwise comparisons for ranking, using a rating algorithm that converges on a stable preference order
- **FR-005**: System MUST maintain a leaderboard per ranking session showing names ordered by calculated preference score
- **FR-006**: System MUST accumulate ranking data across multiple rounds into a single evolving leaderboard, with each round's filter criteria and comparisons contributing to the overall preference scores
- **FR-007**: System MUST display detailed name profiles including: meaning(s), etymology, linguistic origin, cultural significance, historical popularity trends by region and decade, variant spellings, and notable namesakes where data is available
- **FR-008**: System MUST show popularity trends visually with the ability to filter by region and time range
- **FR-009**: System MUST allow users to favourite/unfavourite names from any screen where a name appears
- **FR-010**: System MUST allow users to add, edit, and delete personal notes on any favourited name
- **FR-011**: System MUST persist all user data (favourites, rankings, sessions, notes, filters) across app restarts
- **FR-012**: System MUST support using the favourites list as the input set for a new ranking session
- **FR-013**: System MUST allow multiple participants to independently rank the same set of names and view combined results highlighting agreement and disagreement
- **FR-014**: System MUST handle names in non-Latin scripts, displaying original characters alongside romanised versions where data exists
- **FR-015**: System MUST indicate when data is unavailable for a specific region or time period rather than showing misleading defaults
- **FR-016**: System MUST authenticate users via the existing Authentik SSO instance and persist all state server-side, accessible from any device

### Key Entities

- **Name**: The core entity — includes display name, romanised form (if applicable), gender association (masculine/feminine/unisex), and links to origins, meanings, and popularity records
- **Origin**: Cultural, linguistic, or geographic origin of a name. A name may have multiple origins. Includes language family, region, and cultural context
- **Popularity Record**: A name's ranking/frequency in a specific region during a specific time period. Enables trend analysis across decades and geographies
- **Meaning**: One or more semantic meanings of a name, with etymology tracing the word's linguistic history
- **Variant**: Alternative spellings or forms of the same name across languages or regions, linked to a common root
- **Ranking Session**: A user-initiated comparison activity with specific filter criteria, a set of names, pairwise comparison results, and a calculated leaderboard
- **Favourite**: A user's bookmarked name with optional personal notes and timestamp
- **Participant**: A person contributing rankings. Multiple participants can be linked to view combined results

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can narrow the full name database to a shortlist of under 50 names in under 5 minutes using filters
- **SC-002**: Users can complete a ranking session of 20 names (achieving a stable top-5 leaderboard) in under 10 minutes
- **SC-003**: 90% of users who start a ranking session complete it and view the leaderboard
- **SC-004**: Name detail profiles load within 2 seconds and display at least 3 data categories (meaning, origin, popularity)
- **SC-005**: All user data (favourites, sessions, rankings) survives app restart with zero data loss
- **SC-006**: Two participants can independently rank the same names and view combined results within the same day
- **SC-007**: Users rate the app's visual design as "appealing" or better in 75% of feedback responses
- **SC-008**: Users can find and apply any filter combination in under 3 taps/clicks from the main screen

## Assumptions

- The existing US SSA dataset (~99,000 names) provides the foundation; global/regional popularity data will be sourced from additional public datasets (e.g. UK ONS, Australian state registries, Nordic open data) and enriched incrementally — v1 may launch with US data as the most complete region while others are partial
- The Behind the Name enrichment data already in the codebase provides meaning and origin for many names; gaps will be filled progressively rather than blocking launch
- The existing Glicko-2 implementation is a valid ranking algorithm that can be adapted rather than replaced
- The initial version targets web browsers (desktop and mobile-responsive); native mobile apps are out of scope for v1
- Authentication uses the existing Authentik instance — no new auth system to build. Collaborative features link authenticated users rather than requiring separate invite codes
- The UI should be colourful, fun, mobile-first, and guide users through the full flow (filter → rank → review → share) in one seamless experience. Think playful and opinionated — not a generic data table with filters bolted on. The existing mockup in `preview-mockup.html` is NOT the design direction
- Name data is primarily in English with support for displaying non-Latin scripts where source data includes them; the app interface itself is in English only for v1
