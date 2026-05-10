from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError

from utils.auth_utils import decode_token, is_token_blacklisted

bearer = HTTPBearer()
optional_bearer = HTTPBearer(auto_error=False)


class CurrentUser:
    def __init__(self, user_id: str, role: str, ngo_id: str | None, email: str = ""):
        self.user_id = user_id
        self.role    = role
        self.ngo_id  = ngo_id
        self.email   = email


async def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
) -> CurrentUser:
    try:
        payload = decode_token(creds.credentials)
        jti = payload.get("jti")
        if jti and await is_token_blacklisted(jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
            )
        return CurrentUser(
            user_id=payload["sub"],
            role=payload["role"],
            ngo_id=payload.get("ngo_id"),
            email=payload.get("email", ""),
        )
    except HTTPException:
        raise
    except (JWTError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


def require_ngo_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if user.role != "ngo_admin":
        raise HTTPException(status_code=403, detail="NGO admin access required")
    if not user.ngo_id:
        raise HTTPException(status_code=403, detail="NGO not configured — complete NGO setup first")
    return user


def require_volunteer(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if user.role != "volunteer":
        raise HTTPException(status_code=403, detail="Volunteer access required")
    if not user.ngo_id:
        raise HTTPException(status_code=403, detail="Volunteer NGO not configured")
    return user


async def get_current_user_or_none(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(optional_bearer),
) -> Optional[CurrentUser]:
    if not creds:
        return None
    try:
        payload = decode_token(creds.credentials)
        jti = payload.get("jti")
        if jti and await is_token_blacklisted(jti):
            return None
        return CurrentUser(
            user_id=payload["sub"],
            role=payload["role"],
            ngo_id=payload.get("ngo_id"),
            email=payload.get("email", ""),
        )
    except Exception:
        return None


def assert_same_ngo(resource_ngo_id: str, user: CurrentUser) -> None:
    """Inline guard — call in route handlers where resource ngo_id must match user.ngo_id."""
    if user.ngo_id != resource_ngo_id:
        raise HTTPException(status_code=403, detail="Cross-NGO access denied")
