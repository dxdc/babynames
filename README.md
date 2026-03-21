# Baby Names

A tool to help parents find names for their newborns.

Names like Jonathan, Johnathan, Johnathon, Jonothan, and Jonathon are treated as alternative spellings of a single name — so you only review each distinct name once.

Using publicly-available datasets from the United States Social Security Administration, baby names from 1880 to 2024 were collated, de-duplicated by phonetic pronunciation using the [CMU Pronouncing Dictionary](https://en.wikipedia.org/wiki/CMU_Pronouncing_Dictionary), and ordered by popularity.

## How to Use

Browse the data using the [interactive web viewer](https://dxdc.github.io/babynames/), which supports filtering by:

- **Gender** — boys or girls
- **Name search** — case-insensitive substring match (also searches spelling variants)
- **Rank** — top 100, 500, 1,000, or 5,000
- **Syllable count** — 1, 2, 3, or 4+
- **Name length** — short (≤4 chars), medium (5–6), or long (≥7); matches if any spelling (primary or variant) fits
- **Peak decade** — when the name was most popular (2020s, 2010s, … 1940s & earlier)
- **Year filter** — single dropdown with clear modes: "Appeared after" (modern names), "Appeared before" (vintage names), "Retired before" (extinct names), "Still used after" (active names)
- **Starting letter** — A through Z (multi-select: click several letters to combine)
- **Unisex** — dropdown to filter by minority gender share (≥5%, ≥10%, ≥20%, ≥30%, ≥40%); the Unisex column shows the percentage and dominant gender (♂/♀)
- **Variants** — dropdown to filter names that have or don't have alternate spellings
- **Traits** — Biblical, Trending (peaked within last 15 years), Palindrome, and Alliteration toggles

Filter states are saved in the URL hash for easy sharing. Dark mode is also available.

The compiled datasets are also available for download:

- [all-names.csv](data/all-names.csv), [boys.csv](data/boys.csv), [girls.csv](data/girls.csv)

### How Many Names Should I Review?

Reviewing a few thousand names is probably sufficient to find one that is relatively "normal", and encompasses 90–95% of the most common names. Unless you happen to be looking for a highly unique or specific name, that is a very reasonable number of options for review.

![Baby Name Distribution](/images/graph.png?raw=true "Baby Name Distribution")

As the chart shows, boys' names are more concentrated (775 names covers 90%), while girls' names are more diverse (1,834 names to reach 90%). In either case, reviewing roughly 2,000–3,000 names covers the vast majority.

### CSV Columns

| Header             | Description                                                                                            |
| ------------------ | ------------------------------------------------------------------------------------------------------ |
| rank               | Popularity rank (1880–2024)                                                                            |
| name               | Baby name (most popular spelling)                                                                      |
| spelling_variants  | Alternative spellings with the same pronunciation, separated by spaces                                 |
| total_count        | Total babies born in the US with this name (includes alternate spellings)                              |
| cumulative_pct     | Cumulative percentage of babies born with this name (includes higher rows)                             |
| year_min           | Year this name was first used                                                                          |
| year_max           | Year this name was last used                                                                           |
| year_peak          | Most popular year for this name                                                                        |
| biblical           | Biblical name (1 = yes)                                                                                |
| is_palindrome      | Name reads the same forwards and backwards (1 = yes)                                                   |
| pronunciations     | ARPABET phonetic pronunciations, separated by `\|` for multiple variants                               |
| first_letter       | First letter of the name                                                                               |
| stresses           | Lexical stress pattern (0=unstressed, 1=primary, 2=secondary), separated by `\|` for multiple variants |
| syllables          | Number of syllables                                                                                    |
| alliteration       | Name contains any repeated phoneme (1 = yes)                                                           |
| alliteration_first | First phoneme repeats later in the name (1 = yes)                                                      |
| unisex_pct         | Minority gender share as % of total (0–50, where 50 = perfectly balanced); null if single-gender       |
| unisex_dominant    | Dominant gender for the name (M or F); null if single-gender                                           |

## About

Baby books are outdated — mostly name lists with no context for popularity, spelling variations, or historical trends. This project was created to fill that gap.

## Development

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Setup

Using uv (recommended):

```bash
uv venv
source .venv/bin/activate   # Linux/macOS
uv pip install -e ".[dev]"  # or: uv pip install polars cmudict g2p-en pytest ruff
```

Using pip:

```bash
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
pip install polars cmudict g2p-en pytest ruff
```

The `g2p-en` package is optional but recommended — it provides a neural model for pronouncing names not found in the CMU dictionary (e.g., Jaxson, Khloe). Without it, the pipeline falls back to a subword-splitting heuristic.

### Regenerating CSV Files

The CSV files in `data/` are generated from the source data in `raw/`. To regenerate:

```bash
python src/babynames.py --verbose
```

This writes `boys.csv`, `girls.csv`, and `all-names.csv` to `data/`.

### Regenerating the Distribution Graph

The graph in the README is generated from the CSV data. To regenerate after updating CSVs:

```bash
pip install matplotlib   # if not already installed
python images/generate_graph.py
```

This reads `data/boys.csv` and `data/girls.csv` and writes `images/graph.png`. The script automatically detects the year range from the data.

### Running Tests

```bash
pytest tests/ -v
```

### Linting & Formatting

```bash
ruff check src/ tests/
ruff format src/ tests/
```

### Viewing the Web UI Locally

The web viewer loads CSV files via HTTP, so opening `index.html` directly from the filesystem won't work. Use a local server:

```bash
python -m http.server 8000
# then open http://localhost:8000
```

### Web Viewer

The web viewer (`index.html`) uses [Pico CSS](https://picocss.com/) for styling, [Tabulator](https://tabulator.info/) for the data grid, and [Papa Parse](https://papaparse.com/) for CSV parsing — all loaded from CDN with no build step required.

### Project Structure

```
├── index.html              # Web UI entry point
├── grid.js                 # Web UI logic (filtering, table, URL state)
├── images/
│   ├── generate_graph.py   # Script to regenerate the distribution chart
│   └── graph.png           # Cumulative name distribution chart
├── raw/                    # Input data (SSA files + reference data)
│   ├── yob1880.txt … yob2024.txt  # SSA baby name files
│   └── biblical_names.csv  # Curated biblical name list
├── data/                   # Generated output CSVs
│   ├── boys.csv
│   ├── girls.csv
│   └── all-names.csv
├── src/
│   └── babynames.py        # Data processing pipeline
├── tests/                  # Test suite
├── .github/workflows/      # CI, CSV generation, GitHub Pages deployment
└── pyproject.toml          # Python project config
```

## CI/CD

Three GitHub Actions workflows handle automation:

- **CI** (`ci.yml`) — Runs linting (ruff), tests (pytest), and format checks (prettier) on every push and PR to main.
- **Generate CSVs** (`generate.yml`) — Regenerates CSV files when `src/` or `raw/` changes on main, and auto-commits the result.
- **Deploy Pages** (`pages.yml`) — Deploys to GitHub Pages when web assets or CSV files change on main.

## Datasets

This project uses two datasets (both in `raw/`):

- **SSA Baby Names** (`raw/yob*.txt`): For each year from 1880 to 2024, the number of children of each sex given each name. All names with more than 5 uses are given. (Source: [SSA Baby Names](https://www.ssa.gov/oact/babynames/limits.html))

- **Biblical Names** (`raw/biblical_names.csv`): A curated, de-duplicated collection of biblical names.

## How to Contribute

Have an idea? Found a bug? Contributions and pull requests are welcome.

1. Fork the repository
2. Create a feature branch: `git checkout -b my-feature`
3. Set up your development environment (see [Development](#development))
4. Make your changes and run `pytest tests/ -v` to verify
5. Run `ruff check src/ tests/ && ruff format src/ tests/` to lint and format
6. Commit your changes and open a pull request

### Updating SSA Data

When new SSA data is released (typically in May each year):

1. Download the latest `names.zip` from the [SSA Baby Names](https://www.ssa.gov/oact/babynames/limits.html) page
2. Extract the new `yobYYYY.txt` file(s) into `raw/`
3. Regenerate the CSVs: `python src/babynames.py --verbose`
4. Regenerate the graph: `python images/generate_graph.py`
5. Verify results and commit

## Credits

A huge thank you to our little :star2: who is the inspiration behind this repository.

## Support this project

I try to reply to everyone needing help using these projects. Obviously, this takes time. However, if you get some profit from this or just want to encourage me to continue creating stuff, there are few ways you can do it:

- Starring and sharing the projects you like :rocket:
- [![PayPal][badge_paypal]][paypal-donations-dxdc] **PayPal**— You can make one-time donations to **dxdc** via PayPal.
- **Venmo**— You can make one-time donations via Venmo.
  ![Venmo QR Code](/images/venmo.png?raw=true "Venmo QR Code")
- **Bitcoin**— You can send me Bitcoin at this address: `33sT6xw3tZWAdP2oL4ygbH5TVpVMfk9VW7`

[badge_paypal]: https://img.shields.io/badge/Donate-PayPal-blue.svg
[paypal-donations-dxdc]: https://paypal.me/ddcaspi
