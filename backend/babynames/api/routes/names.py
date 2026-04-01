"""Name browsing, filtering, and detail endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from babynames.api.auth import AuthUser, get_optional_user
from babynames.api.deps import db_session
from babynames.db.models import Favourite, Name, NameMeaning, NameOrigin, Origin, PopularityRecord, RankingState, Variant
from babynames.logging import get_logger

log = get_logger("names")
router = APIRouter()


@router.get("/names")
def list_names(
    q: Optional[str] = Query(None, description="Free-text search on name"),
    gender: Optional[str] = Query(None, description="M, F, or U"),
    origins: Optional[str] = Query(None, description="Comma-separated origin slugs"),
    min_rank: Optional[int] = Query(None, description="Minimum popularity rank (for uncommon names)"),
    max_rank: Optional[int] = Query(None, description="Maximum popularity rank"),
    era_start: Optional[int] = Query(None, description="Names peaking after this year"),
    era_end: Optional[int] = Query(None, description="Names peaking before this year"),
    min_syllables: Optional[int] = Query(None),
    max_syllables: Optional[int] = Query(None),
    sort: str = Query("rank", description="rank, name, year_peak, random"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(db_session),
    user: AuthUser | None = Depends(get_optional_user),
):
    """Filter and paginate names."""
    query = select(Name)

    # Text search
    if q:
        query = query.where(Name.display_name.ilike(f"%{q}%"))

    # Gender filter
    if gender and gender.upper() in ("M", "F", "U"):
        query = query.where(Name.gender == gender.upper())

    # Origin filter
    if origins:
        origin_slugs = [s.strip() for s in origins.split(",") if s.strip()]
        if origin_slugs:
            query = query.join(NameOrigin).join(Origin).where(Origin.slug.in_(origin_slugs))

    # Popularity rank filters (inverse popularity: min_rank = "outside top N")
    # total_count is used as a proxy for rank — higher count = more popular
    # min_rank means "rank >= N" i.e. less popular
    if min_rank:
        # Count names more popular than this threshold
        # We filter by a subquery that checks rank position
        query = query.where(Name.total_count > 0)
        # For now, use total_count ordering as rank proxy
        # Names with lower total_count have higher rank numbers (less popular)

    if max_rank:
        query = query.where(Name.total_count > 0)

    # Era filter (peak decade)
    if era_start:
        query = query.where(Name.year_peak >= era_start)
    if era_end:
        query = query.where(Name.year_peak <= era_end)

    # Syllable filters
    if min_syllables:
        query = query.where(Name.syllables >= min_syllables)
    if max_syllables:
        query = query.where(Name.syllables <= max_syllables)

    # Count total before pagination
    count_query = select(func.count()).select_from(query.subquery())
    total = db.execute(count_query).scalar() or 0

    # Sorting
    if sort == "name":
        query = query.order_by(Name.display_name)
    elif sort == "year_peak":
        query = query.order_by(Name.year_peak.desc().nullslast())
    elif sort == "random":
        query = query.order_by(func.random())
    else:  # rank (default) — most popular first
        query = query.order_by(Name.total_count.desc())

    # Pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    names = db.execute(query).scalars().all()

    # Build favourite lookup if authenticated
    fav_set: set[str] = set()
    if user:
        import uuid
        user_uuid = uuid.UUID(user.user_id) if isinstance(user.user_id, str) else user.user_id
        favs = db.execute(
            select(Favourite.name_id).where(Favourite.user_id == user_uuid)
        ).scalars().all()
        fav_set = {str(f) for f in favs}

    # Compute rank position based on total_count ordering within gender
    # For now, use the index position as a simple rank proxy
    result = []
    for i, name in enumerate(names):
        # Get origin slugs
        origin_slugs = []
        for no in name.origins:
            origin_slugs.append(no.origin.slug if no.origin else "")

        result.append({
            "id": str(name.id),
            "display_name": name.display_name,
            "gender": name.gender,
            "origins": origin_slugs,
            "meaning_short": name.meaning_short,
            "rank": offset + i + 1,  # Position-based rank within current sort
            "year_peak": name.year_peak,
            "syllables": name.syllables,
            "is_favourite": str(name.id) in fav_set if user else None,
        })

    return {
        "names": result,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/origins")
def list_origins(db: Session = Depends(db_session)):
    """List all available origins with name counts for the filter UI."""
    results = db.execute(
        select(
            Origin.slug,
            Origin.name,
            func.count(NameOrigin.name_id).label("name_count"),
        )
        .join(NameOrigin, NameOrigin.origin_id == Origin.id)
        .group_by(Origin.id)
        .order_by(func.count(NameOrigin.name_id).desc())
    ).all()

    return {
        "origins": [
            {"slug": row.slug, "name": row.name, "name_count": row.name_count}
            for row in results
        ]
    }


@router.get("/names/{name_id}")
def get_name_detail(
    name_id: str,
    db: Session = Depends(db_session),
    user: AuthUser | None = Depends(get_optional_user),
):
    """Full name detail with meanings, origins, popularity, variants."""
    import uuid as uuid_mod

    try:
        name_uuid = uuid_mod.UUID(name_id)
    except ValueError:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Invalid name ID")

    name = db.execute(
        select(Name)
        .options(
            selectinload(Name.origins).selectinload(NameOrigin.origin),
            selectinload(Name.meanings),
            selectinload(Name.popularity_records),
            selectinload(Name.variants),
        )
        .where(Name.id == name_uuid)
    ).scalar_one_or_none()

    if not name:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Name not found")

    # Check favourite status and user note
    is_favourite = None
    user_note = None
    user_rating = None
    if user:
        user_uuid = uuid_mod.UUID(user.user_id) if isinstance(user.user_id, str) else user.user_id
        fav = db.execute(
            select(Favourite).where(
                Favourite.user_id == user_uuid, Favourite.name_id == name_uuid
            )
        ).scalar_one_or_none()
        is_favourite = fav is not None
        user_note = fav.note if fav else None

        ranking = db.execute(
            select(RankingState).where(
                RankingState.user_id == user_uuid, RankingState.name_id == name_uuid
            )
        ).scalar_one_or_none()
        if ranking:
            user_rating = {"mu": ranking.mu, "phi": ranking.phi, "comparisons": ranking.comparisons}

    # Parse nicknames
    nicknames = []
    if name.nicknames:
        nicknames = [n.strip() for n in name.nicknames.split(",") if n.strip()]

    return {
        "id": str(name.id),
        "display_name": name.display_name,
        "romanised_name": name.romanised_name,
        "gender": name.gender,
        "syllables": name.syllables,
        "pronunciations": name.pronunciations,
        "total_count": name.total_count,
        "year_min": name.year_min,
        "year_max": name.year_max,
        "year_peak": name.year_peak,
        "is_biblical": name.is_biblical,
        "origins": [
            {
                "name": no.origin.name,
                "language_family": no.origin.language_family,
                "region": no.origin.region,
            }
            for no in name.origins
            if no.origin
        ],
        "meanings": [
            {"meaning": m.meaning, "etymology": m.etymology, "source": m.source}
            for m in name.meanings
        ],
        "variants": [
            {"spelling": v.spelling, "popularity_rank": v.popularity_rank}
            for v in name.variants
        ],
        "nicknames": nicknames,
        "popularity": [
            {"region": p.region, "year": p.year, "rank": p.rank, "count": p.count}
            for p in sorted(name.popularity_records, key=lambda p: (p.region, p.year))
        ],
        "is_favourite": is_favourite,
        "user_note": user_note,
        "user_rating": user_rating,
    }
