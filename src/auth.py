"""API key authentication and rate limiting."""

import hashlib
import secrets
import time
from collections import defaultdict

from fastapi import HTTPException, Request, Security
from fastapi.security import APIKeyHeader

from src.config import settings

# In-memory rate limit tracking (use Redis in production)
_rate_limits: dict[str, list[float]] = defaultdict(list)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def generate_api_key() -> str:
    """Generate a new API key."""
    return f"ocean_{secrets.token_urlsafe(32)}"


def hash_key(key: str) -> str:
    """Hash an API key for storage."""
    return hashlib.sha256(key.encode()).hexdigest()


def _check_rate_limit(key: str, max_requests: int, window_seconds: int = 60) -> bool:
    """Check if a key has exceeded its rate limit. Returns True if allowed."""
    now = time.time()
    cutoff = now - window_seconds

    # Clean old entries
    _rate_limits[key] = [t for t in _rate_limits[key] if t > cutoff]

    if len(_rate_limits[key]) >= max_requests:
        return False

    _rate_limits[key].append(now)
    return True


async def require_api_key(
    request: Request,
    api_key: str | None = Security(api_key_header),
) -> str:
    """Dependency that requires a valid API key.

    For MVP: accepts any key starting with 'ocean_' or the dev secret key.
    In production: validate against a database table.
    """
    # Allow unauthenticated access to docs and health
    if request.url.path in ("/", "/docs", "/openapi.json", "/health", "/redoc"):
        return "anonymous"

    if api_key is None:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Include X-API-Key header.",
        )

    # Accept dev key or any ocean_ prefixed key
    if api_key == settings.api_secret_key:
        return "dev"

    if not api_key.startswith("ocean_"):
        raise HTTPException(status_code=401, detail="Invalid API key format.")

    # Rate limiting
    if not _check_rate_limit(api_key, max_requests=settings.api_rate_limit):
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Max {settings.api_rate_limit} requests/minute.",
        )

    return api_key
