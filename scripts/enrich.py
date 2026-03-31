"""Enrich baby names CSV with meaning, detailed origin, and nickname data."""

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
BTN_CSV = ROOT / "raw/enrichment/btn-data/dataset.csv"
NICKNAMES_CSV = ROOT / "raw/enrichment/nicknames-data/names.csv"
BOYS_CSV = ROOT / "data/boys.csv"
GIRLS_CSV = ROOT / "data/girls.csv"


def load_btn_data():
    """Load Behind the Name dataset — extract clean meaning and origin."""
    meanings = {}  # name (lower) -> { meaning, detailed_origin, gender }

    with open(BTN_CSV, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("name", "").strip()
            if not name:
                continue

            raw_meaning = row.get("meaning", "")
            gender = row.get("gender", "").strip()
            raw_origin = row.get("origin", "").strip()

            # Clean meaning: the raw format is like:
            # "OLIVER   m   English, FrenchFrom Old French olivier..."
            # We need to strip: NAME + gender + language list, keeping only the description
            meaning = raw_meaning.replace("\n", " ").replace("\r", " ").strip()

            # Strategy: find the actual description by looking for common description starters
            # The description usually starts with: "From", "Means", "Derived", "Short form",
            # "Variant", "Diminutive", "Possibly", "Originally", "The name", "An English"
            desc_match = re.search(
                r"(?:From |Means |Derived |Short form |Variant |Diminutive |"
                r"Possibly |Originally |The name |An? [A-Z]|This name |"
                r"Of |In |Old |Combination |Form |Elabor|Modern |"
                r"Latini[sz]|Anglici[sz]|Feminine |Masculine )",
                meaning,
            )
            if desc_match:
                meaning = meaning[desc_match.start():]
            else:
                # Fallback: strip everything up to and including known language names
                meaning = re.sub(
                    r"^.*?(?:English|French|German|Latin|Greek|Hebrew|Biblical|Dutch|"
                    r"Swedish|Norwegian|Danish|Spanish|Italian|Irish|Scottish|Welsh|"
                    r"Portuguese|Russian|Polish|Czech|Ancient\s+\w+|Medieval\s+\w+)"
                    r"[,\s]*",
                    "",
                    meaning,
                ).strip()

            # Remove duplicate words from bad concatenation
            meaning = re.sub(r"(\b\w{4,})\1", r"\1", meaning)

            # Trim to first sentence for brevity
            if ". " in meaning:
                meaning = meaning[: meaning.index(". ") + 1]
            if len(meaning) > 200:
                meaning = meaning[:197] + "..."

            # Clean origin: "[English, French]" → "english|french"
            origin = raw_origin.strip("[]").strip()
            origin_parts = [
                o.strip()
                .lower()
                .replace("(rare)", "")
                .replace("(modern)", "")
                .strip()
                for o in origin.split(",")
            ]
            origin_parts = [o for o in origin_parts if o and len(o) < 30]

            # Map to our categories
            category_map = {
                "english": "english",
                "anglo-saxon": "english",
                "old english": "english",
                "medieval english": "english",
                "scottish": "celtic",
                "irish": "celtic",
                "welsh": "celtic",
                "gaelic": "celtic",
                "scottish gaelic": "celtic",
                "irish gaelic": "celtic",
                "cornish": "celtic",
                "breton": "celtic",
                "german": "germanic",
                "germanic": "germanic",
                "ancient germanic": "germanic",
                "old norse": "germanic",
                "norse mythology": "germanic",
                "swedish": "germanic",
                "danish": "germanic",
                "norwegian": "germanic",
                "dutch": "germanic",
                "biblical": "biblical",
                "biblical hebrew": "biblical",
                "biblical greek": "biblical",
                "biblical latin": "biblical",
                "hebrew": "biblical",
                "greek": "biblical",
                "ancient greek": "biblical",
                "latin": "biblical",
                "ancient roman": "biblical",
                "roman": "biblical",
            }

            categories = set()
            for o in origin_parts:
                if o in category_map:
                    categories.add(category_map[o])

            key = name.lower()
            if key not in meanings or len(meaning) > len(
                meanings.get(key, {}).get("meaning", "")
            ):
                meanings[key] = {
                    "meaning": meaning,
                    "detailed_origin": "|".join(sorted(origin_parts)[:5]),
                    "origin_categories": "|".join(sorted(categories)),
                    "gender": gender,
                }

    return meanings


def load_nicknames():
    """Load nickname mappings: formal name → list of nicknames."""
    nicknames = {}  # name (lower) -> set of nicknames
    nickname_of = {}  # nickname (lower) -> set of formal names

    with open(NICKNAMES_CSV) as f:
        reader = csv.DictReader(f)
        for row in reader:
            name1 = row.get("name1", "").strip().lower()
            rel = row.get("relationship", "").strip()
            name2 = row.get("name2", "").strip().lower()

            if rel == "has_nickname" and name1 and name2:
                nicknames.setdefault(name1, set()).add(name2)
                nickname_of.setdefault(name2, set()).add(name1)

    return nicknames, nickname_of


def enrich_csv(csv_path, btn_data, extra_nicknames, extra_nickname_of):
    """Add meaning, detailed_origin, and extra nicknames to a names CSV."""
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        original_fields = reader.fieldnames
        rows = list(reader)

    # Add new columns
    new_fields = [
        f
        for f in ["meaning", "detailed_origin"]
        if f not in original_fields
    ]
    fields = original_fields + new_fields

    # Update origin column if it exists but is empty, use BTN categories
    enriched = 0
    for row in rows:
        key = row["name"].lower()
        btn = btn_data.get(key, {})

        # Meaning
        if "meaning" not in row or not row.get("meaning"):
            row["meaning"] = btn.get("meaning", "")

        # Detailed origin (full language list)
        if "detailed_origin" not in row or not row.get("detailed_origin"):
            row["detailed_origin"] = btn.get("detailed_origin", "")

        # Update origin categories if BTN has better data
        if btn.get("origin_categories") and (
            not row.get("origin") or row["origin"] == ""
        ):
            row["origin"] = btn["origin_categories"]

        # Supplement nicknames
        if key in extra_nicknames:
            existing = set(
                (row.get("nicknames") or "").split(" ")
            )
            existing.discard("")
            new_nicks = extra_nicknames[key] - {
                n.lower() for n in existing
            }
            if new_nicks:
                # Title case new nicknames
                all_nicks = list(existing) + [
                    n.title() for n in sorted(new_nicks)
                ]
                row["nicknames"] = " ".join(all_nicks)

        if btn.get("meaning"):
            enriched += 1

        # Ensure all fields have values
        for f in fields:
            if f not in row:
                row[f] = ""

    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    total = len(rows)
    print(f"  {csv_path.name}: {enriched}/{total} names enriched with meanings")


def main():
    print("Loading Behind the Name data...")
    btn_data = load_btn_data()
    print(f"  {len(btn_data)} names loaded")

    print("Loading nickname data...")
    nicknames, nickname_of = load_nicknames()
    print(f"  {len(nicknames)} formal names, {len(nickname_of)} nicknames")

    print("Enriching boys.csv...")
    enrich_csv(BOYS_CSV, btn_data, nicknames, nickname_of)

    print("Enriching girls.csv...")
    enrich_csv(GIRLS_CSV, btn_data, nicknames, nickname_of)

    print("Done!")


if __name__ == "__main__":
    main()
