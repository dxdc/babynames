"""SQLAlchemy models for the Baby Names database."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def new_uuid() -> uuid.UUID:
    return uuid.uuid4()


# ─── Name Data ───────────────────────────────────────────────────────


class Name(Base):
    __tablename__ = "names"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    romanised_name: Mapped[str | None] = mapped_column(String(100))
    gender: Mapped[str] = mapped_column(String(1), nullable=False, index=True)  # M, F, U
    syllables: Mapped[int | None] = mapped_column(Integer)
    first_letter: Mapped[str | None] = mapped_column(String(1), index=True)
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    year_min: Mapped[int | None] = mapped_column(Integer)
    year_max: Mapped[int | None] = mapped_column(Integer)
    year_peak: Mapped[int | None] = mapped_column(Integer, index=True)
    pronunciations: Mapped[str | None] = mapped_column(Text)
    is_biblical: Mapped[str | None] = mapped_column(String(20))
    is_palindrome: Mapped[bool] = mapped_column(Boolean, default=False)
    unisex_pct: Mapped[float | None] = mapped_column(Float)
    spelling_variants: Mapped[str | None] = mapped_column(Text)  # Pipe-separated
    nicknames: Mapped[str | None] = mapped_column(Text)  # Comma-separated
    nickname_of: Mapped[str | None] = mapped_column(Text)

    # Enrichment fields
    meaning_short: Mapped[str | None] = mapped_column(Text)
    detailed_origin: Mapped[str | None] = mapped_column(Text)

    # Relationships
    origins: Mapped[list["NameOrigin"]] = relationship(back_populates="name", cascade="all, delete")
    meanings: Mapped[list["NameMeaning"]] = relationship(back_populates="name", cascade="all, delete")
    popularity_records: Mapped[list["PopularityRecord"]] = relationship(
        back_populates="name", cascade="all, delete"
    )
    variants: Mapped[list["Variant"]] = relationship(back_populates="name", cascade="all, delete")

    __table_args__ = (
        UniqueConstraint("display_name", "gender", name="uq_name_gender"),
        Index("ix_names_total_count", "total_count"),
    )


class Origin(Base):
    __tablename__ = "origins"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    language_family: Mapped[str | None] = mapped_column(String(100))
    region: Mapped[str | None] = mapped_column(String(100))

    name_origins: Mapped[list["NameOrigin"]] = relationship(back_populates="origin")


class NameOrigin(Base):
    __tablename__ = "name_origins"

    name_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("names.id", ondelete="CASCADE"), primary_key=True
    )
    origin_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("origins.id", ondelete="CASCADE"), primary_key=True
    )

    name: Mapped["Name"] = relationship(back_populates="origins")
    origin: Mapped["Origin"] = relationship(back_populates="name_origins")


class NameMeaning(Base):
    __tablename__ = "name_meanings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    name_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("names.id", ondelete="CASCADE"), nullable=False, index=True
    )
    meaning: Mapped[str] = mapped_column(Text, nullable=False)
    etymology: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(100))

    name: Mapped["Name"] = relationship(back_populates="meanings")


class PopularityRecord(Base):
    __tablename__ = "popularity_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    name_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("names.id", ondelete="CASCADE"), nullable=False
    )
    region: Mapped[str] = mapped_column(String(20), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    rank: Mapped[int | None] = mapped_column(Integer)
    count: Mapped[int | None] = mapped_column(Integer)

    name: Mapped["Name"] = relationship(back_populates="popularity_records")

    __table_args__ = (
        Index("ix_popularity_name_region_year", "name_id", "region", "year"),
        UniqueConstraint("name_id", "region", "year", name="uq_popularity_record"),
    )


class Variant(Base):
    __tablename__ = "variants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    name_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("names.id", ondelete="CASCADE"), nullable=False, index=True
    )
    group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    spelling: Mapped[str] = mapped_column(String(100), nullable=False)
    popularity_rank: Mapped[int | None] = mapped_column(Integer)

    name: Mapped["Name"] = relationship(back_populates="variants")


# ─── User Data ───────────────────────────────────────────────────────


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_active: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    favourites: Mapped[list["Favourite"]] = relationship(back_populates="user", cascade="all, delete")
    ranking_states: Mapped[list["RankingState"]] = relationship(
        back_populates="user", cascade="all, delete"
    )
    comparison_history: Mapped[list["ComparisonHistory"]] = relationship(
        back_populates="user", cascade="all, delete"
    )


class Favourite(Base):
    __tablename__ = "favourites"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("names.id", ondelete="CASCADE"), nullable=False
    )
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="favourites")
    name: Mapped["Name"] = relationship()

    __table_args__ = (UniqueConstraint("user_id", "name_id", name="uq_user_favourite"),)


class RankingState(Base):
    __tablename__ = "ranking_states"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("names.id", ondelete="CASCADE"), nullable=False
    )
    mu: Mapped[float] = mapped_column(Float, default=1500.0)
    phi: Mapped[float] = mapped_column(Float, default=350.0)
    sigma: Mapped[float] = mapped_column(Float, default=0.06)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)
    comparisons: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user: Mapped["User"] = relationship(back_populates="ranking_states")
    name: Mapped["Name"] = relationship()

    __table_args__ = (
        UniqueConstraint("user_id", "name_id", name="uq_user_ranking"),
        Index("ix_ranking_user_mu", "user_id", "mu"),
    )


class ComparisonHistory(Base):
    __tablename__ = "comparison_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    winner_name_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("names.id", ondelete="CASCADE"), nullable=False
    )
    loser_name_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("names.id", ondelete="CASCADE"), nullable=False
    )
    round_label: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="comparison_history")

    __table_args__ = (Index("ix_comparison_user_created", "user_id", "created_at"),)


class CollaborativeSession(Base):
    __tablename__ = "collaborative_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    invite_code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    participants: Mapped[list["SessionParticipant"]] = relationship(
        back_populates="session", cascade="all, delete"
    )


class SessionParticipant(Base):
    __tablename__ = "session_participants"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("collaborative_sessions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    session: Mapped["CollaborativeSession"] = relationship(back_populates="participants")
    user: Mapped["User"] = relationship()
