# Tasks: Baby Name Discovery & Ranking App

**Input**: Design documents from `/specs/001-baby-name-ranker/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md

**Tests**: Included — the spec requires modular, testable code with structured logging for Chrome extension verification.

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Exact file paths included in descriptions

## Workflow Rules

1. **Atomic commits.** Commit after each logical task group, not at the end of a phase.
2. **Every phase MUST end with:** commit, push, PR, `/gemini-deathloop`, resolve all Gemini feedback before proceeding to the next phase.
3. **PR naming.** Branch `phase-N-description` off `001-baby-name-ranker`. One PR per phase, squash-merged after approval.
4. **No phase is "done" until the deathloop exits clean.** All Gemini review comments must be resolved before moving on.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialisation, tooling, both frontend and backend scaffolding

- [x] T001 Create project directory structure: `backend/`, `frontend/`, per plan.md layout
- [x] T002 [P] Initialise backend Python project with pyproject.toml in `backend/pyproject.toml` — FastAPI, SQLAlchemy, Alembic, uvicorn, python-jose, httpx deps
- [x] T003 [P] Initialise frontend SvelteKit project with pnpm in `frontend/` — Svelte 5, Tailwind CSS, Vitest, Playwright deps
- [x] T004 [P] Create design tokens (colour palette, spacing, typography, border radii) in `frontend/src/lib/design/tokens.css` — colourful, playful, mobile-first
- [x] T005 [P] Configure structured logging utility in `frontend/src/lib/utils/logger.ts` — JSON-formatted console output with component tags, levels, timestamps for Chrome extension observation
- [x] T006 [P] Configure structured logging in `backend/babynames/logging.py` — structured JSON logs with request IDs, timing

**Checkpoint**: Both projects build and run (empty shells). `pnpm dev` and `uvicorn` both start without errors. → Commit, PR, `/gemini-deathloop`. Resolve all feedback before next phase.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Database, auth, API scaffold, base models — MUST complete before any user story

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T007 Create SQLAlchemy models for Name, Origin, NameOrigin, NameMeaning, PopularityRecord, Variant in `backend/babynames/db/models.py`
- [x] T008 Configure Alembic migrations in `backend/alembic.ini` and `backend/babynames/db/migrations/`
- [x] T009 Create database seed script that loads CSVs + enrichment data into PostgreSQL in `backend/babynames/db/seed.py`
- [x] T010 [P] Implement Authentik OIDC JWT validation middleware in `backend/babynames/api/auth.py`
- [x] T011 [P] Create User model and auto-provision on first login in `backend/babynames/db/models.py` (add to existing)
- [x] T012 [P] Create FastAPI app scaffold with CORS, error handling, health check in `backend/babynames/api/main.py`
- [x] T013 [P] Create shared dependencies (db session, current user) in `backend/babynames/api/deps.py`
- [x] T014 [P] Create Authentik OIDC client integration (login/logout/token refresh) in `frontend/src/lib/stores/auth.ts`
- [x] T015 [P] Create typed API client with auth header injection in `frontend/src/lib/api/client.ts`
- [x] T016 Create app shell layout with nav, auth wrapper, mobile-first chrome in `frontend/src/routes/+layout.svelte`
- [x] T017 [P] Write unit tests for Glicko-2 algorithm in `backend/tests/unit/test_glicko2.py`
- [x] T018 Port Glicko-2 algorithm from `glicko.js` to `backend/babynames/ranking/glicko2.py`
- [ ] T019 [P] Write integration tests for auth middleware in `backend/tests/integration/test_auth.py`
- [ ] T020 [P] Write integration test for seed script in `backend/tests/integration/test_seed.py`

**Checkpoint**: Database seeded with ~99k names + enrichment. Auth flow works end-to-end (Authentik → frontend → backend JWT validation). API returns health check. Glicko-2 tests pass. → Commit, PR, `/gemini-deathloop`. Resolve all feedback before next phase.

---

## Phase 3: User Story 1 — Browse and Filter Names (Priority: P1) MVP

**Goal**: Users can search, filter, and browse the full name database with real-time filtering including inverse popularity.

**Independent Test**: Load app, apply multiple filter combinations (origin, popularity range, era, gender), verify results update correctly. Apply "outside top 1000" filter, confirm only uncommon names shown. Empty results show helpful message.

### Tests for User Story 1

- [ ] T021 [P] [US1] Integration test for `GET /api/names` with filter combinations in `backend/tests/integration/test_names_api.py`
- [ ] T022 [P] [US1] Integration test for `GET /api/origins` in `backend/tests/integration/test_names_api.py`
- [ ] T023 [P] [US1] Unit test for filter query builder in `backend/tests/unit/test_filters.py`

### Implementation for User Story 1

- [x] T024 [US1] Implement name filtering/pagination endpoint `GET /api/names` in `backend/babynames/api/routes/names.py` — all filter params from contract (q, gender, origins, min/max rank, region, era, syllables, sort, pagination)
- [x] T025 [US1] Implement origins list endpoint `GET /api/origins` in `backend/babynames/api/routes/names.py`
- [x] T026 [P] [US1] Create FilterPanel component with origin pills, popularity slider, era range, gender toggle in `frontend/src/lib/components/FilterPanel.svelte`
- [x] T027 [P] [US1] Create NameCard component (name, origin tags, popularity badge, meaning snippet) in `frontend/src/lib/components/NameCard.svelte`
- [x] T028 [US1] Create names store with reactive filter state and API integration in `frontend/src/lib/stores/names.ts`
- [x] T029 [US1] Create browse page with FilterPanel, name list (infinite scroll), sort controls in `frontend/src/routes/browse/+page.svelte`
- [x] T030 [US1] Create home page with guided entry point ("Let's find a name!") routing to browse in `frontend/src/routes/+page.svelte`
- [x] T031 [US1] Add structured console logging for filter actions and API responses in browse components
- [ ] T032 [US1] E2E test: apply filters, verify results, clear filters, verify empty state in `frontend/tests/e2e/browse.spec.ts`

**Checkpoint**: User can browse all names, apply any filter combination, see results update. Inverse popularity works. Empty state handled. MVP deliverable. → Commit, PR, `/gemini-deathloop`. Resolve all feedback before next phase.

---

## Phase 4: User Story 2 — Rank Names Through Pairwise Comparison (Priority: P1)

**Goal**: Users rank filtered names via head-to-head pairs. Rankings accumulate across rounds into a single evolving leaderboard with confidence indicators.

**Independent Test**: Filter to a set of 20 names, start ranking, complete 15+ comparisons, view leaderboard. Start a second round with different filters, verify leaderboard accumulates. Names with many comparisons show as "settled".

### Tests for User Story 2

- [ ] T033 [P] [US2] Integration test for `POST /api/ranking/compare` and `GET /api/ranking/leaderboard` in `backend/tests/integration/test_ranking_api.py`
- [ ] T034 [P] [US2] Integration test for `GET /api/ranking/pair` (pair selection algorithm) in `backend/tests/integration/test_ranking_api.py`

### Implementation for User Story 2

- [ ] T035 [US2] Create RankingState and ComparisonHistory models (add to `backend/babynames/db/models.py`)
- [ ] T036 [US2] Create Alembic migration for ranking tables in `backend/babynames/db/migrations/versions/`
- [ ] T037 [US2] Implement pair selection endpoint `GET /api/ranking/pair` in `backend/babynames/api/routes/ranking.py` — prefer high-uncertainty names, respect current filters
- [ ] T038 [US2] Implement comparison endpoint `POST /api/ranking/compare` in `backend/babynames/api/routes/ranking.py` — update Glicko-2 ratings, record history
- [ ] T039 [US2] Implement leaderboard endpoint `GET /api/ranking/leaderboard` in `backend/babynames/api/routes/ranking.py` — sorted by mu, with settled/uncertain indicator
- [ ] T040 [P] [US2] Create BattleView component (two name cards side-by-side, tap to choose, swipe gestures on mobile) in `frontend/src/lib/components/BattleView.svelte`
- [ ] T041 [P] [US2] Create Leaderboard component (ranked list with confidence badges, comparison count) in `frontend/src/lib/components/Leaderboard.svelte`
- [ ] T042 [US2] Create ranking store with session state, API integration in `frontend/src/lib/stores/ranking.ts`
- [ ] T043 [US2] Create rank page with BattleView, progress indicator, "view leaderboard" transition in `frontend/src/routes/rank/+page.svelte`
- [ ] T044 [US2] Create leaderboard page showing cumulative rankings in `frontend/src/routes/leaderboard/+page.svelte`
- [ ] T045 [US2] Add transition from browse → rank (start ranking from current filter set)
- [ ] T046 [US2] E2E test: complete ranking round, verify leaderboard, start second round, verify accumulation in `frontend/tests/e2e/ranking.spec.ts`

**Checkpoint**: Full filter → rank → leaderboard flow works. Rankings accumulate across rounds. Confidence indicators visible. → Commit, PR, `/gemini-deathloop`. Resolve all feedback before next phase.

---

## Phase 5: User Story 3 — Explore Name Details (Priority: P2)

**Goal**: Tapping any name opens a detailed profile with meanings, etymology, origins, popularity charts by region/decade, variants, and nicknames.

**Independent Test**: Tap a name from browse list, verify detail view shows meaning, origin, etymology, and popularity chart. Change region/time range on chart, verify update.

### Tests for User Story 3

- [ ] T047 [P] [US3] Integration test for `GET /api/names/:id` (full detail response) in `backend/tests/integration/test_names_api.py`

### Implementation for User Story 3

- [ ] T048 [US3] Implement name detail endpoint `GET /api/names/:id` with full joins (meanings, origins, popularity, variants, nicknames) in `backend/babynames/api/routes/names.py`
- [ ] T049 [P] [US3] Create PopularityChart component (line chart, region selector, decade range) in `frontend/src/lib/components/PopularityChart.svelte`
- [ ] T050 [P] [US3] Create NameDetail component (meaning, etymology, origin, variants, nicknames sections) in `frontend/src/lib/components/NameDetail.svelte`
- [ ] T051 [US3] Create name detail page with SSR for SEO in `frontend/src/routes/name/[id]/+page.svelte` and `+page.server.ts`
- [ ] T052 [US3] Wire name taps from NameCard, Leaderboard, and FavouriteButton to navigate to detail page
- [ ] T053 [US3] E2E test: navigate to name detail, verify all sections rendered, interact with chart in `frontend/tests/e2e/name-detail.spec.ts`

**Checkpoint**: Name detail pages work from any entry point. Popularity chart interactive. SSR working for SEO.

---

## Phase 6: User Story 4 — Favourite and Save Names (Priority: P2)

**Goal**: Users favourite names from any screen, add notes, view favourites list, use favourites as ranking input.

**Independent Test**: Favourite names from browse, leaderboard, and detail screens. View favourites list. Add/edit notes. Start ranking from favourites only.

### Tests for User Story 4

- [ ] T054 [P] [US4] Integration test for favourites CRUD endpoints in `backend/tests/integration/test_favourites_api.py`

### Implementation for User Story 4

- [ ] T055 [US4] Create Favourite model (add to `backend/babynames/db/models.py`) and migration
- [ ] T056 [US4] Implement favourites CRUD endpoints (GET, POST, DELETE, PATCH) in `backend/babynames/api/routes/favourites.py`
- [ ] T057 [US4] Add `is_favourite` and `user_note` fields to name list and detail API responses (augment when user is authenticated)
- [ ] T058 [P] [US4] Create FavouriteButton component (heart icon, toggle state, animation) in `frontend/src/lib/components/FavouriteButton.svelte`
- [ ] T059 [US4] Create favourites store with optimistic updates in `frontend/src/lib/stores/favourites.ts`
- [ ] T060 [US4] Create favourites page with note editing, "rank these" button in `frontend/src/routes/favourites/+page.svelte`
- [ ] T061 [US4] Integrate FavouriteButton into NameCard, NameDetail, and Leaderboard components
- [ ] T062 [US4] Wire "rank favourites" flow: favourites → rank page with favourites-only filter
- [ ] T063 [US4] E2E test: favourite from multiple screens, verify persistence, edit note, rank from favourites in `frontend/tests/e2e/favourites.spec.ts`

**Checkpoint**: Favourites work everywhere. Notes persist. Can rank from favourites list.

---

## Phase 7: User Story 5 — Collaborative Rating (Priority: P3)

**Goal**: Two+ participants rank independently, then view combined results showing strong matches and discussion points.

**Independent Test**: Two authenticated users rank the same names independently. View combined results. Strong matches and disagreements are clearly displayed.

### Tests for User Story 5

- [ ] T064 [P] [US5] Integration test for session creation, joining, and comparison endpoints in `backend/tests/integration/test_sessions_api.py`

### Implementation for User Story 5

- [ ] T065 [US5] Create CollaborativeSession and SessionParticipant models (add to `backend/babynames/db/models.py`) and migration
- [ ] T066 [US5] Implement session endpoints (POST create, POST join, GET compare) in `backend/babynames/api/routes/sessions.py`
- [ ] T067 [US5] Implement agreement scoring algorithm (overlap detection, strong match/discussion point classification) in `backend/babynames/ranking/collaboration.py`
- [ ] T068 [P] [US5] Create collaborative comparison view component (side-by-side rankings, match highlights, disagreement flags) in `frontend/src/lib/components/CompareView.svelte`
- [ ] T069 [US5] Create compare page with invite link sharing in `frontend/src/routes/compare/+page.svelte`
- [ ] T070 [US5] Add "invite partner" flow from leaderboard page
- [ ] T071 [US5] E2E test: create session, join as second user, rank independently, view combined results in `frontend/tests/e2e/collaboration.spec.ts`

**Checkpoint**: Full collaborative flow works end-to-end. Partners can rank independently and compare.

---

## Phase 8: User Story 6 — Save and Resume Progress (Priority: P2)

**Goal**: All user state persists server-side via Authentik identity. Resume on any device.

**Independent Test**: Create filters, run partial ranking, favourite names, close app, reopen — all state restored. Sign in on second device, verify same state.

*Note: Most persistence is already implemented by earlier phases (ranking state, favourites stored server-side). This phase covers remaining gaps and cross-device verification.*

### Implementation for User Story 6

- [ ] T072 [US6] Implement filter state persistence — save active filters to server on change in `backend/babynames/api/routes/preferences.py`
- [ ] T073 [US6] Create user preferences endpoint (GET/PUT) for filter presets and UI state in `backend/babynames/api/routes/preferences.py`
- [ ] T074 [US6] Restore filter state on app load from server in `frontend/src/lib/stores/names.ts`
- [ ] T075 [US6] Restore ranking session position on app load in `frontend/src/lib/stores/ranking.ts`
- [ ] T076 [US6] E2E test: create state, close browser, reopen, verify all state restored in `frontend/tests/e2e/persistence.spec.ts`

**Checkpoint**: Complete state persistence. Close app, reopen on any device, everything is exactly as left.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Visual polish, performance, accessibility, deployment readiness

- [ ] T077 [P] Responsive design audit and fixes across all pages — verify on mobile viewports (375px, 390px, 414px)
- [ ] T078 [P] Animation and transition polish — page transitions, card interactions, button feedback in Svelte transitions
- [ ] T079 [P] Accessibility audit — keyboard navigation, screen reader labels, colour contrast, focus indicators
- [ ] T080 [P] Performance optimisation — lazy loading, image optimisation, API response caching headers
- [ ] T081 Create Dockerfile for combined frontend+backend container in `Dockerfile`
- [ ] T082 Create kalevala Kubernetes manifests in `~/code/kalevala/k8s/babynames/` (Deployment, Service, InfisicalSecret, Ingress)
- [ ] T083 Create Authentik application and OAuth2 provider for babynames
- [ ] T084 Create PostgreSQL deployment or reference existing shared instance
- [ ] T085 [P] Update README.md with new architecture, setup instructions, and screenshots
- [ ] T086 Run quickstart.md validation — verify all setup steps work on clean environment

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — BLOCKS all user stories
- **Phase 3 (US1 Browse/Filter)**: Depends on Phase 2 — MVP target
- **Phase 4 (US2 Ranking)**: Depends on Phase 2. Benefits from Phase 3 (filter → rank flow) but can be developed in parallel
- **Phase 5 (US3 Name Detail)**: Depends on Phase 2. Independent of US1/US2 for core functionality
- **Phase 6 (US4 Favourites)**: Depends on Phase 2. Integrates with US1/US2/US3 components but core is independent
- **Phase 7 (US5 Collaboration)**: Depends on Phase 4 (requires ranking system)
- **Phase 8 (US6 Persistence)**: Depends on Phases 3–6 (fills gaps in existing persistence)
- **Phase 9 (Polish)**: Depends on all desired user stories being complete

### User Story Dependencies

- **US1 (Browse/Filter)**: Independent after Phase 2
- **US2 (Ranking)**: Independent after Phase 2. Integrates with US1 for filter→rank flow
- **US3 (Name Detail)**: Independent after Phase 2
- **US4 (Favourites)**: Independent after Phase 2. Integrates into US1/US2/US3 components
- **US5 (Collaboration)**: Requires US2 (ranking data to compare)
- **US6 (Persistence)**: Augments US1–US4

### Within Each User Story

- Tests first (written to fail)
- Backend models/endpoints before frontend
- Frontend components before page assembly
- Integration and E2E tests last

### Parallel Opportunities

- T002 + T003 + T004 + T005 + T006 (all setup tasks)
- T010 + T011 + T012 + T013 + T014 + T015 (all foundational infra)
- T017 + T019 + T020 (foundational tests)
- T021 + T022 + T023 (US1 tests)
- T026 + T027 (US1 frontend components)
- T033 + T034 (US2 tests)
- T040 + T041 (US2 frontend components)
- T049 + T050 (US3 frontend components)
- US3 + US4 can run in parallel (different endpoints, different components)

---

## Parallel Example: User Story 1

```bash
# Tests (parallel):
Task: "Integration test for GET /api/names in backend/tests/integration/test_names_api.py"
Task: "Integration test for GET /api/origins in backend/tests/integration/test_names_api.py"
Task: "Unit test for filter query builder in backend/tests/unit/test_filters.py"

# Frontend components (parallel, after backend endpoints):
Task: "Create FilterPanel component in frontend/src/lib/components/FilterPanel.svelte"
Task: "Create NameCard component in frontend/src/lib/components/NameCard.svelte"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1 (Browse/Filter)
4. **STOP and VALIDATE**: Test browsing and filtering independently
5. Complete Phase 4: User Story 2 (Ranking)
6. **STOP and VALIDATE**: Test full filter → rank → leaderboard flow
7. Deploy MVP

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. US1 (Browse/Filter) → Test → Deploy (MVP-alpha)
3. US2 (Ranking) → Test → Deploy (MVP)
4. US3 (Name Detail) + US4 (Favourites) → parallel → Test → Deploy
5. US5 (Collaboration) → Test → Deploy
6. US6 (Persistence gaps) → Test → Deploy
7. Polish → Final Deploy

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story
- Each user story independently completable and testable
- Commit after each task or logical group
- Use structured console logging (`logger.ts`) in all frontend components for Chrome extension debugging
- Use `read_console_messages` via Chrome extension to verify state after each frontend change
- Backend tests use pytest with a test PostgreSQL database
- Frontend E2E tests use Playwright
