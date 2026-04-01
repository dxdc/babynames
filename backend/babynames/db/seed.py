"""Seed PostgreSQL from existing CSV data and enrichment files.

Reads:
  - data/boys.csv, data/girls.csv (main name data)
  - raw/enrichment/btn-data/dataset.csv (Behind the Name meanings/origins)
  - raw/enrichment/nicknames-data/names.csv (nickname data)

Usage:
  python -m babynames.db.seed [--drop]
"""

import csv
import re
import sys
import uuid
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from babynames.db.config import engine
from babynames.db.models import Base, Name, NameMeaning, NameOrigin, Origin
from babynames.logging import get_logger, setup_logging

log = get_logger("seed")

ROOT = Path(__file__).parent.parent.parent.parent  # repo root
DATA_DIR = ROOT / "data"
BTN_CSV = ROOT / "raw" / "enrichment" / "btn-data" / "dataset.csv"

# Origin slug → display name mapping
ORIGIN_DISPLAY = {
    "english": "English",
    "french": "French",
    "german": "German",
    "latin": "Latin",
    "greek": "Greek",
    "hebrew": "Hebrew",
    "biblical": "Biblical",
    "celtic": "Celtic",
    "irish": "Irish",
    "scottish": "Scottish",
    "welsh": "Welsh",
    "spanish": "Spanish",
    "italian": "Italian",
    "portuguese": "Portuguese",
    "dutch": "Dutch",
    "scandinavian": "Scandinavian",
    "swedish": "Swedish",
    "norwegian": "Norwegian",
    "danish": "Danish",
    "finnish": "Finnish",
    "russian": "Russian",
    "polish": "Polish",
    "czech": "Czech",
    "arabic": "Arabic",
    "persian": "Persian",
    "turkish": "Turkish",
    "indian": "Indian",
    "japanese": "Japanese",
    "chinese": "Chinese",
    "korean": "Korean",
    "african": "African",
    "native american": "Native American",
    "hawaiian": "Hawaiian",
    "slavic": "Slavic",
    "hungarian": "Hungarian",
    "romanian": "Romanian",
    "ancient greek": "Ancient Greek",
    "old english": "Old English",
    "old norse": "Old Norse",
    "medieval": "Medieval",
    "germanic": "Germanic",
}

# Language family groupings
LANGUAGE_FAMILIES = {
    "english": "Germanic",
    "german": "Germanic",
    "dutch": "Germanic",
    "scandinavian": "Germanic",
    "swedish": "Germanic",
    "norwegian": "Germanic",
    "danish": "Germanic",
    "old english": "Germanic",
    "old norse": "Germanic",
    "germanic": "Germanic",
    "french": "Romance",
    "spanish": "Romance",
    "italian": "Romance",
    "portuguese": "Romance",
    "romanian": "Romance",
    "latin": "Romance",
    "irish": "Celtic",
    "scottish": "Celtic",
    "welsh": "Celtic",
    "celtic": "Celtic",
    "greek": "Hellenic",
    "ancient greek": "Hellenic",
    "russian": "Slavic",
    "polish": "Slavic",
    "czech": "Slavic",
    "slavic": "Slavic",
    "hebrew": "Semitic",
    "arabic": "Semitic",
    "biblical": "Semitic",
    "persian": "Indo-Iranian",
    "indian": "Indo-Iranian",
    "turkish": "Turkic",
    "finnish": "Uralic",
    "hungarian": "Uralic",
    "japanese": "Japonic",
    "chinese": "Sino-Tibetan",
    "korean": "Koreanic",
}


