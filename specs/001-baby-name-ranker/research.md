# Research: Baby Name Discovery & Ranking App

## Decision 1: Frontend Framework

**Decision**: SvelteKit (Svelte 5) with Vite

**Rationale**: The existing codebase is vanilla JS with IIFE modules — no framework, no build step, no component model. The new app needs: routing, state management, reactive UI, component reuse, and a mobile-first guided flow. Svelte produces minimal JS bundles (important for mobile performance), has built-in transitions/animations (important for the playful UI), and SvelteKit provides SSR/routing out of the box. The existing code is being replaced, not incrementally migrated, so framework choice is unconstrained.

**Alternatives considered**:
- React/Next.js: Heavier runtime, more boilerplate for a consumer app of this size
- Vue/Nuxt: Good option but Svelte's smaller bundle and built-in animations better suit the mobile-first, playful requirement
- Vanilla JS (keep current): Would require building routing, state, components from scratch — not worth it for the scope

## Decision 2: Backend Architecture

**Decision**: Keep FastAPI (Python), replace SQLite with PostgreSQL, add Authentik OIDC integration

**Rationale**: FastAPI is already in the codebase and handles the API pattern well. PostgreSQL supports the richer data model (names, origins, meanings, user state, rankings) and concurrent access better than SQLite. The existing data pipeline is Python (Polars), so keeping the backend in Python means the enrichment pipeline and API share a language. Authentik provides OIDC — the backend validates JWT tokens from Authentik.

**Alternatives considered**:
- Go backend: Faster runtime but Python is already established, data pipeline is Python, and FastAPI performance is adequate for this scale
- Keep SQLite: Doesn't support concurrent writes well enough for multi-user collaborative features
- Supabase/Firebase: Adds external dependency; we already have infrastructure

## Decision 3: Name Data Storage

**Decision**: Pre-process enriched CSVs into PostgreSQL at build/deploy time. Serve name data via API endpoints, not raw CSV loading in the browser.

**Rationale**: Current approach loads full CSVs client-side (99k rows via Papa Parse). This is slow on mobile and makes filtering/searching happen in JS. Moving to server-side filtering with paginated API responses dramatically improves mobile performance and enables richer queries (join names with origins, meanings, popularity records). The existing Python pipeline already generates the CSVs — we add a load step that imports them into PostgreSQL.

**Alternatives considered**:
- Keep client-side CSV: Poor mobile performance with 99k rows, can't join enrichment data efficiently
- Pre-built JSON bundles: Better than CSV but still loads everything client-side
- Search engine (Meilisearch/Typesense): Good for search but overkill — PostgreSQL full-text search + indexes are sufficient

## Decision 4: Ranking Algorithm

**Decision**: Adapt existing Glicko-2 implementation. Cumulative leaderboard across rounds.

**Rationale**: Glicko-2 is already implemented and well-suited: it tracks rating confidence (RD), so names with fewer comparisons naturally show as "less settled" in the leaderboard. When a new round introduces names that haven't been compared yet, they start with high RD and get refined. The cumulative model works naturally with Glicko-2's design. Port the core algorithm from the IIFE JS module to a shared utility.

**Alternatives considered**:
- ELO: Simpler but no confidence tracking — can't show users which rankings are "settled" vs "uncertain"
- TrueSkill: Microsoft's Bayesian system, more complex than needed for 1v1 comparisons
- Simple win/loss counting: Too noisy, doesn't converge well

## Decision 5: UI Design System

**Decision**: Custom design tokens + Tailwind CSS. No off-the-shelf component library. Colourful, mobile-first, guided-flow design.

**Rationale**: The spec explicitly rejects generic UI. Off-the-shelf component libraries (Material, Shadcn, etc.) produce recognisable "template" aesthetics. A custom design system with Tailwind utility classes gives full control over the playful, opinionated visual identity. Svelte's built-in transitions handle animations. Design tokens (colours, spacing, typography) ensure consistency without a heavy framework.

**Alternatives considered**:
- Pico CSS (current): Too minimal, no component model, not playful enough
- Material/Shadcn/Radix: Too corporate/generic — user explicitly wants colourful and fun
- Skeleton UI (Svelte): Better than generic but still constrains visual identity

## Decision 6: Testing Strategy

**Decision**: Vitest (unit/integration) + Playwright (E2E) + structured console logging for Chrome extension verification

**Rationale**: Vitest is the natural test runner for Vite/SvelteKit projects. Playwright handles E2E browser testing. Structured console logging (JSON format with levels, component tags) enables the Claude Chrome extension to read and verify application state via `read_console_messages`. This creates a fast feedback loop: make change → verify in browser → read console → fix.

**Alternatives considered**:
- Jest: Works but Vitest is faster and natively supports ESM/Vite
- Cypress: Good E2E but Playwright is faster and better for CI
- No structured logging: Would make Chrome extension verification much harder

## Decision 7: Deployment

**Decision**: Container image → GHCR → kalevala manifest → ArgoCD. SvelteKit builds to Node adapter. FastAPI serves API. Nginx or Caddy reverse proxy in the container.

**Rationale**: Follows the standard deployment pipeline already established. Single container with both frontend (static assets from SvelteKit build) and backend (FastAPI/Uvicorn). PostgreSQL runs as a separate service in the cluster.

**Alternatives considered**:
- Separate frontend/backend containers: More complexity for marginal benefit at this scale
- Static site + API: SvelteKit can do this but we need SSR for SEO (name detail pages should be crawlable)
- Vercel/Cloudflare Pages: External hosting when we have infrastructure already
