"""Baby name analysis using SSA data with phonetic deduplication.

Processes US Social Security Administration baby name data (1880-present),
deduplicates names by phonetic pronunciation using the CMU Pronouncing Dictionary,
and enriches with features like syllable count, stress patterns, and biblical status.

For names not found in CMU dict, the g2p_en neural model is used if available
(pip install g2p-en), otherwise falls back to recursive subword splitting.
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
# Excluded names — SSA data artifacts, not real baby names
# ---------------------------------------------------------------------------

EXCLUDED_NAMES: set[str] = {
    "Unknown",
    "Infant",
    "Male",
    "Female",
    "Babyboy",
    "Babygirl",
    "Notnamed",
    "Unnamed",
}

# ---------------------------------------------------------------------------
# CMU Pronouncing Dictionary
# ---------------------------------------------------------------------------

ARPABET: ArpabetDict = cmudict.dict()

PRONUNCIATION_SEPARATOR = " | "
STRESS_SEPARATOR = " | "

# Try to load g2p_en for neural OOV pronunciation
_g2p_model = None
try:
    from g2p_en import G2p as _G2p

    _g2p_model = _G2p()
    log.info("g2p_en neural model loaded -- will use for OOV names")
except Exception:
    log.info("g2p_en not available -- falling back to subword splitting for OOV names")


# ---------------------------------------------------------------------------
# Phonetic helpers
# ---------------------------------------------------------------------------


MAX_PRONUNCIATION_VARIANTS = 10
MIN_SUBWORD_LENGTH = 2


@cache
def split_into_subwords(word: str) -> list[Phonemes]:
    """Recursively split a word into CMU-dict sub-words and combine phonemes.

    Tries partitions starting near the middle of the word, preferring
    longer prefixes. Requires both prefix and suffix to be at least
    MIN_SUBWORD_LENGTH characters to avoid spurious matches against
    short CMU entries like "ja", "a", "j" which produce garbage phonemes
    when used as name components.

    Returns combined phoneme lists for all valid splits,
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
        if len(prefix) < MIN_SUBWORD_LENGTH or len(suffix) < MIN_SUBWORD_LENGTH:
            continue
        if prefix in ARPABET and split_into_subwords(suffix):
            combined = [
                left + right
                for left, right in iterprod(ARPABET[prefix], split_into_subwords(suffix))
            ]
            return combined[:MAX_PRONUNCIATION_VARIANTS]
    return []


def _g2p_neural(name: str) -> PronunciationList:
    """Use g2p_en neural model to predict pronunciation for an OOV name.

    Returns a single-element list with the ARPABET pronunciation string,
    or an empty list if the model produces no valid phonemes.
    """
    if _g2p_model is None:
        return []
    try:
        raw = _g2p_model(name)
        # g2p_en returns a flat list mixing phonemes and spaces; filter to phonemes only
        phonemes = [p for p in raw if p.strip() and p != " "]
        if phonemes:
            return [" ".join(phonemes)]
    except Exception:
        pass
    return []


def get_grouping_pronunciations(name: str) -> PronunciationList:
    """Get pronunciations suitable for determining spelling variant groups.

    Only uses high-confidence sources: CMU dictionary direct lookup and
    subword splitting (which itself only combines known CMU entries).
    Does NOT use the g2p_en neural model, because it can produce
    incorrect English-centric pronunciations for non-English names
    (e.g., Juane → 'W EY1 N' instead of the correct Spanish pronunciation),
    causing unrelated names to merge.
    """
    lower = name.lower()
    if lower in ARPABET:
        return [" ".join(phonemes) for phonemes in ARPABET[lower]]
    return [" ".join(phonemes) for phonemes in split_into_subwords(name)]


def get_pronunciations(name: str) -> PronunciationList:
    """Get all known ARPABET pronunciations for a name.

    Used for display, syllable counting, and feature extraction.
    Priority:
    1. CMU dictionary direct lookup (may return multiple pronunciations)
    2. g2p_en neural model if available (single pronunciation, high quality)
    3. Recursive sub-word splitting (multiple pronunciations, lower quality)
    """
    lower = name.lower()
    if lower in ARPABET:
        return [" ".join(phonemes) for phonemes in ARPABET[lower]]
    neural = _g2p_neural(name)
    if neural:
        return neural
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


