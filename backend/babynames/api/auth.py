"""Authentik OIDC JWT validation."""

import logging
from typing import Any

import httpx
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from babynames.db.config import settings
from babynames.logging import get_logger

log = get_logger("auth")
security = HTTPBearer(auto_error=False)

# Cache JWKS keys in memory — refreshed on key rotation failure
_jwks_cache: dict[str, Any] | None = None


async def _fetch_jwks() -> dict[str, Any]:
    """Fetch JWKS from Authentik."""
    global _jwks_cache
    if _jwks_cache is not None:
        return _jwks_cache

    jwks_url = settings.authentik_jwks_url
    if not jwks_url:
        log.warning("AUTHENTIK_JWKS_URL not configured — auth disabled")
        return {"keys": []}

    async with httpx.AsyncClient() as client:
        resp = await client.get(jwks_url, timeout=10.0)
        resp.raise_for_status()
        _jwks_cache = resp.json()
        log.info("JWKS fetched", extra={"key_count": len(_jwks_cache.get("keys", []))})
        return _jwks_cache


async def _decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token against Authentik's JWKS."""
    global _jwks_cache

    jwks = await _fetch_jwks()
    if not jwks.get("keys"):
        # Auth disabled — return a stub for development
        log.warning("No JWKS keys — returning stub user")
        return {"sub": "dev-user", "name": "Developer", "email": "dev@localhost"}

    try:
        payload = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            audience=settings.authentik_client_id,
            issuer=settings.authentik_issuer,
        )
        return payload
    except JWTError:
        # Key rotation? Clear cache and retry once
        _jwks_cache = None
        jwks = await _fetch_jwks()
        try:
            payload = jwt.decode(
                token,
                jwks,
                algorithms=["RS256"],
                audience=settings.authentik_client_id,
                issuer=settings.authentik_issuer,
            )
            return payload
        except JWTError as e:
            log.warning("JWT decode failed after JWKS refresh", extra={"error": str(e)})
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            ) from e


class AuthUser:
    """Authenticated user extracted from JWT claims."""

    def __init__(self, sub: str, name: str, email: str | None):
        self.sub = sub
        self.name = name
        self.email = email

    @property
    def user_id(self) -> str:
        return self.sub


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> AuthUser:
    """Extract authenticated user from JWT. Raises 401 if no valid token."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    payload = await _decode_token(credentials.credentials)
    return AuthUser(
        sub=payload.get("sub", ""),
        name=payload.get("name", payload.get("preferred_username", "Unknown")),
        email=payload.get("email"),
    )


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> AuthUser | None:
    """Extract user if token present, None otherwise. For public endpoints."""
    if credentials is None:
        return None
    try:
        payload = await _decode_token(credentials.credentials)
        return AuthUser(
            sub=payload.get("sub", ""),
            name=payload.get("name", payload.get("preferred_username", "Unknown")),
            email=payload.get("email"),
        )
    except HTTPException:
        return None
