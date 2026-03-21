"""Baby name analysis using SSA data with phonetic deduplication.

Processes US Social Security Administration baby name data (1880-present),
deduplicates names by phonetic pronunciation using the CMU Pronouncing Dictionary,
and enriches with features like syllable count, stress patterns, and biblical status.
"""

import argparse
import logging
import re
from collections.abc import Callable
from functools import lru_cache
from itertools import chain
from itertools import product as iterprod
from pathlib import Path
from statistics import mean

import cmudict
import polars as pl

log = logging.getLogger(__name__)

# Load CMU Pronouncing Dictionary
ARPABET: dict[str, list[list[str]]] = cmudict.dict()


# ---------------------------------------------------------------------------
# Phonetic helpers
# ---------------------------------------------------------------------------


@lru_cache(maxsize=None)
def wordbreak(s: str) -> list[list[str]]:
    """Recursively break a word into CMU-dict sub-words and combine pronunciations."""
    s = s.lower()
    if s in ARPABET:
        return ARPABET[s]
    middle = len(s) / 2
    partition = sorted(range(len(s)), key=lambda x: (x - middle) ** 2 - x)
    for i in partition:
        pre, suf = s[:i], s[i:]
        if pre in ARPABET and wordbreak(suf):
            return [x + y for x, y in iterprod(ARPABET[pre], wordbreak(suf))]
    return []


def phones_in_word(word: str) -> list[str]:
    """Get list of phonetic pronunciations for a word as ARPABET strings."""
    lower = word.lower()
    if lower in ARPABET:
        return [" ".join(phonemes) for phonemes in ARPABET[lower]]
    return [" ".join(x) for x in wordbreak(word)]


def stresses_in_word(phones: list[str]) -> list[str]:
    """Extract stress patterns (digits 0-2) from ARPABET phone strings."""
    return [re.sub(r"[^0-2]", "", phone) for phone in phones]


def syllable_count(phone_str: str) -> int:
    """Count syllables in an ARPABET phone string (count of stress digits)."""
    return len(re.sub(r"[^0-2]", "", phone_str))


def syllables_in_word(phones: list[str]) -> int:
    """Average syllable count across all pronunciations of a word."""
    if phones:
        return int(round(mean(syllable_count(p) for p in phones), 1))
    return 0


def alliteration_in_word(phones: list[str]) -> int | None:
    """Check if any phoneme repeats within any pronunciation."""
    for phone in phones:
        parts = phone.split()
        if any(parts.count(p) > 1 for p in parts):
            return 1
    return None


def alliteration_in_word_first_letter(phones: list[str]) -> int | None:
    """Check if the first phoneme repeats later in any pronunciation."""
    for phone in phones:
        parts = phone.split()
        if parts and parts.count(parts[0]) > 1:
            return 2
    return None


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def load_ssa_data(data_dir: Path) -> pl.DataFrame:
    """Load all SSA baby name year-of-birth files into a single DataFrame."""
    source_files = sorted(data_dir.glob("yob*.txt"))
    if not source_files:
        raise FileNotFoundError(f"No yob*.txt files found in {data_dir}")

    log.info("Loading %d SSA data files from %s", len(source_files), data_dir)
    frames = []
    for f in source_files:
        year = int(f.stem.replace("yob", ""))
        df = pl.read_csv(
            f,
            has_header=False,
            new_columns=["name", "sex", "n"],
        ).with_columns(pl.lit(year).alias("year"))
        frames.append(df)

    return pl.concat(frames)


def load_biblical_names(path: Path) -> pl.DataFrame:
    """Load biblical names CSV (single 'name' column)."""
    log.info("Loading biblical names from %s", path)
    df = pl.read_csv(path, encoding="utf8-lossy")
    return df.with_columns(pl.lit(1).alias("biblical"))


# ---------------------------------------------------------------------------
# Pipeline stages
# ---------------------------------------------------------------------------


def compute_popular_years(df: pl.DataFrame) -> pl.DataFrame:
    """For each name+sex, find the year with the highest count."""
    max_counts = df.group_by(["name", "sex"]).agg(pl.col("n").max().alias("n_max"))
    with_max = df.join(max_counts, on=["name", "sex"])
    popular = (
        with_max.filter(pl.col("n") == pl.col("n_max"))
        .group_by(["name", "sex"])
        .agg(pl.col("year").max().alias("year_pop"))
    )
    return popular


def aggregate_by_name(df: pl.DataFrame) -> pl.DataFrame:
    """Aggregate SSA data: sum counts, find year min/max per name+sex."""
    return (
        df.group_by(["name", "sex"])
        .agg(
            pl.col("year").min().alias("year_min"),
            pl.col("year").max().alias("year_max"),
            pl.col("n").sum().alias("n_sum"),
        )
        .sort(["sex", "n_sum", "name"], descending=[False, True, False])
    )


