"""Operational probes; no restaurant data or deployment details are exposed."""

import logging

from django.db import DatabaseError, connection
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class HealthCheckView(APIView):
    """Liveness: the application can respond without requiring a database."""

    authentication_classes = []
    permission_classes = [AllowAny]
    http_method_names = ["get", "head", "options"]

    def get(self, request):
        return Response({"status": "ok", "version": request.version})


class ReadinessCheckView(HealthCheckView):
    """Readiness: a lightweight PostgreSQL query succeeds."""

    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except DatabaseError:
            # Do not log exception text: drivers may include connection details.
            logger.warning("Database readiness check failed.")
            return Response({"status": "unavailable"}, status=503)
        return Response({"status": "ok", "version": request.version})
