import logging
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.backends import TokenBackend
from django.conf import settings

logger = logging.getLogger(__name__)


class RequestUser:
    """Drop-in replacement for middleware.rbac.CurrentUser."""
    def __init__(self, user_id: str, role: str, ngo_id, email: str = ""):
        self.user_id = user_id
        self.role = role
        self.ngo_id = ngo_id
        self.email = email
        self.is_authenticated = True

    def __repr__(self):
        return f"<RequestUser {self.user_id} role={self.role} ngo={self.ngo_id}>"


class SynapseJWTAuthentication(BaseAuthentication):
    """Validates Bearer JWT tokens using the same HS256 secret as the old python-jose stack."""

    def authenticate(self, request):
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if not header.startswith("Bearer "):
            return None
        token = header.split(" ", 1)[1].strip()
        if not token:
            return None
        try:
            backend = TokenBackend(
                algorithm="HS256",
                signing_key=settings.SIMPLE_JWT["SIGNING_KEY"],
            )
            payload = backend.decode(token, verify=True)
            user = RequestUser(
                user_id=payload["sub"],
                role=payload["role"],
                ngo_id=payload.get("ngo_id"),
                email=payload.get("email", ""),
            )
            return (user, token)
        except Exception as exc:
            logger.debug("JWT decode failed: %s", exc)
            raise AuthenticationFailed("Invalid or expired token")

    def authenticate_header(self, request):
        return "Bearer"
