import os
import warnings
from datetime import timedelta

from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.backends import TokenBackend
from django.conf import settings
import bcrypt

_DEV_SECRET = "synapse-dev-secret-change-in-prod-32chars!"


def validate_jwt_config() -> None:
    key = settings.SIMPLE_JWT.get("SIGNING_KEY", "")
    if not key or key == _DEV_SECRET:
        warnings.warn(
            "JWT_SECRET_KEY is using the insecure default — set a strong secret in production!",
            stacklevel=2,
        )


class SynapseAccessToken(AccessToken):
    """Custom token that mirrors the existing JWT payload: sub, role, ngo_id, email."""

    @classmethod
    def for_user_data(cls, user_id: str, role: str, ngo_id, email: str = ""):
        token = cls()
        token["sub"] = user_id
        token["role"] = role
        token["ngo_id"] = ngo_id
        token["email"] = email
        # Override simplejwt's default 'user_id' claim with our 'sub'
        if "user_id" in token.payload:
            del token.payload["user_id"]
        return token


def create_token(user_id: str, role: str, ngo_id, email: str = "") -> str:
    return str(SynapseAccessToken.for_user_data(user_id, role, ngo_id, email))


def decode_token_payload(token: str) -> dict:
    backend = TokenBackend(
        algorithm="HS256",
        signing_key=settings.SIMPLE_JWT["SIGNING_KEY"],
    )
    return backend.decode(token, verify=True)


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False
