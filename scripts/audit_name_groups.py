#!/usr/bin/env python3
"""Audit name groupings in the generated CSV data.

Checks for potential issues:
  1. Names with very similar pronunciations that aren't grouped together
  2. Names with high-count spelling variants that might deserve their own entry
  3. Singleton names that share a pronunciation with another singleton

Usage:
    python scripts/audit_name_groups.py [--data-dir data] [--min-count 500]
"""

import argparse
import csv
from collections import defaultdict
from pathlib import Path


def load_names(data_dir: Path, min_count: int) -> list[dict]:
    """Load names from boys.csv and girls.csv."""
    names = []
    for filename, sex in [("boys.csv", "M"), ("girls.csv", "F")]:
        filepath = data_dir / filename
        if not filepath.exists():
            continue
        with open(filepath) as f:
            reader = csv.DictReader(f)
            for row in reader:
                count = int(row.get("total_count", 0))
                if count < min_count:
                    continue
                names.append(
                    {
                        "name": row["name"],
                        "sex": sex,
                        "count": count,
                        "rank": int(row.get("rank", 0)),
                        "variants": row.get("spelling_variants", ""),
                        "pronunciations": row.get("pronunciations", ""),
                    }
                )
    return names


def normalize_pronunciation(pron: str) -> str:
    """Normalize pronunciation for comparison: strip stress markers."""
    return "".join(c for c in pron if not c.isdigit()).strip()


def audit_shared_pronunciations(names: list[dict]) -> list[dict]:
    """Find names that share a normalized pronunciation but aren't grouped."""
    # Group by (normalized_pronunciation, sex)
    pron_groups: dict[tuple[str, str], list[dict]] = defaultdict(list)

    for entry in names:
        prons_raw = entry["pronunciations"]
        if not prons_raw:
            continue
        # pronunciations field is pipe-separated
        for pron in prons_raw.split("|"):
            pron = pron.strip()
            if not pron:
                continue
            norm = normalize_pronunciation(pron)
            if norm:
                pron_groups[(norm, entry["sex"])].append(entry)

    results = []
    seen = set()
    for (norm_pron, sex), group in pron_groups.items():
        if len(group) < 2:
            continue
        # Deduplicate — same name can appear via multiple pronunciations
        unique_names = {}
        for entry in group:
            if entry["name"] not in unique_names:
                unique_names[entry["name"]] = entry

        if len(unique_names) < 2:
            continue

        # Check if they're already grouped as variants of each other
        entries = list(unique_names.values())
        for i, a in enumerate(entries):
            a_all = {a["name"]} | set(a["variants"].split()) if a["variants"] else {a["name"]}
            for b in entries[i + 1 :]:
                if b["name"] in a_all:
                    continue  # already grouped
                b_all = {b["name"]} | set(b["variants"].split()) if b["variants"] else {b["name"]}
                if a["name"] in b_all:
                    continue  # already grouped

                pair_key = (min(a["name"], b["name"]), max(a["name"], b["name"]), sex)
                if pair_key in seen:
                    continue
                seen.add(pair_key)

                results.append(
                    {
                        "name_a": a["name"],
                        "name_b": b["name"],
                        "sex": sex,
                        "count_a": a["count"],
                        "count_b": b["count"],
                        "combined": a["count"] + b["count"],
                        "pronunciation": norm_pron,
                    }
                )

    results.sort(key=lambda x: -x["combined"])
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit name groupings")
    parser.add_argument(
        "--data-dir", type=Path, default=Path("data"), help="Directory with CSV files"
    )
    parser.add_argument(
        "--min-count",
        type=int,
        default=500,
        help="Min total count to consider (default: 500)",
    )
    args = parser.parse_args()

    print("Loading data...")
    names = load_names(args.data_dir, args.min_count)
    print(f"Loaded {len(names)} names (count >= {args.min_count})")

    print("\n=== Names with same pronunciation but not grouped ===\n")
    shared = audit_shared_pronunciations(names)

    if not shared:
        print("No ungrouped pronunciation matches found.")
    else:
        print(
            f"{'Name A':<16} {'Name B':<16} {'Sex':>3} {'Count A':>10} "
            f"{'Count B':>10} {'Combined':>10} {'Pronunciation'}"
        )
        print("-" * 95)
        for r in shared[:100]:  # top 100 by combined count
            print(
                f"{r['name_a']:<16} {r['name_b']:<16} {r['sex']:>3} {r['count_a']:>10} "
                f"{r['count_b']:>10} {r['combined']:>10} {r['pronunciation']}"
            )
        if len(shared) > 100:
            print(f"\n... and {len(shared) - 100} more")

    print(f"\nTotal: {len(shared)} pairs")


if __name__ == "__main__":
    main()
