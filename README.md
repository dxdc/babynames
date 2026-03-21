# baby names

This project was designed as a tool to help parents find names for their newborns.

With this list: Jonathan, Johnathan, Johnathon, Jonothan, Jonathon are now just considered alternative spellings for a single "name".

Using publicly-available datasets from the United States Social Security Administration, lists of baby names between the years of 1880 and 2023 were collated, de-duplicated by phonetic
pronunciation using the [CMU Pronouncing Dictionary](https://en.wikipedia.org/wiki/CMU_Pronouncing_Dictionary), and then ordered by popularity.

## How to Use

The source code for this project is included, as are the compiled datasets:

- [all-names.csv](all-names.csv), as well as [boys.csv](boys.csv) and [girls.csv](girls.csv)

You can also browse the data using the [interactive web viewer](https://dxdc.github.io/babynames/), which supports filtering by gender, rank, syllable count, starting letter, year range, biblical status, and unisex classification. Filter states are saved in the URL hash for easy sharing.

Recommendation: Review this list in order from top to bottom, applying any filters you wish.

The following columns are provided:

| Header             | Description                                                                                                    |
| ------------------ | -------------------------------------------------------------------------------------------------------------- |
| rank               | Popularity index (1880-2023)                                                                                   |
| name               | Baby name (most popular spelling)                                                                              |
| spelling_variants  | Alternative spellings with the same pronunciation, separated by spaces                                         |
| total_count        | Total number of babies born in the United States with this name (includes alternate spellings)                  |
| cumulative_pct     | Cumulative percentage of babies born with this name (includes higher rows)                                     |
| year_min           | Year this name was first used                                                                                  |
| year_max           | Year this name was last used                                                                                   |
| year_peak          | Most popular year for this name                                                                                |
| biblical           | Biblical name (1 = yes)                                                                                        |
| is_palindrome      | Name reads the same forwards and backwards (1 = yes)                                                           |
| pronunciations     | ARPABET phonetic pronunciations, separated by ` \| ` for multiple variants                                     |
| first_letter       | First letter of the name                                                                                       |
| stresses           | Lexical stress pattern (0=unstressed, 1=primary, 2=secondary), separated by ` \| ` for multiple variants      |
| syllables          | Number of syllables                                                                                            |
| alliteration       | Name contains any repeated phoneme (1 = yes)                                                                   |
| alliteration_first | First phoneme repeats later in the name (1 = yes)                                                              |
| unisex             | Used by both genders with 15,000+ babies each, after 1970 (1 = yes)                                           |

## Observations

Reviewing a few thousand names is probably sufficient to find one that is relatively "normal", and encompasses 90-95% of the most common names.
Unless you happen to be looking for a highly unique or specific name, that is a very reasonable number of options for review.

## About

Baby books are outdated. Mostly, they consist of name lists that expectant parents need to review with little or no context / direction. That is highly inefficient.

Topics like:

- Name popularity
- Alternative spellings
- Biblical names
- Number of syllables
- Starting letters
- Old-fashioned names
- Unisex names

and more, are not considered.

Furthermore, the datasets these baby books are using don't necessarily reflect reality, and reviewing similar lists of names from different resources multiple times is a waste of time.

No helpful resources could be identified, so this project was created.

## Development

Requires Python 3.12+ and the following dependencies:

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

## Datasets

This package uses two datasets (see `src/data`):

- `babynames`: For each year from 1880 to 2023 the number of children of
  each sex given each name. All names with more than 5 uses are given.
  (Source: http://www.ssa.gov/oact/babynames/limits.html)

- `biblical_names`: A collection of de-duplicated biblical names collected from the web.

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
