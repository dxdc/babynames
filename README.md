# baby names

A tool to help parents find names for their newborns.

Names like Jonathan, Johnathan, Johnathon, Jonothan, and Jonathon are treated as alternative spellings of a single name — so you only review each distinct name once.

Using publicly-available datasets from the United States Social Security Administration, baby names from 1880 to 2023 were collated, de-duplicated by phonetic pronunciation using the [CMU Pronouncing Dictionary](https://en.wikipedia.org/wiki/CMU_Pronouncing_Dictionary), and ordered by popularity.

## How to Use

Browse the data using the [interactive web viewer](https://dxdc.github.io/babynames/), which supports filtering by:

- **Gender** — boys or girls
- **Name search** — case-insensitive substring match
- **Rank** — top 100, 500, 1,000, or 5,000
- **Syllable count** — 1, 2, 3, or 4+
- **Year range** — "Active After" / "Active Before" (overlap-based, so classic names aren't excluded)
- **Starting letter** — A through Z
- **Biblical** and **Unisex** toggles

Filter states are saved in the URL hash for easy sharing. Dark mode is also available.

The compiled datasets are also available for download:

- [all-names.csv](all-names.csv), [boys.csv](boys.csv), [girls.csv](girls.csv)

Recommendation: Review the list from top to bottom, applying any filters you wish. A few thousand names covers 90-95% of the most common names.

### CSV Columns

| Header             | Description                                                                                               |
| ------------------ | --------------------------------------------------------------------------------------------------------- |
| rank               | Popularity rank (1880-2023)                                                                               |
| name               | Baby name (most popular spelling)                                                                         |
| spelling_variants  | Alternative spellings with the same pronunciation, separated by spaces                                    |
| total_count        | Total babies born in the US with this name (includes alternate spellings)                                 |
| cumulative_pct     | Cumulative percentage of babies born with this name (includes higher rows)                                |
| year_min           | Year this name was first used                                                                             |
| year_max           | Year this name was last used                                                                              |
| year_peak          | Most popular year for this name                                                                           |
| biblical           | Biblical name (1 = yes)                                                                                   |
| is_palindrome      | Name reads the same forwards and backwards (1 = yes)                                                      |
| pronunciations     | ARPABET phonetic pronunciations, separated by ` \| ` for multiple variants                                |
| first_letter       | First letter of the name                                                                                  |
| stresses           | Lexical stress pattern (0=unstressed, 1=primary, 2=secondary), separated by ` \| ` for multiple variants |
| syllables          | Number of syllables                                                                                       |
| alliteration       | Name contains any repeated phoneme (1 = yes)                                                              |
| alliteration_first | First phoneme repeats later in the name (1 = yes)                                                         |
| unisex             | Used by both genders with 15,000+ babies each, after 1970 (1 = yes)                                      |

## About

Baby books are outdated — mostly name lists with no context for popularity, spelling variations, or historical trends. This project was created to fill that gap.

## Development

Requires Python 3.12+ with [Polars](https://pola.rs/) for data processing and the [cmudict](https://pypi.org/project/cmudict/) package for phonetic lookups.

```bash
pip install polars cmudict
```

To regenerate the CSV files:

```bash
cd src
python babynames.py --verbose
```

To run the test suite:

```bash
pip install pytest
pytest tests/ -v
```

### Web Viewer

The web viewer (`index.html`) uses [Pico CSS](https://picocss.com/) for styling, [Tabulator](https://tabulator.info/) for the data grid, and [Papa Parse](https://papaparse.com/) for CSV parsing — all loaded from CDN with no build step required.

## Datasets

This project uses two datasets (see `src/data`):

- **babynames**: For each year from 1880 to 2023, the number of children of each sex given each name. All names with more than 5 uses are given. (Source: [SSA Baby Names](https://www.ssa.gov/oact/babynames/limits.html))

- **biblical_names**: A curated, de-duplicated collection of biblical names.

## How to contribute

Have an idea? Found a bug? Contributions and pull requests are welcome.

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
