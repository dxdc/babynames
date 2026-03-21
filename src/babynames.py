"""Baby name analysis using SSA data with phonetic deduplication.

Processes US Social Security Administration baby name data (1880-present),
deduplicates names by phonetic pronunciation using the CMU Pronouncing Dictionary,
and enriches with features like syllable count, stress patterns, and biblical status.
"""

import argparse
import logging
import re
from functools import cache
from itertools import product as iterprod
from pathlib import Path
from statistics import mean
from typing import TypeAlias

import cmudict
import polars as pl

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

Phonemes: TypeAlias = list[str]  # e.g. ["AH0", "B", "IY1"]
Pronunciation: TypeAlias = str  # ARPABET string, e.g. "AH0 B IY1"
PronunciationList: TypeAlias = list[Pronunciation]
ArpabetDict: TypeAlias = dict[str, list[Phonemes]]

# ---------------------------------------------------------------------------
# CMU Pronouncing Dictionary
# ---------------------------------------------------------------------------

ARPABET: ArpabetDict = cmudict.dict()

PRONUNCIATION_SEPARATOR = " | "
STRESS_SEPARATOR = " | "


# ---------------------------------------------------------------------------
# Phonetic helpers
# ---------------------------------------------------------------------------


MAX_PRONUNCIATION_VARIANTS = 10


@cache
def split_into_subwords(word: str) -> list[Phonemes]:
    """Recursively split a word into CMU-dict sub-words and combine phonemes.

    Tries partitions starting near the middle of the word, preferring
    longer prefixes. Returns combined phoneme lists for all valid splits,
    capped at MAX_PRONUNCIATION_VARIANTS to avoid combinatorial explosion.
    """
    word = word.lower()
    if word in ARPABET:
        return ARPABET[word][:MAX_PRONUNCIATION_VARIANTS]
    midpoint = len(word) / 2
    # Try split points ordered by distance from middle (prefer balanced splits)
    split_points = sorted(range(len(word)), key=lambda i: (i - midpoint) ** 2 - i)
    for i in split_points:
        prefix, suffix = word[:i], word[i:]
        if prefix in ARPABET and split_into_subwords(suffix):
            combined = [
                left + right
                for left, right in iterprod(ARPABET[prefix], split_into_subwords(suffix))
            ]
            return combined[:MAX_PRONUNCIATION_VARIANTS]
    return []


def get_pronunciations(name: str) -> PronunciationList:
    """Get all known ARPABET pronunciations for a name.

    First checks the CMU dictionary directly, then falls back to
    recursive sub-word splitting for compound or unusual names.
    """
    lower = name.lower()
    if lower in ARPABET:
        return [" ".join(phonemes) for phonemes in ARPABET[lower]]
    return [" ".join(phonemes) for phonemes in split_into_subwords(name)]


def extract_stress_pattern(pronunciation: Pronunciation) -> str:
    """Extract the stress pattern (digits 0-2) from an ARPABET pronunciation.

    Example: "M EH1 R IY0" -> "10"
    """
    return re.sub(r"[^0-2]", "", pronunciation)


def get_stress_patterns(pronunciations: PronunciationList) -> list[str]:
    """Extract stress patterns for all pronunciations."""
    return [extract_stress_pattern(p) for p in pronunciations]


def count_syllables(pronunciation: Pronunciation) -> int:
    """Count syllables in an ARPABET pronunciation (number of stress digits)."""
    return len(extract_stress_pattern(pronunciation))


def get_syllable_count(pronunciations: PronunciationList) -> int:
    """Average syllable count across all pronunciations, rounded to nearest int."""
    if pronunciations:
        return round(mean(count_syllables(p) for p in pronunciations))
    return 0


def has_repeated_phoneme(pronunciations: PronunciationList) -> bool:
    """Check if any phoneme appears more than once in any pronunciation."""
    return any(
        any(parts.count(phoneme) > 1 for phoneme in parts)
        for parts in (p.split() for p in pronunciations)
    )


