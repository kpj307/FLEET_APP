from django.conf import settings
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient


class VersionEndpointTests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_version_endpoint_returns_metadata(self):
        response = self.client.get("/version/")

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data,
            {
                "name": settings.APP_NAME,
                "version": settings.APP_VERSION,
                "environment": settings.DJANGO_ENV,
            },
        )

    def test_version_endpoint_does_not_require_authentication(self):
        response = self.client.get("/version/")

        self.assertNotEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_version_endpoint_does_not_expose_secrets(self):
        response = self.client.get("/version/")

        response_text = str(response.data).lower()

        self.assertNotIn(
            "secret_key",
            response_text,
        )

        self.assertNotIn(
            "flutterwave",
            response_text,
        )

        self.assertNotIn(
            "database",
            response_text,
        )