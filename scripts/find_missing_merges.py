#!/usr/bin/env python3
"""Find candidate missing forced merges by detecting name pairs that likely
should be grouped but aren't.

Reads the generated CSV files and checks for common substitution patterns
(C/K swaps, vowel endings, etc.) between ungrouped names.

Usage:
    python scripts/find_missing_merges.py [--data-dir data] [--merges raw/forced_merges.csv]
"""

import argparse
import csv
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Substitution rules: (pattern, replacement, description)
# Applied to name_a to generate candidate name_b forms.
# ---------------------------------------------------------------------------

RULES: list[tuple[str, str, str]] = [
    # C/K initial swaps
    (r"^C(?=[aeiou])", "K", "C→K initial"),
    (r"^K(?=[aeiou])", "C", "K→C initial"),
    (r"^Ch(?=r)", "K", "Chr→Kr"),
    (r"^Chr", "Kr", "Chr→Kr"),
    (r"^Kr", "Chr", "Kr→Chr"),
    # Vowel ending variants
    (r"yn$", "in", "-yn→-in"),
    (r"in$", "yn", "-in→-yn"),
    (r"en$", "an", "-en→-an"),
    (r"an$", "en", "-an→-en"),
    (r"en$", "in", "-en→-in"),
    (r"in$", "en", "-in→-en"),
    (r"en$", "on", "-en→-on"),
    (r"on$", "en", "-on→-en"),
    (r"an$", "in", "-an→-in"),
    (r"yn$", "en", "-yn→-en"),
    (r"yn$", "an", "-yn→-an"),
    # -ee/-ey/-ie/-eigh/-i endings
    (r"ey$", "ee", "-ey→-ee"),
    (r"ee$", "ey", "-ee→-ey"),
    (r"ey$", "ie", "-ey→-ie"),
    (r"ie$", "ey", "-ie→-ey"),
    (r"ey$", "eigh", "-ey→-eigh"),
    (r"eigh$", "ey", "-eigh→-ey"),
    (r"ee$", "ie", "-ee→-ie"),
    (r"ie$", "ee", "-ie→-ee"),
    (r"ee$", "eigh", "-ee→-eigh"),
    (r"eigh$", "ee", "-eigh→-ee"),
    (r"ey$", "i", "-ey→-i"),
    (r"ee$", "i", "-ee→-i"),
    (r"ie$", "i", "-ie→-i"),
    (r"ley$", "lee", "-ley→-lee"),
    (r"lee$", "ley", "-lee→-ley"),
    (r"ley$", "leigh", "-ley→-leigh"),
    (r"leigh$", "ley", "-leigh→-ley"),
    (r"lee$", "leigh", "-lee→-leigh"),
    (r"leigh$", "lee", "-leigh→-lee"),
    # -lyn/-lynn/-lin/-line
    (r"lynn$", "lyn", "-lynn→-lyn"),
    (r"lyn$", "lynn", "-lyn→-lynn"),
    (r"lynn$", "lin", "-lynn→-lin"),
    (r"lin$", "lynn", "-lin→-lynn"),
    (r"lyn$", "lin", "-lyn→-lin"),
    (r"lin$", "lyn", "-lin→-lyn"),
    # -son/-sen
    (r"son$", "sen", "-son→-sen"),
    (r"sen$", "son", "-sen→-son"),
    # Double/single consonant
    (r"ll", "l", "ll→l"),
    (r"(?<=[aeiou])l(?=[aeiouy])", "ll", "l→ll"),
    (r"tt", "t", "tt→t"),
    (r"(?<=[aeiou])t(?=[aeiouy])", "tt", "t→tt"),
    (r"nn", "n", "nn→n"),
    # Ph/F
    (r"^Ph", "F", "Ph→F"),
    (r"^F", "Ph", "F→Ph"),
    (r"ph", "f", "ph→f"),
    # -cia/-sha
    (r"cia$", "sha", "-cia→-sha"),
    (r"sha$", "cia", "-sha→-cia"),
    # -ette/-et
    (r"ette$", "et", "-ette→-et"),
    (r"et$", "ette", "-et→-ette"),
    # Jay-/Ja- (require at least 4 chars to avoid matching standalone "Ja")
    (r"^Jay(?=.)", "Ja", "Jay-→Ja-"),
    (r"^Ja(?=[^y].)", "Jay", "Ja-→Jay-"),
]


def load_names(data_dir: Path) -> dict[str, dict]:
    """Load names from boys.csv and girls.csv."""
    names: dict[str, dict] = {}
    for filename, sex in [("boys.csv", "M"), ("girls.csv", "F")]:
        filepath = data_dir / filename
        if not filepath.exists():
            continue
        with open(filepath) as f:
            reader = csv.DictReader(f)
            required = {"name", "total_count", "rank"}
            if not required.issubset(set(reader.fieldnames or [])):
                missing = required - set(reader.fieldnames or [])
                raise ValueError(f"{filepath}: missing required columns: {missing}")
            for row in reader:
                key = f"{row['name']}|{sex}"
                names[key] = {
                    "name": row["name"],
                    "sex": sex,
                    "count": int(row["total_count"]),
                    "variants": set(row.get("spelling_variants", "").split()),
                    "rank": int(row.get("rank", 0)),
                }
    return names