def estimate_syllables_from_spelling(name: str) -> int:
    """Estimate syllable count from spelling when no pronunciation is available.

    Counts vowel groups and applies heuristics for silent-e and consonant-le.
    Not as accurate as ARPABET-based counting, but far better than returning 0
    for the ~22% of names that the CMU dictionary doesn't cover.
    """
    lower = name.lower()
    groups = re.findall(r"[aeiouy]+", lower)
    count = len(groups)
    # Silent e at end (but not 'ee', 'ie', 'ye' endings)
    if (
        lower.endswith("e")
        and not lower.endswith(("ee", "ie", "ye"))
        and count > 1
        and len(lower) > 3
    ):
        count -= 1
    # Consonant-le at end counts as a syllable
    if lower.endswith("le") and len(lower) > 2 and lower[-3] not in "aeiouy":
        count += 1
    return max(count, 1)


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

    raw = pl.concat(frames)
    before = raw.height
    raw = raw.filter(~pl.col("name").is_in(EXCLUDED_NAMES))
    excluded = before - raw.height
    if excluded:
        log.info("Excluded %d rows matching %d blocked names", excluded, len(EXCLUDED_NAMES))
    return raw


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
    """Group names that share a pronunciation as spelling variants.

    Uses get_grouping_pronunciations() (CMU dict + subword only) for
    determining groups, NOT the full pronunciations column (which may
    include g2p_en neural predictions that incorrectly merge unrelated
    names like Juane→Wayne or Djaun→John).

    For names with multiple pronunciations, each name is assigned to the
    pronunciation cluster with the most members — i.e., the pronunciation
    shared by the most other names.

    Since each name maps to exactly one "best" pronunciation, a simple dict
    yields the groups directly — no transitive closure is needed.

    Creates two columns:
    - spelling_variants: other names in the same group (excludes self)
    - variant_group: integer group ID (used as merge key)
    """
    names: list[str] = df["name"].to_list()

    # Compute grouping-safe pronunciations (CMU dict + subword only)
    grouping_prons: list[PronunciationList] = [get_grouping_pronunciations(name) for name in names]

    # Build pronunciation -> names index using ALL grouping pronunciations
    pron_to_names: dict[str, set[str]] = {}
    for name, pronunciations in zip(names, grouping_prons, strict=True):
        for pron in pronunciations:
            if pron:
                pron_to_names.setdefault(pron, set()).add(name)

    # For each name, pick the pronunciation whose cluster has the most members.
    # This selects the "most shared" pronunciation as the grouping key.
    # Ties are broken by pronunciation order (first in list wins).
    name_to_best_pron: dict[str, str] = {}
    for name, pronunciations in zip(names, grouping_prons, strict=True):
        if not pronunciations:
            name_to_best_pron[name] = ""
            continue
        best_pron = pronunciations[0]
        best_size = len(pron_to_names.get(best_pron, set()))
        for pron in pronunciations[1:]:
            size = len(pron_to_names.get(pron, set()))
            if size > best_size:
                best_pron = pron
                best_size = size
        name_to_best_pron[name] = best_pron

    # Build groups from best-pronunciation assignments
    best_pron_to_group: dict[str, set[str]] = {}
    for name, pron in name_to_best_pron.items():
        if pron:
            best_pron_to_group.setdefault(pron, set()).add(name)

    # Assign stable integer group IDs.
    # Names without pronunciation each get their own unique group
    # to prevent them from being merged together.
    pron_to_id: dict[str, int] = {}
    next_id = 0
    variant_ids: list[int] = []
    variant_strs: list[str] = []
    for name in names:
        pron = name_to_best_pron[name]
        if not pron:
            # No pronunciation — assign a unique group (no merging)
            variant_ids.append(next_id)
            next_id += 1
            variant_strs.append("")
            continue
        if pron not in pron_to_id:
            pron_to_id[pron] = next_id
            next_id += 1
        variant_ids.append(pron_to_id[pron])
        group = best_pron_to_group.get(pron, set())
        others = sorted(group - {name})
        variant_strs.append(" ".join(others))

    return df.with_columns(
        pl.Series("spelling_variants", variant_strs),
        pl.Series("variant_group", variant_ids),
    )