def extract_phonetics(df: pl.DataFrame) -> pl.DataFrame:
    """Add phonetic pronunciation column to DataFrame."""
    log.info("Extracting phonetic pronunciations for %d names", df.height)
    names = df["name"].to_list()
    phones = [phones_in_word(n) for n in names]
    return df.with_columns(pl.Series("phones", phones))


def build_alt_spellings(df: pl.DataFrame) -> pl.DataFrame:
    """Build alternative spellings map based on shared phonetic pronunciations."""
    # Explode phones to map each pronunciation -> set of names
    exploded = df.select("name", "phones").explode("phones")

    phones_map: dict[str, set[str]] = {}
    for row in exploded.iter_rows():
        name, phone = row
        if phone:
            phones_map.setdefault(phone, set()).add(name)

    # For each name, collect all names that share any pronunciation
    def get_alt_spellings(name: str, phones: list[str]) -> str:
        alts: set[str] = set()
        for phone in phones:
            if phone in phones_map:
                alts.update(phones_map[phone])
        alts.discard(name)
        return " ".join(sorted(alts))

    def get_full_alt_spellings(name: str, phones: list[str]) -> str:
        alts: set[str] = set()
        for phone in phones:
            if phone in phones_map:
                alts.update(phones_map[phone])
        return " ".join(sorted(alts))

    names = df["name"].to_list()
    phones_lists = df["phones"].to_list()

    alt_spellings = [get_alt_spellings(n, p) for n, p in zip(names, phones_lists)]
    full_alt_spellings = [get_full_alt_spellings(n, p) for n, p in zip(names, phones_lists)]

    return df.with_columns(
        pl.Series("alt_spellings", alt_spellings),
        pl.Series("full_alt_spellings", full_alt_spellings),
    )


def deduplicate_by_pronunciation(df: pl.DataFrame) -> pl.DataFrame:
    """Combine names with identical pronunciations, keeping most popular spelling."""
    log.info("Deduplicating names by pronunciation")

    # Group by full_alt_spellings + sex, aggregate
    # Convert to Python for the complex aggregation
    groups: dict[tuple[str, str], dict] = {}

    for row in df.iter_rows(named=True):
        key = (row["full_alt_spellings"], row["sex"])
        if key not in groups:
            groups[key] = {
                "name": row["name"],
                "alt_spellings": row["alt_spellings"],
                "n_sum": row["n_sum"],
                "year_min": row["year_min"],
                "year_max": row["year_max"],
                "year_pop": row["year_pop"],
                "biblical": row["biblical"],
                "palindrome": row.get("palindrome"),
                "phones": set(row["phones"]) if row["phones"] else set(),
                "sex": row["sex"],
            }
        else:
            g = groups[key]
            g["n_sum"] += row["n_sum"]
            g["year_min"] = min(g["year_min"], row["year_min"])
            g["year_max"] = max(g["year_max"], row["year_max"])
            g["year_pop"] = max(g["year_pop"], row["year_pop"]) if row["year_pop"] else g["year_pop"]
            if row["biblical"]:
                g["biblical"] = 1
            if row.get("palindrome"):
                g["palindrome"] = 1
            if row["phones"]:
                g["phones"].update(row["phones"])

    records = []
    for g in groups.values():
        g["phones"] = list(g["phones"])
        records.append(g)

    result = pl.DataFrame(records)
    return result.sort(["sex", "n_sum", "name"], descending=[False, True, False])


def compute_features(df: pl.DataFrame) -> pl.DataFrame:
    """Compute derived features: first_letter, stresses, syllables, alliteration."""
    log.info("Computing derived features")
    phones_lists = df["phones"].to_list()
    names = df["name"].to_list()

    first_letters = [n[0] for n in names]
    stresses = [stresses_in_word(p) for p in phones_lists]
    syllables = [syllables_in_word(p) for p in phones_lists]
    allit = [alliteration_in_word(p) for p in phones_lists]
    allit_first = [alliteration_in_word_first_letter(p) for p in phones_lists]

    return df.with_columns(
        pl.Series("first_letter", first_letters),
        pl.Series("stresses", stresses),
        pl.Series("syllables", syllables),
        pl.Series("alliteration", allit, dtype=pl.Int64),
        pl.Series("alliteration_first", allit_first, dtype=pl.Int64),
    )