def load_existing_merges(merges_path: Path) -> set[tuple[str, str]]:
    """Load existing forced merges as a set of (source, target) pairs."""
    pairs = set()
    if not merges_path.exists():
        return pairs
    with open(merges_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("source"):
                continue
            parts = line.split(",", 1)
            if len(parts) == 2:
                pairs.add((parts[0].strip(), parts[1].strip()))
    return pairs


def main() -> None:
    parser = argparse.ArgumentParser(description="Find candidate missing forced merges")
    parser.add_argument(
        "--data-dir", type=Path, default=Path("data"), help="Directory with CSV files"
    )
    parser.add_argument(
        "--merges", type=Path, default=Path("raw/forced_merges.csv"), help="Existing merges file"
    )
    parser.add_argument(
        "--min-count", type=int, default=100, help="Min total count to consider (default: 100)"
    )
    parser.add_argument(
        "--max-ratio",
        type=float,
        default=0,
        help="Max source/target count ratio (e.g., 0.05 = 5%%). "
        "Filters out pairs where source is a large fraction of target, "
        "suggesting distinct names rather than misspellings. 0 = no filter.",
    )
    args = parser.parse_args()

    print("Loading data...")
    all_names = load_names(args.data_dir)
    existing = load_existing_merges(args.merges)
    print(f"Loaded {len(all_names)} name+sex entries, {len(existing)} existing merges")

    # Build lookup: (lowercase_name, sex) → key
    name_lookup: dict[tuple[str, str], str] = {}
    for key, info in all_names.items():
        name_lookup[(info["name"].lower(), info["sex"])] = key

    candidates: list[dict] = []
    seen_pairs: set[tuple[str, str, str]] = set()

    print("Applying substitution rules...")
    for _key, info in all_names.items():
        if info["count"] < args.min_count:
            continue

        name = info["name"]
        sex = info["sex"]

        for pat, repl, desc in RULES:
            # Apply pattern (case-preserving where possible)
            transformed = re.sub(pat, repl, name, count=1)
            if transformed == name:
                # Try case-insensitive
                transformed = re.sub(pat, repl, name, count=1, flags=re.IGNORECASE)
            if transformed == name:
                continue

            # Look up the transformed name
            match_key = name_lookup.get((transformed.lower(), sex))
            if not match_key:
                continue

            match_info = all_names[match_key]
            if match_info["count"] < args.min_count:
                continue

            # Skip if already grouped
            if transformed in info["variants"] or name in match_info["variants"]:
                continue

            # Skip if already in forced merges
            if (name, transformed) in existing or (transformed, name) in existing:
                continue

            # Deduplicate
            pair = tuple(sorted([name, transformed]) + [sex])
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)

            # The higher-count name should be the target
            # Use actual names from data (not transformed string which may have wrong case)
            if info["count"] >= match_info["count"]:
                source, target = match_info["name"], info["name"]
                source_count, target_count = match_info["count"], info["count"]
            else:
                source, target = info["name"], match_info["name"]
                source_count, target_count = info["count"], match_info["count"]

            # Ratio filter: if source is a large fraction of target, likely distinct names
            ratio = source_count / target_count if target_count else 1
            if args.max_ratio and ratio > args.max_ratio:
                continue

            candidates.append(
                {
                    "source": source,
                    "target": target,
                    "sex": sex,
                    "source_count": source_count,
                    "target_count": target_count,
                    "combined": info["count"] + match_info["count"],
                    "ratio": ratio,
                    "rule": desc,
                }
            )

    # Sort by combined count (highest impact first)
    candidates.sort(key=lambda x: -x["combined"])

    print(f"\nFound {len(candidates)} candidate pairs\n")
    print(
        f"{'Source':<16} {'Target':<16} {'Sex':>3} {'Src Count':>10} "
        f"{'Tgt Count':>10} {'Combined':>10} {'Ratio':>7} {'Rule'}"
    )
    print("-" * 103)
    for c in candidates:
        print(
            f"{c['source']:<16} {c['target']:<16} {c['sex']:>3} {c['source_count']:>10} "
            f"{c['target_count']:>10} {c['combined']:>10} {c['ratio']:>6.1%} {c['rule']}"
        )

    if candidates:
        print(f"\nTotal: {len(candidates)} candidates")
        print("\nTo add a merge, append to raw/forced_merges.csv:")
        print("  source_name,target_name")


if __name__ == "__main__":
    main()
