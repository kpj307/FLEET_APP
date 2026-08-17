from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.cache import cache
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from .models import Organization, Payment, Subscription
from .throttles import (
    LoginThrottle,
    PaymentCreateThrottle,
    PaymentStatusThrottle,
    RegistrationThrottle,
    TokenRefreshThrottle,
)


class RegistrationThrottleTests(APITestCase):
    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    @patch.object(
        RegistrationThrottle,
        "THROTTLE_RATES",
        {
            "registration": "2/min",
        },
    )
    def test_registration_is_rate_limited(self):
        url = reverse("register")

        for index in range(2):
            response = self.client.post(
                url,
                {
                    "username": f"throttle-user-{index}",
                    "email": (
                        f"throttle-{index}@example.com"
                    ),
                    "password": "StrongPass123!",
                },
                format="json",
            )

            self.assertNotEqual(
                response.status_code,
                status.HTTP_429_TOO_MANY_REQUESTS,
            )

        response = self.client.post(
            url,
            {
                "username": "throttle-user-3",
                "email": "throttle-3@example.com",
                "password": "StrongPass123!",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_429_TOO_MANY_REQUESTS,
        )


class LoginThrottleTests(APITestCase):
    def setUp(self):
        cache.clear()

        self.user = User.objects.create_user(
            username="login-throttle",
            password="StrongPass123!",
        )

    def tearDown(self):
        cache.clear()

    @patch.object(
        LoginThrottle,
        "THROTTLE_RATES",
        {
            "login": "2/min",
        },
    )
    def test_login_is_rate_limited(self):
        url = reverse("get_token")

        payload = {
            "username": "login-throttle",
            "password": "WrongPassword123!",
        }

        # First two requests reach authentication.
        for _ in range(2):
            response = self.client.post(
                url,
                payload,
                format="json",
            )

            self.assertEqual(
                response.status_code,
                status.HTTP_401_UNAUTHORIZED,
            )

        # Third request is throttled before authentication.
        response = self.client.post(
            url,
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_429_TOO_MANY_REQUESTS,
        )


class TokenRefreshThrottleTests(APITestCase):
    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    @patch.object(
        TokenRefreshThrottle,
        "THROTTLE_RATES",
        {
            "token_refresh": "2/min",
        },
    )
    def test_token_refresh_is_rate_limited(self):
        url = reverse("refresh")

        # We intentionally use an invalid refresh token.
        # The first two requests reach JWT validation.
        # The third request must be throttled first.
        payload = {
            "refresh": "invalid-test-refresh-token",
        }

        for _ in range(2):
            response = self.client.post(
                url,
                payload,
                format="json",
            )

            self.assertNotEqual(
                response.status_code,
                status.HTTP_429_TOO_MANY_REQUESTS,
            )

        response = self.client.post(
            url,
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_429_TOO_MANY_REQUESTS,
        )


class PaymentThrottleTests(APITestCase):
    def setUp(self):
        cache.clear()

        self.user = User.objects.create_user(
            username="payment-owner",
            password="StrongPass123!",
            email="owner@example.com",
        )

        self.organization = Organization.objects.create(
            owner=self.user,
            name="Payment Fleet",
            slug="payment-fleet",
        )

        self.subscription = Subscription.objects.create(
            organization=self.organization,
            plan="free",
        )

        self.client.force_authenticate(
            user=self.user
        )

        self.payment = Payment.objects.create(
            organization=self.organization,
            subscription=self.subscription,
            tx_ref="fleet-throttle-status",
            amount=Decimal("10000.00"),
            currency="UGX",
            plan="professional",
            billing_cycle="monthly",
            status="pending",
        )

    def tearDown(self):
        cache.clear()

    @patch.object(
        PaymentCreateThrottle,
        "THROTTLE_RATES",
        {
            "payment_create": "2/min",
        },
    )
    @patch(
        "api.payment_views.create_flutterwave_checkout"
    )
    def test_payment_creation_is_rate_limited(
        self,
        mock_checkout,
    ):
        mock_checkout.side_effect = [
            (
                f"fleet-throttle-create-{index}",
                Decimal("10000.00"),
                "https://checkout.example.com",
            )
            for index in range(3)
        ]

        url = reverse("payment-create")

        payload = {
            "plan": "professional",
            "billing_cycle": "monthly",
        }

        # First request: allowed.
        response = self.client.post(
            url,
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        # Second request: allowed.
        response = self.client.post(
            url,
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        # Third request: throttled.
        response = self.client.post(
            url,
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_429_TOO_MANY_REQUESTS,
        )

        # Flutterwave checkout must not be called
        # for the throttled request.
        self.assertEqual(
            mock_checkout.call_count,
            2,
        )

    @patch.object(
        PaymentStatusThrottle,
        "THROTTLE_RATES",
        {
            "payment_status": "2/min",
        },
    )
    def test_payment_status_is_rate_limited(self):
        url = reverse(
            "payment-status",
            kwargs={
                "tx_ref": self.payment.tx_ref,
            },
        )

        # First request: allowed.
        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        # Second request: allowed.
        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        # Third request: throttled.
        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_429_TOO_MANY_REQUESTS,
        )