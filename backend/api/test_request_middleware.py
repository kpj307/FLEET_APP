import json
import logging
from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient


class RequestContextMiddlewareTests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_request_id_is_generated_when_missing(self):
        response = self.client.get("/health/")

        self.assertEqual(
            response.status_code,
            200,
        )

        request_id = response.headers.get(
            "X-Request-ID"
        )

        self.assertIsNotNone(request_id)

        self.assertTrue(
            len(request_id) > 0
        )

    def test_existing_request_id_is_preserved(self):
        request_id = "test-request-123"

        response = self.client.get(
            "/health/",
            HTTP_X_REQUEST_ID=request_id,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.headers.get("X-Request-ID"),
            request_id,
        )

    @patch(
        "api.middleware.logger.info"
    )
    def test_completed_request_is_logged(
        self,
        mock_logger,
    ):
        response = self.client.get(
            "/health/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        mock_logger.assert_called_once()

        args, kwargs = (
            mock_logger.call_args
        )

        self.assertEqual(
            args[0],
            "API request completed",
        )

        extra = kwargs["extra"]

        self.assertIn(
            "request_id",
            extra,
        )

        self.assertIn(
            "method",
            extra,
        )

        self.assertIn(
            "path",
            extra,
        )

        self.assertIn(
            "status_code",
            extra,
        )

        self.assertIn(
            "duration_ms",
            extra,
        )

    @override_settings(
        SLOW_REQUEST_THRESHOLD_MS=0
    )
    @patch(
        "api.middleware.logger.warning"
    )
    def test_slow_request_is_logged(
        self,
        mock_logger,
    ):
        self.client.get(
            "/health/"
        )

        messages = [
            call.args[0]
            for call in mock_logger.call_args_list
        ]

        self.assertIn(
            "Slow request",
            messages,
        )

    @patch(
        "api.middleware.logger.info"
    )
    def test_sensitive_headers_are_not_logged(
        self,
        mock_logger,
    ):
        self.client.get(
            "/health/",
            HTTP_AUTHORIZATION=(
                "Bearer super-secret-token"
            ),
            HTTP_COOKIE=(
                "sessionid=secret-session"
            ),
        )

        _, kwargs = (
            mock_logger.call_args
        )

        extra = kwargs["extra"]

        serialized = json.dumps(
            extra,
            default=str,
        ).lower()

        self.assertNotIn(
            "super-secret-token",
            serialized,
        )

        self.assertNotIn(
            "secret-session",
            serialized,
        )

        self.assertNotIn(
            "authorization",
            serialized,
        )

        self.assertNotIn(
            "cookie",
            serialized,
        )