def merge_spelling_variants(df: pl.DataFrame) -> pl.DataFrame:
    """Merge rows that share a variant_group, keeping the most popular spelling.

    Explicitly selects the name with the highest total_count as the primary name.
    Sums counts, takes min/max of years, unions pronunciations.
    Spelling variants are sorted by descending popularity (most common first).
    """
    log.info("Merging spelling variants")

    merged: dict[tuple[int, str], dict] = {}

    for row in df.iter_rows(named=True):
        key = (row["variant_group"], row["sex"])
        if key not in merged:
            merged[key] = {
                "name": row["name"],
                "_best_count": row["total_count"],
                "_members": {row["name"]: row["total_count"]},
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
            entry["_members"][row["name"]] = row["total_count"]
            if row["total_count"] > entry["_best_count"]:
                entry["name"] = row["name"]
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
        primary = entry["name"]
        members = entry.pop("_members")
        del entry["_best_count"]
        # Sort variants by descending count (most popular first), exclude primary
        others = sorted(
            ((name, count) for name, count in members.items() if name != primary),
            key=lambda x: -x[1],
        )
        entry["spelling_variants"] = " ".join(name for name, _ in others)
        entry["pronunciations"] = sorted(entry["pronunciations"])
        records.append(entry)

    result = pl.DataFrame(records)
    return result.sort(["sex", "total_count", "name"], descending=[False, True, False])


def compute_name_features(df: pl.DataFrame) -> pl.DataFrame:
    """Compute derived linguistic features from pronunciations.

    For names without ARPABET pronunciations, syllable count is estimated
    from the spelling using vowel-group heuristics.
    """
    log.info("Computing linguistic features")
    pronunciations_list: list[PronunciationList] = df["pronunciations"].to_list()
    names: list[str] = df["name"].to_list()

    syllables = []
    for name, prons in zip(names, pronunciations_list, strict=True):
        if prons:
            syllables.append(get_syllable_count(prons))
        else:
            syllables.append(estimate_syllables_from_spelling(name))

    return df.with_columns(
        pl.Series("first_letter", [name[0] for name in names]),
        pl.Series("stresses", [get_stress_patterns(p) for p in pronunciations_list]),
        pl.Series("syllables", syllables),
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
    df: pl.DataFrame,
    *,
    min_count: int = 5000,
    min_year: int = 1970,
) -> pl.DataFrame:
    """Compute unisex percentage for names used by both genders.

    For each name that appears in both M and F datasets (with year_max > min_year
    and total_count > min_count for both), computes the minority gender's share
    of the total as a percentage (0–50, where 50 = perfectly balanced).

    For example: Jordan has 419k boys + 139k girls = 24.9% minority share.
    This value appears in both boys.csv and girls.csv, meaning "24.9% of all
    Jordans are the minority gender."

    Names that don't appear in both genders (or don't meet thresholds) get null.
    """
    candidates = df.filter((pl.col("year_max") > min_year) & (pl.col("total_count") > min_count))

    # Build name -> {sex: count} mapping
    name_sex_counts: dict[str, dict[str, int]] = {}
    for row in candidates.iter_rows(named=True):
        name_sex_counts.setdefault(row["name"], {})[row["sex"]] = row["total_count"]

    # Compute minority share and dominant gender for names with both genders
    name_pcts: dict[str, float] = {}
    name_dominant: dict[str, str] = {}
    for name, sex_counts in name_sex_counts.items():
        if len(sex_counts) < 2:
            continue
        counts = list(sex_counts.values())
        sexes = list(sex_counts.keys())
        minority = min(counts)
        total = sum(counts)
        name_pcts[name] = round(100 * minority / total, 1)
        # Dominant = the gender with more babies
        name_dominant[name] = sexes[0] if counts[0] >= counts[1] else sexes[1]

    log.info(
        "Computed unisex share for %d names (min count %d, after %d)",
        len(name_pcts),
        min_count,
        min_year,
    )

    names_list = df["name"].to_list()
    return df.with_columns(
        pl.Series(
            "unisex_pct",
            [name_pcts.get(name) for name in names_list],
            dtype=pl.Float64,
        ),
        pl.Series(
            "unisex_dominant",
            [name_dominant.get(name) for name in names_list],
            dtype=pl.String,
        ),
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
    "unisex_pct",
    "unisex_dominant",
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
        default=Path("raw"),
        help="Directory containing yob*.txt SSA files (default: raw)",
    )
    parser.add_argument(
        "--biblical",
        type=Path,
        default=Path("raw/biblical_names.csv"),
        help="Path to biblical names CSV (default: raw/biblical_names.csv)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data"),
        help="Output directory for CSV files (default: data)",
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
