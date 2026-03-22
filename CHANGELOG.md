# Changelog

All notable changes to this project are documented in this file. Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [2.1.0] - 2026-03-22

Swipe mode for couples, sharing, and a bunch of polish.

### Swipe Mode

New full-screen overlay for reviewing names one at a time — swipe right to like, left to pass, up for maybe. Works with touch drag, mouse drag, tap buttons, or arrow keys.

- Choose how deep to go before starting (Top 100 / 500 / 1000 / All) with time estimates
- Multi-select spelling variants on each card (tap to toggle preferred spellings)
- Card badges for quick visual ID: 📖 Biblical (category), 📈 Trending, 🕰️ Classic, ⚤ Unisex, 🔁 Palindrome, 🔤 Alliteration
- Progress bar with running ♥/★ counts, undo (Ctrl+Z), Escape to close
- Swipe down to dismiss on mobile
- Simplified intro screen — just pick scope, enter name, go
- Session auto-saved to localStorage; resume where you left off

### Sharing & Comparison

Everyone is a peer — no "host" or "admin." Anyone can share at any time.

- **Share My Picks**: generates a URL with your name, gender, and liked/maybe ranks
- **Add Someone's Picks**: paste a link to load a partner's, grandparent's, or friend's picks
- **Comparison view**: groups matches as "Everyone loves" / "Strong contenders" / "Worth discussing"
- **Individual voter details**: expandable section showing each person's picks with remove button
- Gender validation: warns if someone shared boys picks but you're viewing girls
- Self-import protection: won't add your own picks as another voter
- Export to CSV (opens in Excel/Sheets), import from CSV or JSON
- Share as image: generates a PNG with your picks for texting

### Web UI

- Custom domain: `baby.dxdc.dev`
- Custom OG image for social sharing previews (Twitter Card, JSON-LD structured data)
- Nav with inline SVG icons (GitHub, download arrows), footer with source/feedback/donate links
- PWA manifest for "Add to Home Screen" on mobile
- Mobile table hides overflow columns cleanly instead of collapsing into sub-rows
- Improved contrast in light/dark mode (visible borders, darker chip backgrounds, stronger muted text)
- Card shadow, button press/glow animations, screen fade transitions, completion bounce
- Year filter input disabled until a mode is selected
- Cache-busting version param on CSV URLs
- Screen reader announcements for card changes, actions, and completion

### Pipeline

- Forced spelling merges (`raw/forced_merges.csv`) — 180 manual overrides for names the phonetic algorithm splits incorrectly (Kaitlyn/Katelyn/Caitlin, Caleb/Kaleb, Brooklyn/Brooklynn, etc.)
- Biblical names now categorized: Person, Place, God, Other (was boolean). Shows category in table and swipe card badges.
- Expanded biblical names list with missing entries (Elizabeth, Timothy, Ethan, Elijah, etc.) and BibleNLP cross-reference
- Excluded junk names from SSA data: Unknown, Baby, Infant, Male, Female, Boy, Girl, Notnamed, Unnamed
- Unisex recency cutoff derived from data (`max_year - 50`) instead of hardcoded 1970

### Infrastructure

- `biblical` CSV column changed from `1`/empty to category string: `Person`, `Place`, `God`, `Other`, or empty
- Pages workflow deploys only `_site/` directory (was shipping entire 41MB repo)
- Generate workflow queues instead of cancelling on rapid pushes
- Pages auto-redeploys after successful data generation
- Added `permissions: contents: write` to generate workflow
- Fixed CRLF line endings in test files
- Added `.prettierignore` for data/raw/images

## [2.0.0] - 2026-03-21

