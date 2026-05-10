import uuid
import time
import logging

logger = logging.getLogger(__name__)


class GuestSessionMiddleware:
    """Ports FastAPI GuestSessionMiddleware. Sets request.guest_id cookie."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        guest_id = request.COOKIES.get("guest_id")
        is_new_guest = not guest_id
        if not guest_id:
            guest_id = str(uuid.uuid4())
        request.guest_id = guest_id

        response = self.get_response(request)

        if is_new_guest:
            response.set_cookie(
                "guest_id",
                guest_id,
                max_age=365 * 24 * 60 * 60,
                httponly=True,
                secure=request.is_secure(),
                samesite="Lax",
            )
        return response


class RequestLoggingMiddleware:
    """Ports FastAPI log_requests middleware."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.monotonic()
        try:
            response = self.get_response(request)
        except Exception:
            import traceback
            duration = time.monotonic() - start
            logger.error(
                "%s %s → 500 (%.3fs) UNHANDLED EXCEPTION:\n%s",
                request.method,
                request.path,
                duration,
                traceback.format_exc(),
            )
            from django.http import JsonResponse
            return JsonResponse({"error": "Internal server error"}, status=500)
        duration = time.monotonic() - start
        level = logging.WARNING if response.status_code >= 400 else logging.INFO
        logger.log(level, "%s %s → %s (%.3fs)",
                   request.method, request.path, response.status_code, duration)
        return response
