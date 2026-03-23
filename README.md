# Baby Names

A tool to help parents find names for their newborns.

Names like Jonathan, Johnathan, Johnathon, Jonothan, and Jonathon are treated as alternative spellings of a single name — so you only review each distinct name once.

Uses publicly-available data from the US Social Security Administration (1880–2024), de-duplicated by phonetic pronunciation using the [CMU Pronouncing Dictionary](https://en.wikipedia.org/wiki/CMU_Pronouncing_Dictionary). Names not in the CMU dictionary get pronunciations from the [g2p_en](https://github.com/Kyubyong/g2p) neural model when available.

## How to Use

Browse names at [baby.dxdc.dev](https://baby.dxdc.dev/). You can filter by gender, popularity rank, syllable count, name length, peak decade, year range, starting letter, unisex share, spelling variants, and traits (biblical, trending, palindrome, alliteration). Filter state is saved in the URL for easy sharing. Dark mode available.

**Swipe Mode** (♥ button) lets you review names one at a time — swipe right to like, left to pass, up for maybe. Share your picks with a partner and compare to find names you both love.

The compiled datasets are also available for download:

- [all-names.csv](data/all-names.csv), [boys.csv](data/boys.csv), [girls.csv](data/girls.csv)

### How Many Names Should I Review?

A few thousand is probably enough to cover the "normal" range — roughly 90–95% of all babies born. Unless you're specifically looking for something unusual, that's plenty.

![Baby Name Distribution](/images/graph.png?raw=true "Baby Name Distribution")

Boys' names are more concentrated (fewer names to reach 90%), while girls' names are more spread out. Either way, 2,000–3,000 names covers the vast majority.

### CSV Columns

| Header             | Description                                                                   |
| ------------------ | ----------------------------------------------------------------------------- |
| rank               | Popularity rank within gender                                                 |
| name               | Baby name (most popular spelling)                                             |
| spelling_variants  | Alternative spellings with the same pronunciation, sorted by popularity       |
| total_count        | Total babies born with this name (includes alternate spellings)               |
| cumulative_pct     | Cumulative percentage of babies born with this name (includes higher rows)    |
| year_min           | First year this name appears in SSA data                                      |
| year_max           | Last year this name appears                                                   |
| year_peak          | Year with the highest single-year count (for the primary spelling)            |
| biblical           | Biblical category: Person, Place, God, or Other; empty if not biblical        |
| is_palindrome      | Reads the same forwards and backwards (1 = yes)                               |
| pronunciations     | ARPABET phonetic pronunciations, pipe-separated                               |
| first_letter       | First letter                                                                  |
| stresses           | Lexical stress pattern (0=unstressed, 1=primary, 2=secondary)                 |
| syllables          | Number of syllables                                                           |
| alliteration       | Contains any repeated phoneme (1 = yes)                                       |
| alliteration_first | First phoneme repeats later (1 = yes)                                         |
| unisex_pct         | Minority gender share as % (0–50, where 50 = balanced); null if single-gender |
| unisex_dominant    | Dominant gender (M or F); null if single-gender                               |
| nickname_of        | Formal name(s) this is a nickname for (e.g., Matt → Matthew); null if none    |
| nicknames          | Known nicknames for this name that exist in the data; null if none            |

## About

Baby books are outdated — mostly name lists with no context for popularity, spelling variations, or historical trends. This project fills that gap.

## Development

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Setup

```bash
# Using uv (recommended)
uv venv && source .venv/bin/activate
uv pip install -e ".[dev,g2p]"

# Or plain pip
python -m venv .venv && source .venv/bin/activate
pip install polars cmudict g2p-en pytest ruff
```

The `g2p-en` package is optional but recommended — it provides pronunciations for names not in the CMU dictionary (e.g., Jaxson, Khloe). Without it, the pipeline falls back to subword-splitting.

### Regenerating CSV Files

```bash
python src/babynames.py --verbose
```

Writes `boys.csv`, `girls.csv`, and `all-names.csv` to `data/`.

Options: `--data-dir`, `--biblical`, `--output-dir`, `--forced-merges`, `--pronunciation-overrides`, `--nicknames`, `--territory-dir`.

### Regenerating the Graph

```bash
pip install matplotlib
python images/generate_graph.py
```

### Running Tests

```bash
pytest tests/ -v
```

### Linting

```bash
ruff check src/ tests/
ruff format src/ tests/
```

### Local Web Viewer

The viewer loads CSVs via HTTP, so you need a server:

```bash
python -m http.server 8000
# open http://localhost:8000
```

### Stack

[Pico CSS](https://picocss.com/) + [Tabulator](https://tabulator.info/) + [Papa Parse](https://papaparse.com/), all from CDN. No build step.

### Project Structure

```
├── index.html              # Web UI
├── grid.js                 # Table, filtering, URL state
├── swipe.js                # Swipe mode
├── manifest.json           # PWA manifest
├── raw/                    # SSA source files, biblical names, merge overrides
├── data/                   # Generated CSVs
├── src/babynames.py        # Data pipeline
├── tests/                  # Test suite
├── images/                 # Graph + generation script
└── .github/workflows/      # CI, data generation, Pages deploy
```

## CI/CD

- **CI** — Linting (ruff), tests (pytest), format checks (prettier) on push/PR.
- **Generate Data** — Regenerates CSVs and graph when `src/`, `raw/`, or graph script changes. Auto-commits.
- **Deploy Pages** — Deploys to GitHub Pages when web assets or CSVs change. Also triggers after successful data generation.

## Datasets

- **SSA Baby Names** (`raw/yob*.txt`): Children of each sex given each name, per year, 1880–2024. All names with 5+ uses included. ([Source](https://www.ssa.gov/oact/babynames/limits.html))
- **Biblical Names** (`raw/biblical_names.csv`): Categorized list of biblical names (Person, Place, God, Other).
- **Forced Merges** (`raw/forced_merges.csv`): Manual spelling group overrides for names the phonetic algorithm splits incorrectly (e.g., Kaitlyn/Katelyn/Caitlin).
- **Pronunciation Overrides** (`raw/pronunciation_overrides.csv`): Corrections for CMU dictionary entries that cause incorrect groupings (e.g., Jere ≠ Jerry).
- **Nicknames** (`raw/nicknames.csv`): Curated nickname → formal name mappings (e.g., Matt → Matthew) with gender column (M/F) so mappings only apply within the correct gender. Informational only — counts stay separate.
- **Territory Names** (`raw/territories/`): SSA baby name data for US territories (Puerto Rico, Guam, American Samoa, etc.). ([Source](https://www.ssa.gov/oact/babynames/territory/namesbyterritory.zip))

## Contributing

1. Fork → feature branch → make changes
2. `pytest tests/ -v` to verify
3. `ruff check src/ tests/ && ruff format src/ tests/` to lint
4. Open a PR

### Updating SSA Data

When new data drops (usually May):

1. Download `names.zip` from [SSA](https://www.ssa.gov/oact/babynames/limits.html)
2. Extract the new `yobYYYY.txt` into `raw/`
3. Push to main — the Generate Data workflow handles the rest

## Credits

A huge thank you to our little :star2: who is the inspiration behind this repository.

## Support this project

- Star and share the project :rocket:
- [![PayPal][badge_paypal]][paypal-donations-dxdc] **PayPal**
- **Venmo**
  ![Venmo QR Code](/images/venmo.png?raw=true "Venmo QR Code")
- **Bitcoin**: `33sT6xw3tZWAdP2oL4ygbH5TVpVMfk9VW7`

[badge_paypal]: https://img.shields.io/badge/Donate-PayPal-blue.svg
[paypal-donations-dxdc]: https://paypal.me/ddcaspi