def classify_unisex(df: pl.DataFrame, min_count: int = 15000, min_year: int = 1970) -> pl.DataFrame:
    """Mark names as unisex if used by both genders after min_year with min_count each."""
    candidates = df.filter((pl.col("year_max") > min_year) & (pl.col("n_sum") > min_count))
    unisex_names = (
        candidates.group_by("name")
        .agg(pl.col("sex").n_unique().alias("sex_count"))
        .filter(pl.col("sex_count") > 1)["name"]
        .to_list()
    )
    unisex_set = set(unisex_names)
    is_unisex = [1 if n in unisex_set else None for n in df["name"].to_list()]
    return df.with_columns(pl.Series("unisex", is_unisex, dtype=pl.Int64))


def add_palindromes(df: pl.DataFrame) -> pl.DataFrame:
    """Mark palindrome names."""
    names = df["name"].to_list()
    palindromes = [1 if n.lower() == n.lower()[::-1] else None for n in names]
    return df.with_columns(pl.Series("palindrome", palindromes, dtype=pl.Int64))


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


def export_csvs(df: pl.DataFrame, output_dir: Path) -> None:
    """Export all-names.csv, boys.csv, and girls.csv."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Column order for output
    output_cols = [
        "name",
        "alt_spellings",
        "n_sum",
        "year_min",
        "year_max",
        "year_pop",
        "biblical",
        "palindrome",
        "phones",
        "first_letter",
        "stresses",
        "syllables",
        "alliteration",
        "alliteration_first",
        "unisex",
    ]

    def stringify_lists(frame: pl.DataFrame) -> pl.DataFrame:
        """Convert list columns to space-separated strings for CSV output."""
        for col_name in frame.columns:
            if frame[col_name].dtype == pl.List(pl.String):
                frame = frame.with_columns(
                    pl.col(col_name).list.join(" ").alias(col_name)
                )
            elif str(frame[col_name].dtype).startswith("List"):
                frame = frame.with_columns(
                    pl.col(col_name).cast(pl.List(pl.String)).list.join(" ").alias(col_name)
                )
        return frame

    all_cols = ["sex"] + output_cols
    all_names = df.select([c for c in all_cols if c in df.columns])
    all_names = stringify_lists(all_names)
    all_names.write_csv(output_dir / "all-names.csv")
    log.info("Wrote %s (%d rows)", output_dir / "all-names.csv", all_names.height)

    for sex, label in [("M", "boys"), ("F", "girls")]:
        gender_df = df.filter(pl.col("sex") == sex).drop("sex")

        # Add rank and cumulative percentage
        gender_df = gender_df.with_columns(
            pl.col("n_sum")
            .rank(method="dense", descending=True)
            .cast(pl.Int64)
            .alias("rank")
        )
        total = gender_df["n_sum"].sum()
        gender_df = gender_df.with_columns(
            (100 * (pl.col("n_sum").cum_sum() / total))
            .round(1)
            .alias("n_percent")
        )

        # Reorder: rank first, then n_percent after n_sum
        final_cols = ["rank", "name", "alt_spellings", "n_sum", "n_percent"]
        final_cols += [c for c in output_cols if c not in ("name", "alt_spellings", "n_sum")]
        final_cols = [c for c in final_cols if c in gender_df.columns]
        gender_df = gender_df.select(final_cols)
        gender_df = stringify_lists(gender_df)

        gender_df.write_csv(output_dir / f"{label}.csv")
        log.info("Wrote %s (%d rows)", output_dir / f"{label}.csv", gender_df.height)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate baby name analysis CSVs")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data/babynames"),
        help="Directory containing yob*.txt SSA files (default: data/babynames)",
    )
    parser.add_argument(
        "--biblical",
        type=Path,
        default=Path("data/biblical_names.csv"),
        help="Path to biblical names CSV (default: data/biblical_names.csv)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(".."),
        help="Output directory for CSV files (default: ..)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    # Load data
    df = load_ssa_data(args.data_dir)
    df_bible = load_biblical_names(args.biblical)
    popular_years = compute_popular_years(df)

    # Aggregate by name+sex
    df = aggregate_by_name(df)

    # Join biblical names
    df = df.join(df_bible.select("name", "biblical"), on="name", how="left")

    # Extract phonetics and build alt spellings
    df = extract_phonetics(df)
    df = build_alt_spellings(df)

    # Join popular years
    df = df.join(popular_years, on=["name", "sex"], how="left")

    # Add palindromes
    df = add_palindromes(df)

    # Deduplicate by pronunciation
    df = deduplicate_by_pronunciation(df)

    # Compute derived features
    df = compute_features(df)

    # Classify unisex names
    df = classify_unisex(df)

    # Export
    export_csvs(df, args.output_dir)
    log.info("Done!")


if __name__ == "__main__":
    main()
