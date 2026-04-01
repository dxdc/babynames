"""Shared FastAPI dependencies."""

from typing import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from babynames.api.auth import AuthUser, get_current_user, get_optional_user
from babynames.db.config import get_db


def db_session() -> Generator[Session, None, None]:
    """Database session dependency."""
    yield from get_db()


# Re-export auth dependencies for convenience
__all__ = [
    "db_session",
    "get_current_user",
    "get_optional_user",
    "AuthUser",
    "Session",
]
