from django.db import connection
from django.db.utils import OperationalError

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckView(APIView):
    """
    Lightweight liveness endpoint.

    This endpoint confirms that the Django application
    process is running.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response(
            {
                "status": "ok",
            }
        )


class ReadinessCheckView(APIView):
    """
    Readiness endpoint.

    Confirms that the application can reach its database.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()

        except OperationalError:
            return Response(
                {
                    "status": "not_ready",
                },
                status=503,
            )

        return Response(
            {
                "status": "ready",
            }
        )