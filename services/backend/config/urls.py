from django.urls import path, include
from django.http import JsonResponse
from django.db import connection


def health_check(request):
    # Handle preflight — some browsers send OPTIONS before GET
    if request.method == "OPTIONS":
        response = JsonResponse({}, status=200)
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type"
        return response

    db_status = "ok"
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        db_status = "error"

    response = JsonResponse({
        "status": "healthy" if db_status == "ok" else "degraded",
        "database": db_status,
        "service": "sanchaalan-saathi-backend",
        "version": "2.0.0",
    }, status=200)
    # Explicitly allow all origins — this is a public health endpoint with no
    # sensitive data. Belt-and-suspenders alongside django-cors-headers.
    response["Access-Control-Allow-Origin"] = "*"
    return response


urlpatterns = [
    path("api/auth/",           include("apps.accounts.urls")),
    path("api/ngo/",            include("apps.ngo.urls")),
    path("api/volunteer/",      include("apps.volunteer.urls")),
    path("api/graph/",          include("apps.graph.urls")),
    path("api/analytics/",      include("apps.graph.analytics_urls")),
    path("api/volunteers/",     include("apps.graph.volunteer_neo4j_urls")),
    path("api/seed/",           include("apps.graph.seed_urls")),
    path("api/ingest/",         include("apps.ingest.urls")),
    path("api/voice/",          include("apps.ingest.voice_urls")),
    path("api/sim/",            include("simulation.urls")),
    path("api/chatbot/metrics/",include("apps.chatbot.metrics_urls")),
    path("api/chatbot/",        include("apps.chatbot.urls")),
    path("api/",                include("apps.guest.urls")),
    path("api/realtime/",       include("apps.realtime.urls")),
    path("health",              health_check),
]
