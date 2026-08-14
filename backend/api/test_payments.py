from decimal import Decimal
from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from .models import Organization, Payment, Subscription


class PaymentTests(APITestCase):
    def setUp(self):
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

        self.client.force_authenticate(self.user)

    @patch("api.payment_views.create_flutterwave_checkout")
    def test_create_payment_creates_pending_payment(
        self,
        create_checkout,
    ):
        create_checkout.return_value = (
            "fleet-test-ref",
            Decimal("75000"),
            "https://checkout.example.test/pay",
        )

        response = self.client.post(
            "/api/payments/create/",
            {
                "plan": "business",
                "billing_cycle": "monthly",
                "email": "owner@example.com",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        payment = Payment.objects.get(
            tx_ref="fleet-test-ref"
        )

        self.assertEqual(payment.status, "pending")
        self.assertEqual(
            payment.organization_id,
            self.organization.id,
        )
        self.assertEqual(
            payment.amount,
            Decimal("75000"),
        )

    def test_free_plan_does_not_create_payment(self):
        response = self.client.post(
            "/api/payments/create/",
            {
                "plan": "free",
                "billing_cycle": "monthly",
                "email": "owner@example.com",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    @patch("api.payment_views.verify_flutterwave_transaction")
    def test_valid_webhook_activates_subscription(
        self,
        verify_transaction,
    ):
        payment = Payment.objects.create(
            organization=self.organization,
            subscription=self.subscription,
            tx_ref="fleet-success",
            amount=Decimal("75000"),
            currency="UGX",
            plan="business",
            billing_cycle="monthly",
        )

        verify_transaction.return_value = {
            "id": 12345,
            "tx_ref": "fleet-success",
            "flw_ref": "FLW-123",
            "status": "successful",
            "amount": 75000,
            "currency": "UGX",
        }

        with self.settings():
            import os
            os.environ["FLW_SECRET_HASH"] = "test-secret"

            response = self.client.post(
                "/api/payments/flutterwave/webhook/",
                {
                    "event": "charge.completed",
                    "data": {
                        "id": 12345,
                        "tx_ref": "fleet-success",
                        "status": "successful",
                    },
                },
                format="json",
                HTTP_VERIF_HASH="test-secret",
            )

        self.assertEqual(response.status_code, 200)

        self.subscription.refresh_from_db()
        payment.refresh_from_db()

        self.assertEqual(
            self.subscription.plan,
            "business",
        )
        self.assertEqual(
            self.subscription.status,
            "active",
        )
        self.assertIsNotNone(
            self.subscription.expires_at
        )
        self.assertEqual(
            payment.status,
            "successful",
        )

    def test_invalid_webhook_signature_is_rejected(self):
        response = self.client.post(
            "/api/payments/flutterwave/webhook/",
            {
                "event": "charge.completed",
                "data": {
                    "id": 1,
                    "tx_ref": "unknown",
                },
            },
            format="json",
            HTTP_VERIF_HASH="wrong",
        )

        self.assertEqual(response.status_code, 401)

    def test_payment_status_is_organization_scoped(self):
        payment = Payment.objects.create(
            organization=self.organization,
            subscription=self.subscription,
            tx_ref="fleet-status",
            amount=Decimal("25000"),
            currency="UGX",
            plan="starter",
            billing_cycle="monthly",
        )

        response = self.client.get(
            f"/api/payments/status/{payment.tx_ref}/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["status"],
            "pending",
        )
