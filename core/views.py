"""
Core views for health checks and system monitoring.
"""
from django.http import JsonResponse
from django.db import connection

def health_check(request):
    """
    Lightweight healthcheck endpoint for Docker, Docker Swarm, and Load Balancers.
    Returns HTTP 200 if database and application runtime are operating normally.
    """
    db_status = "healthy"
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    is_healthy = db_status == "healthy"
    status_code = 200 if is_healthy else 503
    return JsonResponse(
        {
            "status": "healthy" if is_healthy else "unhealthy",
            "database": db_status,
            "service": "pharmaback-api",
        },
        status=status_code,
    )
