from rest_framework.views import exception_handler
from rest_framework.response import Response
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        logger.exception("Unhandled exception in view %s", context.get("view"))
        response = Response({"error": "Internal server error"}, status=500)
    return response
