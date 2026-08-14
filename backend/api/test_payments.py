from decimal import Decimal
from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from django.db import IntegrityError

from .models import Organization, Payment, Subscription
from api.payment_services import (
    process_successful_payment,
)


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

        with self.settings(FLW_SECRET_HASH="test-secret",):
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

        self.assertEqual(
            response.status_code,
            200,
        )

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

    @patch("api.payment_views.verify_flutterwave_transaction")
    def test_webhook_rejects_wrong_amount(
        self,
        verify_transaction,
    ):
        payment = Payment.objects.create(
            organization=self.organization,
            subscription=self.subscription,
            tx_ref="fleet-wrong-amount",
            amount=Decimal("75000"),
            currency="UGX",
            plan="business",
            billing_cycle="monthly",
        )

        verify_transaction.return_value = {
            "id": 12346,
            "tx_ref": "fleet-wrong-amount",
            "flw_ref": "FLW-WRONG",
            "status": "successful",
            "amount": 100,
            "currency": "UGX",
        }

        with self.settings(FLW_SECRET_HASH="test-secret"):
            response = self.client.post(
                "/api/payments/flutterwave/webhook/",
                {
                    "event": "charge.completed",
                    "data": {
                        "id": 12346,
                        "tx_ref": "fleet-wrong-amount",
                    },
                },
                format="json",
                HTTP_VERIF_HASH="test-secret",
            )

        self.assertEqual(
            response.status_code,
            400,
        )

        payment.refresh_from_db()

        self.assertEqual(
            payment.status,
            "pending",
        )

        self.subscription.refresh_from_db()

        self.assertEqual(
            self.subscription.plan,
            "free",
        )

    @patch("api.payment_views.verify_flutterwave_transaction")
    def test_webhook_rejects_wrong_currency(
        self,
        verify_transaction,
    ):
        payment = Payment.objects.create(
            organization=self.organization,
            subscription=self.subscription,
            tx_ref="fleet-wrong-currency",
            amount=Decimal("75000"),
            currency="UGX",
            plan="business",
            billing_cycle="monthly",
        )

        verify_transaction.return_value = {
            "id": 12347,
            "tx_ref": "fleet-wrong-currency",
            "flw_ref": "FLW-CURRENCY",
            "status": "successful",
            "amount": 75000,
            "currency": "USD",
        }

        with self.settings(FLW_SECRET_HASH="test-secret"):
            response = self.client.post(
                "/api/payments/flutterwave/webhook/",
                {
                    "event": "charge.completed",
                    "data": {
                        "id": 12347,
                        "tx_ref": "fleet-wrong-currency",
                    },
                },
                format="json",
                HTTP_VERIF_HASH="test-secret",
            )

        self.assertEqual(
            response.status_code,
            400,
        )

    @patch("api.payment_views.verify_flutterwave_transaction")
    def test_webhook_rejects_wrong_transaction_reference(
        self,
        verify_transaction,
    ):
        payment = Payment.objects.create(
            organization=self.organization,
            subscription=self.subscription,
            tx_ref="fleet-real-reference",
            amount=Decimal("75000"),
            currency="UGX",
            plan="business",
            billing_cycle="monthly",
        )

        verify_transaction.return_value = {
            "id": 12348,
            "tx_ref": "fleet-attacker-reference",
            "flw_ref": "FLW-REF",
            "status": "successful",
            "amount": 75000,
            "currency": "UGX",
        }

        with self.settings(FLW_SECRET_HASH="test-secret"):
            response = self.client.post(
                "/api/payments/flutterwave/webhook/",
                {
                    "event": "charge.completed",
                    "data": {
                        "id": 12348,
                        "tx_ref": "fleet-real-reference",
                    },
                },
                format="json",
                HTTP_VERIF_HASH="test-secret",
            )

        self.assertEqual(
            response.status_code,
            400,
        )

    @patch("api.payment_views.verify_flutterwave_transaction")
    def test_duplicate_webhook_does_not_extend_subscription_twice(
        self,
        verify_transaction,
    ):
        payment = Payment.objects.create(
            organization=self.organization,
            subscription=self.subscription,
            tx_ref="fleet-duplicate",
            amount=Decimal("75000"),
            currency="UGX",
            plan="business",
            billing_cycle="monthly",
        )

        verify_transaction.return_value = {
            "id": 12349,
            "tx_ref": "fleet-duplicate",
            "flw_ref": "FLW-DUPLICATE",
            "status": "successful",
            "amount": 75000,
            "currency": "UGX",
        }

        with self.settings(FLW_SECRET_HASH="test-secret"):
            first_response = self.client.post(
                "/api/payments/flutterwave/webhook/",
                {
                    "event": "charge.completed",
                    "data": {
                        "id": 12349,
                        "tx_ref": "fleet-duplicate",
                    },
                },
                format="json",
                HTTP_VERIF_HASH="test-secret",
            )

        self.assertEqual(
            first_response.status_code,
            200,
        )

        self.subscription.refresh_from_db()

        first_expiry = (
            self.subscription.expires_at
        )

        with self.settings(FLW_SECRET_HASH="test-secret"):
            second_response = self.client.post(
                "/api/payments/flutterwave/webhook/",
                {
                    "event": "charge.completed",
                    "data": {
                        "id": 12349,
                        "tx_ref": "fleet-duplicate",
                    },
                },
                format="json",
                HTTP_VERIF_HASH="test-secret",
            )

        self.assertEqual(
            second_response.status_code,
            200,
        )

        self.subscription.refresh_from_db()

        self.assertEqual(
            self.subscription.expires_at,
            first_expiry,
        )

    @patch("api.payment_views.verify_flutterwave_transaction")
    def test_payment_status_verifies_pending_payment(
        self,
        verify_transaction,
    ):
        payment = Payment.objects.create(
            organization=self.organization,
            subscription=self.subscription,
            tx_ref="fleet-callback",
            amount=Decimal("75000"),
            currency="UGX",
            plan="business",
            billing_cycle="monthly",
        )

        verify_transaction.return_value = {
            "id": 12350,
            "tx_ref": "fleet-callback",
            "flw_ref": "FLW-CALLBACK",
            "status": "successful",
            "amount": 75000,
            "currency": "UGX",
        }

        response = self.client.get(
            f"/api/payments/status/"
            f"{payment.tx_ref}/",
            {
                "transaction_id": "12350",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        payment.refresh_from_db()

        self.assertEqual(
            payment.status,
            "successful",
        )

        self.subscription.refresh_from_db()

        self.assertEqual(
            self.subscription.plan,
            "business",
        )

    def test_payment_status_cannot_be_accessed_by_another_owner(self):
        other_user = User.objects.create_user(
            username="other-owner",
            password="StrongPass123!",
            email="other@example.com",
        )

        other_org = Organization.objects.create(
            owner=other_user,
            name="Other Fleet",
            slug="other-fleet",
        )

        other_subscription = Subscription.objects.create(
            organization=other_org,
            plan="free",
        )

        payment = Payment.objects.create(
            organization=self.organization,
            subscription=self.subscription,
            tx_ref="fleet-private-payment",
            amount=Decimal("75000"),
            currency="UGX",
            plan="business",
            billing_cycle="monthly",
        )

        self.client.force_authenticate(other_user)

        response = self.client.get(
            f"/api/payments/status/"
            f"{payment.tx_ref}/"
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    @patch("api.payment_views.verify_flutterwave_transaction")
    def test_failed_payment_does_not_activate_subscription(
        self,
        verify_transaction,
    ):
        payment = Payment.objects.create(
            organization=self.organization,
            subscription=self.subscription,
            tx_ref="fleet-failed",
            amount=Decimal("75000"),
            currency="UGX",
            plan="business",
            billing_cycle="monthly",
        )

        verify_transaction.return_value = {
            "id": 12351,
            "tx_ref": "fleet-failed",
            "flw_ref": "FLW-FAILED",
            "status": "failed",
            "amount": 75000,
            "currency": "UGX",
        }

        with self.settings(FLW_SECRET_HASH="test-secret"):
            response = self.client.post(
                "/api/payments/flutterwave/webhook/",
                {
                    "event": "charge.completed",
                    "data": {
                        "id": 12351,
                        "tx_ref": "fleet-failed",
                    },
                },
                format="json",
                HTTP_VERIF_HASH="test-secret",
            )

        self.assertEqual(
            response.status_code,
            200,
        )

        payment.refresh_from_db()

        self.assertEqual(
            payment.status,
            "failed",
        )

        self.subscription.refresh_from_db()

        self.assertEqual(
            self.subscription.plan,
            "free",
        )

    def test_provider_transaction_id_is_unique(self):
        first_payment = Payment.objects.create(
            organization=self.organization,
            subscription=self.subscription,
            tx_ref="fleet-provider-unique-1",
            amount=Decimal("75000"),
            currency="UGX",
            plan="business",
            billing_cycle="monthly",
            provider_transaction_id="FLW-UNIQUE-001",
        )

        self.assertIsNotNone(
            first_payment.pk
        )

        with self.assertRaises(
            IntegrityError
        ):
            Payment.objects.create(
                organization=self.organization,
                subscription=self.subscription,
                tx_ref="fleet-provider-unique-2",
                amount=Decimal("75000"),
                currency="UGX",
                plan="business",
                billing_cycle="monthly",
                provider_transaction_id="FLW-UNIQUE-001",
            )

    def test_multiple_pending_payments_can_have_no_provider_transaction_id(self,):
        first_payment = Payment.objects.create(
            organization=self.organization,
            subscription=self.subscription,
            tx_ref="fleet-pending-001",
            amount=Decimal("75000"),
            currency="UGX",
            plan="business",
            billing_cycle="monthly",
        )

        second_payment = Payment.objects.create(
            organization=self.organization,
            subscription=self.subscription,
            tx_ref="fleet-pending-002",
            amount=Decimal("75000"),
            currency="UGX",
            plan="business",
            billing_cycle="monthly",
        )

        self.assertIsNone(
            first_payment.provider_transaction_id
        )

        self.assertIsNone(
            second_payment.provider_transaction_id
        )

    @patch("api.payment_services.activate_subscription_for_payment")
    def test_successful_payment_processing_is_idempotent(self, activate_subscription,):
        activate_subscription.return_value = (
            self.subscription
        )

        payment = Payment.objects.create(
            organization=self.organization,
            subscription=self.subscription,
            tx_ref="fleet-idempotent-001",
            amount=Decimal("75000"),
            currency="UGX",
            plan="business",
            billing_cycle="monthly",
        )

        transaction_data = {
            "id": 900001,
            "tx_ref": "fleet-idempotent-001",
            "flw_ref": "FLW-IDEMPOTENT-001",
            "status": "successful",
            "amount": 75000,
            "currency": "UGX",
        }

        first_result = process_successful_payment(
            payment,
            transaction_data,
        )

        payment.refresh_from_db()

        second_result = process_successful_payment(
            payment,
            transaction_data,
        )

        self.assertEqual(
            first_result.pk,
            second_result.pk,
        )

        activate_subscription.assert_called_once()

    @patch("api.payment_services.activate_subscription_for_payment")
    def test_provider_transaction_cannot_be_reused(
        self,
        activate_subscription,
    ):
        activate_subscription.return_value = (
            self.subscription
        )

        first_payment = Payment.objects.create(
            organization=self.organization,
            subscription=self.subscription,
            tx_ref="fleet-provider-reuse-001",
            amount=Decimal("75000"),
            currency="UGX",
            plan="business",
            billing_cycle="monthly",
        )

        second_payment = Payment.objects.create(
            organization=self.organization,
            subscription=self.subscription,
            tx_ref="fleet-provider-reuse-002",
            amount=Decimal("75000"),
            currency="UGX",
            plan="business",
            billing_cycle="monthly",
        )

        transaction_data = {
            "id": 900002,
            "tx_ref": first_payment.tx_ref,
            "flw_ref": "FLW-REUSE-001",
            "status": "successful",
            "amount": 75000,
            "currency": "UGX",
        }

        process_successful_payment(
            first_payment,
            transaction_data,
        )

        transaction_data["tx_ref"] = (
            second_payment.tx_ref
        )

        with self.assertRaises(
            ValueError
        ):
            process_successful_payment(
                second_payment,
                transaction_data,
            )