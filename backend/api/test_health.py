from unittest.mock import patch

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient


class HealthCheckTests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_health_endpoint_returns_ok(self):
        response = self.client.get("/health/")

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data,
            {
                "status": "ok",
            },
        )

    def test_health_endpoint_does_not_require_authentication(
        self,
    ):
        response = self.client.get("/health/")

        self.assertNotEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )


class ReadinessCheckTests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_readiness_endpoint_returns_ready(self):
        response = self.client.get("/ready/")

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data,
            {
                "status": "ready",
            },
        )

    def test_readiness_endpoint_does_not_require_authentication(
        self,
    ):
        response = self.client.get("/ready/")

        self.assertNotEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    @patch(
        "api.health_views.connection.cursor",
    )
    def test_readiness_returns_503_when_database_is_unavailable(
        self,
        mock_cursor,
    ):
        from django.db.utils import OperationalError

        mock_cursor.side_effect = OperationalError(
            "Database unavailable"
        )

        response = self.client.get("/ready/")

        self.assertEqual(
            response.status_code,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )

        self.assertEqual(
            response.data,
            {
                "status": "not_ready",
            },
        )