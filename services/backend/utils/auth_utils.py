from __future__ import annotations

import os
import uuid
import warnings
from datetime import datetime, timedelta, timezone

from jose import jwt, JWTError
from passlib.context import CryptContext

# ── Production detection ──────────────────────────────────────────────────────
# Single authoritative env var: DEPLOYMENT_ENV=production | staging | development
_DEPLOYMENT_ENV = os.getenv("DEPLOYMENT_ENV", "development").lower()
_IS_PRODUCTION = _DEPLOYMENT_ENV == "production"

_DEV_SECRET = "synapse-dev-secret-change-in-prod-32chars!"

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    if _IS_PRODUCTION:
        raise RuntimeError(
            "JWT_SECRET_KEY is required in production (DEPLOYMENT_ENV=production). "
            "Set a strong random secret in your deployment environment."
        )
    SECRET_KEY = _DEV_SECRET

if SECRET_KEY == _DEV_SECRET:
    warnings.warn(
        "JWT_SECRET_KEY is using the insecure default — set a strong secret before deploying!",
        stacklevel=2,
    )

ALGORITHM = "HS256"
EXPIRE_MINS = 60 * 24  # 24 hours

# ── Password hashing ──────────────────────────────────────────────────────────
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)


# ── Token creation / decoding ────────────────────────────────────────────────
def create_token(user_id: str, role: str, ngo_id: str | None, email: str = "") -> str:
    expire = datetime.now(tz=timezone.utc) + timedelta(minutes=EXPIRE_MINS)
    payload: dict = {
        "sub":    user_id,
        "role":   role,
        "ngo_id": ngo_id,
        "email":  email,
        "exp":    expire,
        "jti":    str(uuid.uuid4()),   # unique token ID — used for blacklisting on logout
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    for claim in ("sub", "role", "exp"):
        if claim not in payload:
            raise JWTError(f"Missing required claim: {claim}")
    return payload


# ── Startup validation ────────────────────────────────────────────────────────
def validate_jwt_config() -> None:
    if not SECRET_KEY:
        raise RuntimeError("JWT_SECRET_KEY is required.")


# ── Token blacklist (Redis-backed) ────────────────────────────────────────────
_redis_client = None


def _get_redis():
    global _redis_client
    if _redis_client is None:
        import redis.asyncio as aioredis
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        _redis_client = aioredis.from_url(redis_url, decode_responses=True)
    return _redis_client


async def blacklist_token(jti: str, expiry_seconds: int = EXPIRE_MINS * 60) -> None:
    """Add a token JTI to the Redis blacklist with TTL equal to its remaining validity."""
    try:
        r = _get_redis()
        await r.setex(f"bl:{jti}", expiry_seconds, "1")
    except Exception:
        pass  # non-fatal: blacklist unavailable degrades gracefully


async def is_token_blacklisted(jti: str) -> bool:
    """Return True if the token has been explicitly revoked (e.g. via logout)."""
    try:
        r = _get_redis()
        return await r.exists(f"bl:{jti}") == 1
    except Exception:
        return False  # fail open: if Redis is down, don't block all requests