Ground-up rewrite of the data pipeline, web viewer, and project infrastructure. **The CSV schema has changed** — see [Breaking Changes (v2.0)](#breaking-changes-v20) below.

### Added

- **12 interactive filters** with URL hash state for shareable links: gender, name search, rank, syllables, name length, peak decade, year filter (4 modes), starting letter (multi-select), unisex threshold, variants, and traits (biblical, trending, palindrome, alliteration)
- **Virtual scrolling** through all ~39k boys / ~60k girls names (Tabulator virtual DOM)
- **Dark mode** with full theme persistence
- **Gender-aware accent colors** — blue for boys, pink for girls across all UI controls
- **Data info bar** — shows loaded gender, name count, and year range
- **Polars-based pipeline** replacing pandas/swifter for faster processing
- **Best-cluster pronunciation grouping** — prevents multi-pronunciation names from bridging unrelated families
- **g2p_en neural model** (optional) — pronounces names not in CMU dict; used for display/syllables only, not grouping
- **Spelling-based syllable fallback** for names without any pronunciation
- **`unisex_pct`** — minority gender share (0–50%) replacing the old boolean flag
- **`unisex_dominant`** — which gender is dominant (M/F)
- **`is_palindrome`**, **`alliteration`** (any repeated phoneme), **`alliteration_first`** columns
- **Spelling variants sorted by popularity** (most common first), truncated in UI with tooltip
- **GitHub Actions CI/CD** — linting, tests, auto-regeneration of CSVs/graph, auto-deploy to Pages
- **57-test suite** covering pipeline, phonetics, and output validation
- **Distribution graph** auto-generated with 90%/95% threshold annotations
- **SSA data through 2024**

### Changed

- Web UI: Bootstrap + Grid.js → Pico CSS + Tabulator 6.4
- Pipeline: pandas/pronouncing → Polars + direct cmudict with subword splitting
- Trending filter is now relative (last 15 years of data) instead of hardcoded
- Year filter simplified to single dropdown with four clear modes
- `pyproject.toml` replaces `requirements.txt`
- Web viewer moved from `docs/` to project root
- CSVs moved from project root to `data/`
- Source data moved from `src/data/babynames/` to `raw/`

### Breaking Changes (v2.0)

**CSV columns** — every column has been renamed or restructured:

| v1.x                 | v2.0                | Notes                                                                             |
| -------------------- | ------------------- | --------------------------------------------------------------------------------- |
| `rank`               | `rank`              | Now integer (was float `1.0`)                                                     |
| `alt_spellings`      | `spelling_variants` | Sorted by popularity (was alphabetical)                                           |
| `n_sum`              | `total_count`       | Renamed                                                                           |
| `n_percent`          | `cumulative_pct`    | Renamed                                                                           |
| `year_pop`           | `year_peak`         | Renamed                                                                           |
| `palindrome`         | `is_palindrome`     | Renamed                                                                           |
| `phones`             | `pronunciations`    | Pipe-separated ARPABET (was Python list repr)                                     |
| `stresses`           | `stresses`          | Pipe-separated (was Python list repr)                                             |
| `alliteration_first` | `alliteration`      | Broadened to any repeated phoneme; old behavior preserved as `alliteration_first` |
| `unisex`             | `unisex_pct`        | Minority share 0–50% (was boolean); see also new `unisex_dominant`                |

**File layout:**

| v1.x                              | v2.0                              |
| --------------------------------- | --------------------------------- |
| `boys.csv`, `girls.csv`           | `data/boys.csv`, `data/girls.csv` |
| `docs/index.html`, `docs/grid.js` | `index.html`, `grid.js`           |
| `src/data/babynames/yob*.txt`     | `raw/yob*.txt`                    |
| `src/requirements.txt`            | `pyproject.toml`                  |

**Dependencies:** pandas/swifter/numpy/pronouncing → polars/cmudict/g2p-en (optional). Grid.js/Bootstrap → Tabulator/Pico CSS/PapaParse.

### Removed

- Grid.js, Bootstrap, pandas, swifter, pronouncing, `docs/` directory, `requirements.txt`

## [1.0.2] - 2024-08-05

- Updated SSA data through 2023
- Updated dependencies

## [1.0.1] - 2023-06-27

- Added palindrome detection column
- Switched to dense ranking method
- Updated SSA data through 2022

## [1.0.0] - 2022-06-28

- Initial release with HTML grid viewer (Grid.js + Bootstrap)
- Phonetic deduplication via CMU Pronouncing Dictionary
- CSV output with rank, name, alternate spellings, counts, year range, biblical flag, pronunciations, syllables, alliteration, and unisex flag
- SSA data through 2021

[2.1.0]: https://github.com/dxdc/babynames/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/dxdc/babynames/compare/v1.0.2...v2.0.0
[1.0.2]: https://github.com/dxdc/babynames/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/dxdc/babynames/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/dxdc/babynames/releases/tag/v1.0.0
