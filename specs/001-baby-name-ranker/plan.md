# Implementation Plan: Baby Name Discovery & Ranking App

**Branch**: `001-baby-name-ranker` | **Date**: 2026-03-31 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-baby-name-ranker/spec.md`

## Summary

A web app for parents, family, and friends to discover and rank baby names from a large database. Users filter names by origin, popularity, era, and culture; rank them through pairwise comparisons with cumulative Glicko-2 scoring; explore detailed name profiles; favourite and annotate names; and collaborate with partners to find shared preferences. Authentication via Authentik SSO, server-side persistence, colourful mobile-first UI.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript/Svelte 5 (frontend)
**Primary Dependencies**: FastAPI, SvelteKit, Tailwind CSS, Glicko-2 (ported)
**Storage**: PostgreSQL 16
**Testing**: pytest (backend), Vitest (frontend unit), Playwright (E2E), structured console logging
**Target Platform**: Web (mobile-responsive, mobile-first design)
**Project Type**: Web application (SPA with SSR for SEO on name detail pages)
**Performance Goals**: Filter results in <1s, name detail load <2s, 50+ concurrent users
**Constraints**: Must work well on mobile (3G+), colourful/fun/guided UI, Authentik SSO
**Scale/Scope**: ~99k names (US SSA), ~20k with enrichment data, <100 concurrent users initially

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution is unpopulated (template defaults). No gates to evaluate. Proceeding.

**Post-design re-check**: No violations. Project uses 2 deployable units (frontend + backend in single container), standard patterns, no unnecessary abstractions.

## Project Structure

### Documentation (this feature)

```text
specs/001-baby-name-ranker/
├── plan.md              # This file
├── research.md          # Phase 0 output — technology decisions
├── data-model.md        # Phase 1 output — entity definitions
├── quickstart.md        # Phase 1 output — dev setup guide
├── contracts/
│   └── api.md           # Phase 1 output — API contract
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
backend/
├── babynames/
│   ├── api/
│   │   ├── main.py          # FastAPI app, CORS, middleware
│   │   ├── auth.py          # Authentik JWT validation
│   │   ├── routes/
│   │   │   ├── names.py     # Name browsing, filtering, detail
│   │   │   ├── ranking.py   # Pairwise comparison, leaderboard
│   │   │   ├── favourites.py
│   │   │   └── sessions.py  # Collaborative sessions
│   │   └── deps.py          # Shared dependencies (db, auth)
│   ├── db/
│   │   ├── models.py        # SQLAlchemy models
│   │   ├── seed.py          # CSV → PostgreSQL loader
│   │   └── migrations/      # Alembic migrations
│   ├── ranking/
│   │   └── glicko2.py       # Glicko-2 algorithm (ported from JS)
│   └── logging.py           # Structured logging setup
├── tests/
│   ├── unit/
│   │   ├── test_glicko2.py
│   │   └── test_filters.py
│   ├── integration/
│   │   ├── test_names_api.py
│   │   ├── test_ranking_api.py
│   │   └── test_auth.py
│   └── conftest.py
├── pyproject.toml
└── alembic.ini

frontend/
├── src/
│   ├── lib/
│   │   ├── components/
│   │   │   ├── NameCard.svelte       # Name display card
│   │   │   ├── FilterPanel.svelte    # Filter controls
│   │   │   ├── BattleView.svelte     # Pairwise comparison
│   │   │   ├── Leaderboard.svelte    # Ranking results
│   │   │   ├── NameDetail.svelte     # Full name profile
│   │   │   ├── FavouriteButton.svelte
│   │   │   └── PopularityChart.svelte
│   │   ├── stores/
│   │   │   ├── auth.ts               # Authentik OIDC state
│   │   │   ├── names.ts              # Name data + filters
│   │   │   ├── ranking.ts            # Ranking session state
│   │   │   └── favourites.ts         # Favourites state
│   │   ├── api/
│   │   │   └── client.ts             # Typed API client
│   │   ├── design/
│   │   │   └── tokens.css            # Design tokens (colours, spacing, typography)
│   │   └── utils/
│   │       └── logger.ts             # Structured console logging
│   ├── routes/
│   │   ├── +layout.svelte            # App shell, nav, auth wrapper
│   │   ├── +page.svelte              # Home → guided flow entry
│   │   ├── browse/+page.svelte       # Filter + browse names
│   │   ├── rank/+page.svelte         # Pairwise ranking
│   │   ├── leaderboard/+page.svelte  # Cumulative leaderboard
│   │   ├── name/[id]/+page.svelte    # Name detail (SSR for SEO)
│   │   ├── favourites/+page.svelte   # Favourites list
│   │   └── compare/+page.svelte      # Collaborative comparison
│   └── app.html
├── tests/
│   ├── unit/
│   └── e2e/
├── svelte.config.js
├── tailwind.config.js
├── vite.config.ts
├── package.json
└── playwright.config.ts

# Existing (preserved)
src/babynames.py          # Data pipeline (unchanged)
raw/                      # Source data files (unchanged)
data/                     # Generated CSVs (unchanged)
scripts/                  # Enrichment scripts (unchanged)
tests/                    # Existing pipeline tests (unchanged)
```

**Structure Decision**: Separate `backend/` and `frontend/` directories at repo root. Existing data pipeline (`src/`, `raw/`, `data/`, `scripts/`, `tests/`) preserved untouched — the new backend reads from the same CSVs via the seed script. Single Docker container for deployment.

## Complexity Tracking

No constitution violations to justify.