def has_initial_phoneme_repeat(pronunciations: PronunciationList) -> bool:
    """Check if the first phoneme repeats later in any pronunciation."""
    for pronunciation in pronunciations:
        parts = pronunciation.split()
        if parts and parts.count(parts[0]) > 1:
            return True
    return False


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def load_ssa_data(data_dir: Path) -> pl.DataFrame:
    """Load all SSA baby name year-of-birth files into a single DataFrame.

    Each file is named yobYYYY.txt with format: name,sex,count
    """
    source_files = sorted(data_dir.glob("yob*.txt"))
    if not source_files:
        raise FileNotFoundError(f"No yob*.txt files found in {data_dir}")

    log.info("Loading %d SSA data files from %s", len(source_files), data_dir)
    frames: list[pl.DataFrame] = []
    for filepath in source_files:
        year = int(filepath.stem.replace("yob", ""))
        frame = pl.read_csv(
            filepath,
            has_header=False,
            new_columns=["name", "sex", "count"],
        ).with_columns(pl.lit(year).alias("year"))
        frames.append(frame)

    return pl.concat(frames)


def load_biblical_names(filepath: Path) -> pl.DataFrame:
    """Load biblical names CSV and add a boolean marker column."""
    log.info("Loading biblical names from %s", filepath)
    names = pl.read_csv(filepath, encoding="utf8-lossy")
    return names.with_columns(pl.lit(1).alias("biblical"))


# ---------------------------------------------------------------------------
# Pipeline stages
# ---------------------------------------------------------------------------


def find_peak_popularity_years(raw_data: pl.DataFrame) -> pl.DataFrame:
    """For each name+sex, find the year with the highest single-year count.

    When tied, the latest year wins.
    """
    max_counts = raw_data.group_by(["name", "sex"]).agg(pl.col("count").max().alias("count_max"))
    with_max = raw_data.join(max_counts, on=["name", "sex"])
    return (
        with_max.filter(pl.col("count") == pl.col("count_max"))
        .group_by(["name", "sex"])
        .agg(pl.col("year").max().alias("year_peak"))
    )


def aggregate_counts(raw_data: pl.DataFrame) -> pl.DataFrame:
    """Sum counts across all years per name+sex; track year range."""
    return (
        raw_data.group_by(["name", "sex"])
        .agg(
            pl.col("year").min().alias("year_min"),
            pl.col("year").max().alias("year_max"),
            pl.col("count").sum().alias("total_count"),
        )
        .sort(["sex", "total_count", "name"], descending=[False, True, False])
    )


def add_pronunciations(df: pl.DataFrame) -> pl.DataFrame:
    """Add a column of ARPABET pronunciations for each name."""
    log.info("Extracting pronunciations for %d names", df.height)
    names: list[str] = df["name"].to_list()
    pronunciations = [get_pronunciations(name) for name in names]
    return df.with_columns(pl.Series("pronunciations", pronunciations))


def build_spelling_variants(df: pl.DataFrame) -> pl.DataFrame:
    """Map names that share any pronunciation to each other as spelling variants.

    Creates two columns:
    - spelling_variants: other names with shared pronunciation (excludes self)
    - variant_group: all names in the group (includes self, used for dedup)
    """
    # Build pronunciation -> names index
    pronunciation_to_names: dict[str, set[str]] = {}
    for name, pronunciations in zip(
        df["name"].to_list(), df["pronunciations"].to_list(), strict=True
    ):
        for pronunciation in pronunciations:
            if pronunciation:
                pronunciation_to_names.setdefault(pronunciation, set()).add(name)

    names: list[str] = df["name"].to_list()
    pronunciations_list: list[PronunciationList] = df["pronunciations"].to_list()

    variants: list[str] = []
    groups: list[str] = []
    for name, pronunciations in zip(names, pronunciations_list, strict=True):
        all_related: set[str] = set()
        for pronunciation in pronunciations:
            if pronunciation in pronunciation_to_names:
                all_related.update(pronunciation_to_names[pronunciation])
        groups.append(" ".join(sorted(all_related)))
        all_related.discard(name)
        variants.append(" ".join(sorted(all_related)))

    return df.with_columns(
        pl.Series("spelling_variants", variants),
        pl.Series("variant_group", groups),
    )


