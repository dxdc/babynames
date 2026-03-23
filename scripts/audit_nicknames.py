#!/usr/bin/env python3
"""Audit nickname mappings against generated CSV data.

Checks for potential issues:
  1. Duplicate entries in nicknames.csv
  2. Formal names that are spelling variants (not primary names)
  3. Nicknames or formal names not found in data at all
  4. Nickname mappings that produce no output (both sides must exist as primary names)

Usage:
    python scripts/audit_nicknames.py [--data-dir data] [--nicknames raw/nicknames.csv]
"""

import argparse
import csv
from pathlib import Path


def load_primary_names(data_dir: Path) -> dict[str, set[str]]:
    """Load primary names (name column) by gender from generated CSVs."""
    names: dict[str, set[str]] = {"M": set(), "F": set()}
    for filename, sex in [("boys.csv", "M"), ("girls.csv", "F")]:
        filepath = data_dir / filename
        if not filepath.exists():
            continue
        with open(filepath) as f:
            for row in csv.DictReader(f):
                names[sex].add(row["name"])
    return names


def load_variant_map(data_dir: Path) -> dict[tuple[str, str], str]:
    """Load gender-aware mapping of variant names to their primary name.

    Returns dict keyed by (variant_name, sex) → primary_name.
    """
    variants: dict[tuple[str, str], str] = {}
    for filename, sex in [("boys.csv", "M"), ("girls.csv", "F")]:
        filepath = data_dir / filename
        if not filepath.exists():
            continue
        with open(filepath) as f:
            for row in csv.DictReader(f):
                primary = row["name"]
                for v in row.get("spelling_variants", "").split():
                    if v and v != primary:
                        variants[(v, sex)] = primary
    return variants


def audit_nicknames(
    nicknames_path: Path,
    data_dir: Path,
) -> None:
    """Run all nickname audits."""
    names = load_primary_names(data_dir)
    variants = load_variant_map(data_dir)
    entries = []
    with open(nicknames_path) as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("nickname"):
                continue
            parts = line.split(",")
            if len(parts) < 2:
                continue
            nick = parts[0].strip()
            formal = parts[1].strip()
            gender = parts[2].strip() if len(parts) >= 3 else ""
            entries.append((lineno, nick, formal, gender))

    # Check duplicates
    seen: set[tuple[str, str, str]] = set()
    print("=== Duplicate entries ===\n")
    dup_count = 0
    for lineno, nick, formal, gender in entries:
        key = (nick, formal, gender)
        if key in seen:
            print(f"  Line {lineno}: {nick},{formal},{gender}")
            dup_count += 1
        seen.add(key)
    if not dup_count:
        print("  None found.")

    # Check formal names that are variants (gender-aware)
    print("\n=== Formal names that are spelling variants (not primary) ===\n")
    variant_count = 0
    for lineno, nick, formal, gender in entries:
        genders = [gender] if gender in ("M", "F") else ["M", "F"]
        for g in genders:
            key = (formal, g)
            if key in variants and formal not in names[g]:
                primary = variants[key]
                print(
                    f"  Line {lineno}: {nick} -> {formal} ({gender}/{g}) "
                    f"— {formal} is variant of {primary}"
                )
                variant_count += 1
    if not variant_count:
        print("  None found.")

    # Check names not in data at all
    print("\n=== Names not found in data (as primary or variant) ===\n")
    missing_count = 0
    for lineno, nick, formal, gender in entries:
        genders = [gender] if gender in ("M", "F") else ["M", "F"]
        for g in genders:
            nick_known = nick in names[g] or (nick, g) in variants
            formal_known = formal in names[g] or (formal, g) in variants
            if not nick_known:
                print(f"  Line {lineno}: nickname '{nick}' not in {g} data")
                missing_count += 1
                break
            if not formal_known:
                print(f"  Line {lineno}: formal '{formal}' not in {g} data")
                missing_count += 1
                break
    if not missing_count:
        print("  None found.")

    # Check effective mappings (both must be primary for output)
    print("\n=== Dead mappings (won't produce output — nick or formal not a primary name) ===\n")
    dead_count = 0
    active_count = 0
    for lineno, nick, formal, gender in entries:
        genders = [gender] if gender in ("M", "F") else ["M", "F"]
        any_active = False
        for g in genders:
            if nick in names[g] and formal in names[g]:
                any_active = True
        if not any_active:
            reasons = []
            for g in genders:
                if nick not in names[g]:
                    reasons.append(f"{nick} not primary in {g}")
                if formal not in names[g]:
                    reasons.append(f"{formal} not primary in {g}")
            print(f"  Line {lineno}: {nick} -> {formal} ({gender}) — {', '.join(set(reasons))}")
            dead_count += 1
        else:
            active_count += 1

    print(f"\nSummary: {active_count} active, {dead_count} dead, {dup_count} duplicate")
    print(f"Total entries: {len(entries)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit nickname mappings")
    parser.add_argument(
        "--data-dir", type=Path, default=Path("data"), help="Directory with CSV files"
    )
    parser.add_argument(
        "--nicknames",
        type=Path,
        default=Path("raw/nicknames.csv"),
        help="Nicknames CSV file",
    )
    args = parser.parse_args()

    audit_nicknames(args.nicknames, args.data_dir)


if __name__ == "__main__":
    main()
