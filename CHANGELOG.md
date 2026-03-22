# Changelog

All notable changes to this project are documented in this file. Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [2.1.0] - 2026-03-21

### Added

- **Swipe Mode** — Tinder-style card swiping to review names one at a time
  - Swipe right/left/up (or tap ♥/✗/★, or use arrow keys) for like/pass/maybe
  - Touch and mouse drag with physics-style rotation and color feedback
  - Multi-select variant chips on each card to pick preferred spellings
  - Scope selector ("How deep?") with time estimates per option and boundary name hint
  - Inline progress counters (♥ liked / ★ maybe) visible during swiping
  - Direction hints ("← Pass · Maybe ↑ · Like →") below action buttons
  - Progress bar, undo (↩ / Ctrl+Z), and mid-session "View picks so far"
  - Completion screen with summary, bounce animation, and share prompt
  - Escape key closes overlay
- **Multi-person sharing** — everyone is a peer, anyone can share and compare
  - "Share My Picks" generates a URL encoding name + liked/maybe ranks
  - "Add Someone's Picks" loads any number of other voters (partner, grandparents, friends)
  - Re-sharing gives updated picks; re-loading replaces the old data by name
  - N-way comparison groups names as "Everyone loves" / "Strong contenders" / "Worth discussing"
- **Session persistence** — picks saved to localStorage, keyed by deck content hash
  - Resume info on return ("340 reviewed · 12 liked · 5 maybe · 960 remaining")
  - Scope selection persisted across sessions
  - Start Fresh option to reset
  - localStorage warning on intro screen
- **Export/Import** — JSON backup with picks, other voters' data, deck version hash, and timestamp
  - Survives browser wipes, incognito mode, device changes
  - Import warns if data version has changed since export
- **Inline SVG favicon** (👶 emoji)
- **Open Graph meta tags** (og:title, og:description, og:image) and canonical URL
- **`.prettierignore`** to exclude data/raw/images from formatting

### Fixed

- **XSS vulnerability** in swipe comparison view — voter names from URL params were rendered via innerHTML; now uses safe textContent via DOM methods
- **Pages deployed entire 41MB repo** including raw/ SSA data — now builds a `_site/` directory with only web assets (~14MB)
- **generate.yml missing `permissions: contents: write`** — git push could silently fail
- **CRLF line endings** in 5 files (.editorconfig, test files) despite .editorconfig specifying LF
- **Empty card after returning from shortlist** — "← Back" now re-renders the current card instead of showing a stale exit-animation state
- **Progress overflow when reducing scope** — `reviewedCount()` now only counts ranks within the active deck, not globally
- **Rapid double-click on action buttons** — added debounce guard preventing the same card from being acted on twice within the 280ms animation window
- **URL-loaded voter picks discarded** — shared `#picks=` links were wiped by `loadSession()` on first open; now preserved and merged
- **Number formatting** — all counts now use `toLocaleString()` (e.g., "31,935" not "31935")

### Changed

- Card screen wrapped in max-width 440px centered container (fixes desktop/mobile layout)
- Card elevation with shadow (light and dark mode variants)
- Button press animation (`:active` scale) and colored glow on hover
- Screen fade transitions between swipe views
- Improved contrast across both themes: darker backgrounds, visible borders on all chips/toggles/buttons, `--muted-stronger` for interactive text, richer gender accent colors
- `swipe.js` modernized: 0 `var` (all `const`/`let`), arrow functions, template literals, `for...of`, destructuring, `SCREENS` array for screen management
- CDN versions verified as latest: Pico CSS 2.1.1, Tabulator 6.4.0, PapaParse 5.5.3

## [2.0.0] - 2026-03-21

Ground-up rewrite of the data pipeline, web viewer, and project infrastructure. **The CSV schema has changed** — see [Breaking Changes](#breaking-changes-200) below.

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

### Breaking Changes {#breaking-changes-200}

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