def merge_spelling_variants(df: pl.DataFrame) -> pl.DataFrame:
    """Merge rows that share a variant_group, keeping the most popular spelling.

    Explicitly selects the name with the highest total_count as the primary name.
    Sums counts, takes min/max of years, unions pronunciations.
    """
    log.info("Merging spelling variants")

    merged: dict[tuple[str, str], dict] = {}

    for row in df.iter_rows(named=True):
        key = (row["variant_group"], row["sex"])
        if key not in merged:
            merged[key] = {
                "name": row["name"],
                "_best_count": row["total_count"],
                "spelling_variants": row["spelling_variants"],
                "total_count": row["total_count"],
                "year_min": row["year_min"],
                "year_max": row["year_max"],
                "year_peak": row["year_peak"],
                "biblical": row["biblical"],
                "is_palindrome": row.get("is_palindrome"),
                "pronunciations": set(row["pronunciations"] or []),
                "sex": row["sex"],
            }
        else:
            entry = merged[key]
            # Explicitly pick the spelling with the highest individual count;
            # use its year_peak since it dominates the group's popularity
            if row["total_count"] > entry["_best_count"]:
                entry["name"] = row["name"]
                entry["spelling_variants"] = row["spelling_variants"]
                entry["_best_count"] = row["total_count"]
                if row["year_peak"] is not None:
                    entry["year_peak"] = row["year_peak"]
            entry["total_count"] += row["total_count"]
            entry["year_min"] = min(entry["year_min"], row["year_min"])
            entry["year_max"] = max(entry["year_max"], row["year_max"])
            if row["biblical"]:
                entry["biblical"] = 1
            if row.get("is_palindrome"):
                entry["is_palindrome"] = 1
            if row["pronunciations"]:
                entry["pronunciations"].update(row["pronunciations"])

    records = []
    for entry in merged.values():
        del entry["_best_count"]
        entry["pronunciations"] = sorted(entry["pronunciations"])
        records.append(entry)

    result = pl.DataFrame(records)
    return result.sort(["sex", "total_count", "name"], descending=[False, True, False])


def compute_name_features(df: pl.DataFrame) -> pl.DataFrame:
    """Compute derived linguistic features from pronunciations."""
    log.info("Computing linguistic features")
    pronunciations_list: list[PronunciationList] = df["pronunciations"].to_list()
    names: list[str] = df["name"].to_list()

    return df.with_columns(
        pl.Series("first_letter", [name[0] for name in names]),
        pl.Series("stresses", [get_stress_patterns(p) for p in pronunciations_list]),
        pl.Series("syllables", [get_syllable_count(p) for p in pronunciations_list]),
        pl.Series(
            "alliteration",
            [1 if has_repeated_phoneme(p) else None for p in pronunciations_list],
            dtype=pl.Int64,
        ),
        pl.Series(
            "alliteration_first",
            [1 if has_initial_phoneme_repeat(p) else None for p in pronunciations_list],
            dtype=pl.Int64,
        ),
    )


def classify_unisex_names(
    df: pl.DataFrame, *, min_count: int = 15000, min_year: int = 1970
) -> pl.DataFrame:
    """Flag names used by both genders after min_year with at least min_count each."""
    candidates = df.filter((pl.col("year_max") > min_year) & (pl.col("total_count") > min_count))
    unisex_names: set[str] = set(
        candidates.group_by("name")
        .agg(pl.col("sex").n_unique().alias("sex_count"))
        .filter(pl.col("sex_count") > 1)["name"]
        .to_list()
    )
    return df.with_columns(
        pl.Series(
            "unisex",
            [1 if name in unisex_names else None for name in df["name"].to_list()],
            dtype=pl.Int64,
        )
    )


