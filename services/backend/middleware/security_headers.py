from __future__ import annotations

import os
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_IS_PROD = os.getenv("DEPLOYMENT_ENV", "development").lower() == "production"

# Tighter CSP in production; loosen connect-src for local tooling in development
_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: https:; "
    "connect-src 'self' wss: https:; "
    "font-src 'self' data:; "
    "frame-ancestors 'none';"
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Injects OWASP-recommended security headers on every response and strips
    the Server header to prevent framework fingerprinting.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(self), microphone=(), camera=()"
        response.headers["Content-Security-Policy"] = _CSP

        if _IS_PROD:
            response.headers["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains; preload"
            )

        # Suppress framework fingerprinting
        response.headers.pop("server", None)
        response.headers.pop("x-powered-by", None)

        return response
