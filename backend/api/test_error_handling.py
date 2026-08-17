import json
import logging
from django.contrib.auth.models import User
from django.core.cache import cache
from django.urls import reverse
from django.test import override_settings
from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APITestCase

from .models import Organization
from .logging_utils import JSONFormatter

from .models import (
    Organization,
    Subscription,
)

class ErrorHandlingTests(APITestCase):

    def setUp(self):
        cache.clear()

        self.user = User.objects.create_user(
            username="error-owner",
            password="StrongPass123!",
            email="error@example.com",
        )

        self.organization = Organization.objects.create(
            owner=self.user,
            name="Error Fleet",
            slug="error-fleet",
        )

        self.subscription = Subscription.objects.create(
            organization=self.organization,
            plan="free",
        )

        self.client.force_authenticate(
            user=self.user
        )

    def tearDown(self):
        cache.clear()

    def test_unauthorized_request_has_standard_error_shape(
        self,
    ):
        self.client.force_authenticate(
            user=None
        )

        response = self.client.get(
            reverse("dashboard")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        self.assertIn(
            "error",
            response.data,
        )

        self.assertIn(
            "code",
            response.data["error"],
        )

        self.assertIn(
            "message",
            response.data["error"],
        )

        self.assertIn(
            "request_id",
            response.data["error"],
        )

    def test_not_found_has_standard_error_shape(self):
        response = self.client.get(
            "/api/does-not-exist/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        data = response.json()

        self.assertIn(
            "error",
            data,
        )

        self.assertEqual(
            data["error"]["code"],
            "NOT_FOUND",
        )

        self.assertIn(
            "message",
            data["error"],
        )

        self.assertIn(
            "request_id",
            data["error"],
        )

        self.assertEqual(
            response.headers.get(
                "X-Request-ID"
            ),
            data["error"]["request_id"],
        )
    
    def test_request_id_header_is_returned(self):
        response = self.client.get(
            reverse("dashboard")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        request_id = response.headers.get(
            "X-Request-ID"
        )

        self.assertIsNotNone(request_id)

        self.assertTrue(
            len(request_id) > 0
        )

    def test_supplied_request_id_is_preserved(self):
        request_id = "fleet-test-request-123"

        response = self.client.get(
            reverse("dashboard"),
            HTTP_X_REQUEST_ID=request_id,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.headers.get(
                "X-Request-ID"
            ),
            request_id,
        )

    @patch(
    "api.views.DashboardView.get",
    side_effect=RuntimeError(
        "SECRET INTERNAL FAILURE"
    ),
    )
    def test_unexpected_api_exception_is_safe(
        self,
        mocked_get,
    ):
        response = self.client.get(
            reverse("dashboard")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

        self.assertIn(
            "error",
            response.data,
        )

        error = response.data["error"]

        self.assertEqual(
            error["code"],
            "INTERNAL_SERVER_ERROR",
        )

        self.assertEqual(
            error["message"],
            "An unexpected error occurred.",
        )

        self.assertIn(
            "request_id",
            error,
        )

        self.assertNotIn(
            "SECRET INTERNAL FAILURE",
            str(response.data),
        )

    def test_json_formatter_removes_sensitive_fields(self):
        formatter = JSONFormatter()

        record = logging.LogRecord(
            name="api",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="Authentication event",
            args=(),
            exc_info=None,
        )

        record.user_id = 10
        record.password = "SuperSecretPassword"
        record.authorization = (
            "Bearer very-secret-token"
        )

        output = formatter.format(record)

        payload = json.loads(output)

        self.assertEqual(
            payload["user_id"],
            10,
        )

        self.assertNotIn(
            "password",
            payload,
        )

        self.assertNotIn(
            "authorization",
            payload,
        )