def flag_palindromes(df: pl.DataFrame) -> pl.DataFrame:
    """Flag names that read the same forwards and backwards."""
    names: list[str] = df["name"].to_list()
    return df.with_columns(
        pl.Series(
            "is_palindrome",
            [1 if n.lower() == n.lower()[::-1] else None for n in names],
            dtype=pl.Int64,
        )
    )


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

# Columns in output order
OUTPUT_COLUMNS: list[str] = [
    "name",
    "spelling_variants",
    "total_count",
    "year_min",
    "year_max",
    "year_peak",
    "biblical",
    "is_palindrome",
    "pronunciations",
    "first_letter",
    "stresses",
    "syllables",
    "alliteration",
    "alliteration_first",
    "unisex",
]


def serialize_list_columns(frame: pl.DataFrame) -> pl.DataFrame:
    """Convert list columns to pipe-separated strings for unambiguous CSV output.

    Multiple pronunciations: "M EH1 R IY0 | M AA1 R IY0"
    Multiple stress patterns: "10 | 10"
    """
    for col_name in frame.columns:
        dtype = frame[col_name].dtype
        if dtype == pl.List(pl.String):
            frame = frame.with_columns(
                pl.col(col_name).list.join(PRONUNCIATION_SEPARATOR).alias(col_name)
            )
        elif dtype.base_type() == pl.List:
            frame = frame.with_columns(
                pl.col(col_name)
                .cast(pl.List(pl.String))
                .list.join(STRESS_SEPARATOR)
                .alias(col_name)
            )
    return frame


def export_csvs(df: pl.DataFrame, output_dir: Path) -> None:
    """Write all-names.csv, boys.csv, and girls.csv."""
    output_dir.mkdir(parents=True, exist_ok=True)

    all_cols = ["sex"] + OUTPUT_COLUMNS
    all_names = df.select([c for c in all_cols if c in df.columns])
    all_names = serialize_list_columns(all_names)
    all_names.write_csv(output_dir / "all-names.csv")
    log.info("Wrote %s (%d rows)", output_dir / "all-names.csv", all_names.height)

    for sex_code, filename in [("M", "boys"), ("F", "girls")]:
        gender_df = (
            df.filter(pl.col("sex") == sex_code).drop("sex").sort("total_count", descending=True)
        )

        gender_df = gender_df.with_columns(
            pl.col("total_count").rank(method="dense", descending=True).cast(pl.Int64).alias("rank")
        )
        total = gender_df["total_count"].sum()
        gender_df = gender_df.with_columns(
            (100 * (pl.col("total_count").cum_sum() / total)).round(1).alias("cumulative_pct")
        )

        final_cols = ["rank", "name", "spelling_variants", "total_count", "cumulative_pct"]
        final_cols += [
            c for c in OUTPUT_COLUMNS if c not in ("name", "spelling_variants", "total_count")
        ]
        final_cols = [c for c in final_cols if c in gender_df.columns]
        gender_df = serialize_list_columns(gender_df.select(final_cols))

        gender_df.write_csv(output_dir / f"{filename}.csv")
        log.info("Wrote %s (%d rows)", output_dir / f"{filename}.csv", gender_df.height)


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

    # Load source data
    raw_data = load_ssa_data(args.data_dir)
    biblical_names = load_biblical_names(args.biblical)
    peak_years = find_peak_popularity_years(raw_data)

    # Aggregate across years
    df = aggregate_counts(raw_data)

    # Enrich with metadata
    df = df.join(biblical_names.select("name", "biblical"), on="name", how="left")
    df = add_pronunciations(df)
    df = build_spelling_variants(df)
    df = df.join(peak_years, on=["name", "sex"], how="left")
    df = flag_palindromes(df)

    # Deduplicate and compute features
    df = merge_spelling_variants(df)
    df = compute_name_features(df)
    df = classify_unisex_names(df)

    # Export
    export_csvs(df, args.output_dir)
    log.info("Done!")


if __name__ == "__main__":
    main()
