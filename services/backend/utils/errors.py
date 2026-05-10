from __future__ import annotations

import logging
import uuid

from fastapi import HTTPException

logger = logging.getLogger(__name__)


def safe_http_error(
    status_code: int,
    user_message: str,
    exc: Exception | None = None,
    context: str = "",
) -> HTTPException:
    """
    Log the real exception server-side with a short reference ID, then return
    a sanitized HTTPException that never leaks internal details to the client.

    Usage:
        raise safe_http_error(503, "Service temporarily unavailable", exc, "google_auth")
    """
    if exc is not None:
        ref = str(uuid.uuid4())[:8].upper()
        logger.error("[%s] %s: %s", ref, context or "unhandled", exc, exc_info=True)
        if status_code >= 500:
            return HTTPException(
                status_code=status_code,
                detail=f"{user_message} (ref: {ref})",
            )
    return HTTPException(status_code=status_code, detail=user_message)