def _load_btn_meanings() -> dict[str, dict]:
    """Load Behind the Name data → {name_lower: {meaning, origins}}."""
    if not BTN_CSV.exists():
        log.warning(f"BTN data not found at {BTN_CSV}")
        return {}

    meanings: dict[str, dict] = {}
    with open(BTN_CSV, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("name", "").strip()
            if not name:
                continue

            raw_meaning = row.get("meaning", "").replace("\n", " ").replace("\r", " ").strip()
            raw_origin = row.get("origin", "").strip().strip("[]")

            # Extract description from meaning field
            desc_match = re.search(
                r"(?:From |Means |Derived |Short form |Variant |Diminutive |"
                r"Possibly |Originally |The name |An? [A-Z]|This name |"
                r"Of |In |Old |Combination |Form |Elabor|Modern |"
                r"Latini[sz]|Anglici[sz]|Feminine |Masculine )",
                raw_meaning,
            )
            meaning = raw_meaning[desc_match.start():] if desc_match else raw_meaning
            if ". " in meaning:
                meaning = meaning[: meaning.index(". ") + 1]
            if len(meaning) > 200:
                meaning = meaning[:197] + "..."

            # Parse origins
            origin_slugs = []
            for o in raw_origin.split(","):
                slug = o.strip().lower().replace("(rare)", "").replace("(modern)", "").strip()
                if slug and len(slug) < 30:
                    origin_slugs.append(slug)

            meanings[name.lower()] = {"meaning": meaning, "origins": origin_slugs}

    log.info(f"Loaded {len(meanings)} BTN entries")
    return meanings


def _parse_gender(sex: str) -> str:
    if sex.upper() in ("M", "F"):
        return sex.upper()
    return "U"


def seed_database(drop: bool = False) -> None:
    """Load all data into PostgreSQL."""
    setup_logging()

    if drop:
        log.info("Dropping all tables...")
        Base.metadata.drop_all(engine)

    log.info("Creating tables...")
    Base.metadata.create_all(engine)

    btn_data = _load_btn_meanings()

    # Collect all unique origins first
    all_origin_slugs: set[str] = set()
    for entry in btn_data.values():
        all_origin_slugs.update(entry.get("origins", []))

    session = Session(engine)
    try:
        # Check if already seeded
        existing = session.execute(text("SELECT COUNT(*) FROM names")).scalar()
        if existing and existing > 0 and not drop:
            log.info(f"Database already has {existing} names, skipping seed. Use --drop to re-seed.")
            return

        # Create origins
        origin_map: dict[str, uuid.UUID] = {}
        for slug in sorted(all_origin_slugs):
            if slug not in ORIGIN_DISPLAY:
                display = slug.title()
            else:
                display = ORIGIN_DISPLAY[slug]
            origin = Origin(
                slug=slug,
                name=display,
                language_family=LANGUAGE_FAMILIES.get(slug),
                region=None,
            )
            session.add(origin)
            session.flush()
            origin_map[slug] = origin.id

        log.info(f"Created {len(origin_map)} origins")

        # Load names from CSVs
        total = 0
        for csv_file, default_gender in [("boys.csv", "M"), ("girls.csv", "F")]:
            csv_path = DATA_DIR / csv_file
            if not csv_path.exists():
                log.warning(f"CSV not found: {csv_path}")
                continue

            with open(csv_path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                batch = []
                for row in reader:
                    display_name = row.get("name", "").strip()
                    if not display_name:
                        continue

                    name = Name(
                        display_name=display_name,
                        gender=default_gender,
                        syllables=int(row["syllables"]) if row.get("syllables") else None,
                        first_letter=row.get("first_letter", display_name[0] if display_name else None),
                        total_count=int(row["total_count"]) if row.get("total_count") else 0,
                        year_min=int(row["year_min"]) if row.get("year_min") else None,
                        year_max=int(row["year_max"]) if row.get("year_max") else None,
                        year_peak=int(row["year_peak"]) if row.get("year_peak") else None,
                        pronunciations=row.get("pronunciations"),
                        is_biblical=row.get("biblical") or None,
                        is_palindrome=row.get("is_palindrome") == "1",
                        unisex_pct=float(row["unisex_pct"]) if row.get("unisex_pct") else None,
                        spelling_variants=row.get("spelling_variants"),
                        nicknames=row.get("nicknames"),
                        nickname_of=row.get("nickname_of"),
                    )

                    # Enrich with BTN data
                    btn = btn_data.get(display_name.lower())
                    if btn:
                        name.meaning_short = btn["meaning"] if btn["meaning"] else None
                        name.detailed_origin = "|".join(btn["origins"]) if btn["origins"] else None

                    session.add(name)
                    session.flush()

                    # Link origins
                    if btn and btn["origins"]:
                        for slug in btn["origins"]:
                            if slug in origin_map:
                                session.add(NameOrigin(name_id=name.id, origin_id=origin_map[slug]))

                    # Add meaning
                    if btn and btn["meaning"]:
                        session.add(
                            NameMeaning(
                                name_id=name.id,
                                meaning=btn["meaning"],
                                source="Behind the Name",
                            )
                        )

                    total += 1
                    if total % 5000 == 0:
                        session.commit()
                        log.info(f"Processed {total} names...")

            log.info(f"Loaded {csv_file}")

        session.commit()
        log.info(f"Seed complete: {total} names loaded")

    except Exception:
        session.rollback()
        log.error("Seed failed", exc_info=True)
        raise
    finally:
        session.close()


if __name__ == "__main__":
    drop = "--drop" in sys.argv
    seed_database(drop=drop)
