"""Liveness and readiness probes for Kubernetes / load balancers."""

from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def liveness(request):
    """Process is up. Do not depend on external systems."""
    return JsonResponse({"status": "ok"})


@require_GET
def readiness(request):
    """Ready to serve traffic — database must accept connections."""
    try:
        connection.ensure_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ok"})
