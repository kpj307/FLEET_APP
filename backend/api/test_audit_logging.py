from unittest.mock import patch
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient, APITestCase
from rest_framework.exceptions import PermissionDenied
from rest_framework import status
from rest_framework.test import (
    APIClient,
    APIRequestFactory,
    APITestCase,
    force_authenticate,
)

from api.logging_utils import sanitize_log_data
from .models import Organization, Payment, Subscription

from api.exception_handlers import custom_exception_handler

from django.contrib.auth.models import User
from django.urls import reverse

from api.payment_services import (
    activate_subscription_for_payment,
    set_payment_status,
)


class AuditLoggingTests(TestCase):

    @patch("api.audit.audit_logger.info")
    def test_audit_event_is_logged(self, mock_info):
        from api.audit import log_audit_event

        log_audit_event(
            event="test.event",
            success=True,
        )

        mock_info.assert_called_once()

        args, kwargs = mock_info.call_args

        self.assertEqual(args[0], "Audit event")

        payload = kwargs["extra"]

        self.assertEqual(
            payload["event"],
            "test.event",
        )

        self.assertTrue(
            payload["success"]
        )


class SensitiveLoggingTests(TestCase):

    def test_sensitive_values_are_redacted(self):
        data = {
            "username": "testuser",
            "password": "super-secret",
            "access_token": "jwt-secret",
            "refresh_token": "refresh-secret",
            "nested": {
                "api_key": "secret-key",
            },
        }

        sanitized = sanitize_log_data(data)

        self.assertEqual(
            sanitized["username"],
            "testuser",
        )

        self.assertEqual(
            sanitized["password"],
            "[REDACTED]",
        )

        self.assertEqual(
            sanitized["access_token"],
            "[REDACTED]",
        )

        self.assertEqual(
            sanitized["refresh_token"],
            "[REDACTED]",
        )

        self.assertEqual(
            sanitized["nested"]["api_key"],
            "[REDACTED]",
        )


class SecretLoggingTests(TestCase):

    def test_secrets_never_appear_in_audit_log_message(self):
        secret_values = [
            "super-secret-password",
            "super-secret-access-token",
            "super-secret-refresh-token",
            "super-secret-api-key",
            "super-secret-signature",
            "super-secret-flutterwave-hash",
            "4111111111111111",
            "123",
        ]

        sanitized_data = sanitize_log_data(
            {
                "password": "super-secret-password",
                "access_token": "super-secret-access-token",
                "refresh_token": "super-secret-refresh-token",
                "api_key": "super-secret-api-key",
                "signature": "super-secret-signature",
                "flutterwave_secret_hash": (
                    "super-secret-flutterwave-hash"
                ),
                "card_number": "4111111111111111",
                "cvv": "123",
            }
        )

        log_message = repr(sanitized_data)

        for secret in secret_values:
            self.assertNotIn(
                secret,
                log_message,
            )

        self.assertIn(
            "[REDACTED]",
            log_message,
        )


class AuditSecurityTests(TestCase):

    @patch("api.audit.audit_logger.info")
    def test_password_is_not_logged(self, mock_info):
        from api.audit import log_audit_event

        log_audit_event(
            event="auth.login",
            success=True,
        )

        output = repr(mock_info.call_args)

        self.assertNotIn(
            "password",
            output.lower(),
        )

        self.assertNotIn(
            "secret",
            output.lower(),
        )


class AuthenticationAuditTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="audit-auth-user",
            password="StrongPass123!",
        )

        self.url = reverse("get_token")

    def post(self, request, *args, **kwargs):
        response = super().post(
            request,
            *args,
            **kwargs,
        )

        if response.status_code == 200:
            log_audit_event(
                event="authentication.succeeded",
                request=request,
                success=True,
                username=request.data.get("username"),
            )

        elif response.status_code == 401:
            log_audit_event(
                event="authentication.failed",
                request=request,
                success=False,
                username=request.data.get("username"),
                reason="invalid_credentials",
            )

        elif response.status_code == 429:
            log_audit_event(
                event="authentication.throttled",
                request=request,
                success=False,
                username=request.data.get("username"),
                reason="rate_limit_exceeded",
            )

        return response

    @patch("api.auth_views.log_audit_event")
    def test_failed_authentication_is_audited(
        self,
        mock_audit,
    ):
        response = self.client.post(
            self.url,
            {
                "username": "audit-auth-user",
                "password": "WrongPassword123!",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        mock_audit.assert_called_once()

        kwargs = mock_audit.call_args.kwargs

        self.assertEqual(
            kwargs["event"],
            "authentication.failed",
        )

        self.assertFalse(
            kwargs["success"],
        )

        self.assertEqual(
            kwargs["username"],
            "audit-auth-user",
        )

        self.assertEqual(
            kwargs["reason"],
            "invalid_credentials",
        )

    @patch("api.auth_views.log_audit_event")
    def test_failed_authentication_does_not_log_password(
        self,
        mock_audit,
    ):
        password = "SuperSecretPassword123!"

        response = self.client.post(
            self.url,
            {
                "username": "audit-auth-user",
                "password": password,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        logged_call = repr(
            mock_audit.call_args
        )

        self.assertNotIn(
            password,
            logged_call,
        )

    @patch("api.auth_views.log_audit_event")
    def test_successful_authentication_is_audited(
        self,
        mock_audit,
    ):
        response = self.client.post(
            self.url,
            {
                "username": "audit-auth-user",
                "password": "StrongPass123!",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        mock_audit.assert_called_once()

        kwargs = mock_audit.call_args.kwargs

        self.assertEqual(
            kwargs["event"],
            "authentication.succeeded",
        )

        self.assertTrue(
            kwargs["success"],
        )

        self.assertEqual(
            kwargs["username"],
            "audit-auth-user",
        )


class SubscriptionAuditTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="subscription-audit-user",
            password="StrongPass123!",
        )

        self.organization = Organization.objects.create(
            owner=self.user,
            name="Audit Fleet",
            slug="audit-fleet",
        )

        self.subscription = Subscription.objects.create(
            organization=self.organization,
            plan="free",
            status="active",
            billing_cycle="monthly",
        )

    @patch("api.payment_services.log_audit_event")
    def test_subscription_activation_is_audited(
        self,
        mock_audit,
    ):
        from .models import Payment
        from .payment_services import (
            activate_subscription_for_payment,
        )

        payment = Payment.objects.create(
            organization=self.organization,
            subscription=self.subscription,
            tx_ref="audit-activation-test",
            provider_transaction_id="FLW-AUDIT-ACTIVATION-001",
            amount=Decimal("50000.00"),
            currency="UGX",
            plan="business",
            billing_cycle="monthly",
            status="successful",
        )

        activate_subscription_for_payment(
            payment
        )

        mock_audit.assert_called_once()

        kwargs = mock_audit.call_args.kwargs

        self.assertEqual(
            kwargs["event"],
            "subscription.activated",
        )

        self.assertTrue(
            kwargs["success"]
        )

        self.assertEqual(
            kwargs["previous_plan"],
            "free",
        )

        self.assertEqual(
            kwargs["new_plan"],
            "business",
        )

    @patch("api.payment_services.log_audit_event")
    def test_subscription_plan_change_is_audited(
        self,
        mock_audit,
    ):
        from .models import Payment
        from .payment_services import (
            activate_subscription_for_payment,
        )

        self.subscription.plan = "starter"
        self.subscription.save(
            update_fields=["plan"]
        )

        payment = Payment.objects.create(
            organization=self.organization,
            subscription=self.subscription,
            tx_ref="audit-plan-change-test",
            provider_transaction_id="FLW-AUDIT-PLAN-CHANGE-001",
            amount=Decimal("100000.00"),
            currency="UGX",
            plan="professional",
            billing_cycle="monthly",
            status="successful",
        )

        activate_subscription_for_payment(
            payment
        )

        mock_audit.assert_called_once()

        kwargs = mock_audit.call_args.kwargs

        self.assertEqual(
            kwargs["event"],
            "subscription.plan_changed",
        )

        self.assertEqual(
            kwargs["previous_plan"],
            "starter",
        )

        self.assertEqual(
            kwargs["new_plan"],
            "professional",
        )


class PaymentAuditTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="payment-audit-user",
            password="StrongPass123!",
        )

        self.organization = Organization.objects.create(
            owner=self.user,
            name="Payment Audit Fleet",
            slug="payment-audit-fleet",
        )

        self.subscription = Subscription.objects.create(
            organization=self.organization,
            plan="free",
            status="active",
            billing_cycle="monthly",
        )

        self.payment = Payment.objects.create(
            organization=self.organization,
            subscription=self.subscription,
            tx_ref="payment-audit-test",
            amount=Decimal("10000.00"),
            currency="UGX",
            plan="business",
            billing_cycle="monthly",
            status="pending",
        )
    
    @patch("api.payment_services.log_audit_event")
    def test_successful_payment_is_audited(self, mock_audit):

        self.payment.provider_transaction_id = "provider-audit-test-123"

        set_payment_status(
            self.payment,
            "successful",
            update_fields=[
                "status",
                "provider_transaction_id",
            ],
        )

        mock_audit.assert_called_once()

        kwargs = mock_audit.call_args.kwargs

        self.assertEqual(
            kwargs["event"],
            "payment.successful",
        )

        self.assertTrue(
            kwargs["success"],
        )

        self.assertEqual(
            kwargs["previous_status"],
            "pending",
        )

        self.assertEqual(
            kwargs["new_status"],
            "successful",
        )

        self.assertEqual(
            kwargs["payment_id"],
            self.payment.id,
        )

        self.assertEqual(
            kwargs["organization_id"],
            self.organization.id,
        )

        self.assertEqual(
            kwargs["tx_ref"],
            self.payment.tx_ref,
        )

        self.assertEqual(
            kwargs["provider_transaction_id"],
            self.payment.provider_transaction_id,
        )

        self.assertEqual(
            kwargs["provider_reference"],
            self.payment.provider_reference,
        )

        self.assertEqual(
            kwargs["amount"],
            str(self.payment.amount),
        )

        self.assertEqual(
            kwargs["currency"],
            self.payment.currency,
        )

        self.assertEqual(
            kwargs["plan"],
            self.payment.plan,
        )

        self.assertEqual(
            kwargs["billing_cycle"],
            self.payment.billing_cycle,
        )

    @patch("api.payment_services.log_audit_event")
    def test_failed_payment_is_audited(self, mock_audit):

        set_payment_status(
            self.payment,
            "failed",
        )

        mock_audit.assert_called_once()

        kwargs = mock_audit.call_args.kwargs

        self.assertEqual(
            kwargs["event"],
            "payment.failed",
        )

        self.assertFalse(
            kwargs["success"],
        )

        self.assertEqual(
            kwargs["previous_status"],
            "pending",
        )

        self.assertEqual(
            kwargs["new_status"],
            "failed",
        )

    @patch("api.payment_services.log_audit_event")
    def test_cancelled_payment_is_audited(self, mock_audit):

        set_payment_status(
            self.payment,
            "cancelled",
        )

        mock_audit.assert_called_once()

        kwargs = mock_audit.call_args.kwargs

        self.assertEqual(
            kwargs["event"],
            "payment.cancelled",
        )

        self.assertFalse(
            kwargs["success"],
        )

        self.assertEqual(
            kwargs["previous_status"],
            "pending",
        )

        self.assertEqual(
            kwargs["new_status"],
            "cancelled",
        )

    @patch("api.payment_services.log_audit_event")
    def test_same_payment_status_is_not_audited(self, mock_audit):

        set_payment_status(
            self.payment,
            "pending",
        )

        mock_audit.assert_not_called()

    @patch("api.payment_services.log_audit_event")
    def test_payment_audit_does_not_include_provider_payload(
        self,
        mock_audit,
    ):
        self.payment.provider_transaction_id = (
            "provider-safe-test-001"
        )

        self.payment.provider_reference = (
            "provider-reference-001"
        )

        self.payment.provider_payload = {
            "status": "success",
            "secret_hash": "super-secret-hash",
            "authorization": "Bearer super-secret-token",
            "card_number": "4111111111111111",
            "cvv": "123",
        }

        self.payment.save(
            update_fields=[
                "provider_transaction_id",
                "provider_reference",
                "provider_payload",
            ]
        )

        set_payment_status(
            self.payment,
            "successful",
        )

        mock_audit.assert_called_once()

        kwargs = mock_audit.call_args.kwargs

        self.assertNotIn(
            "provider_payload",
            kwargs,
        )

        self.assertNotIn(
            "secret_hash",
            repr(kwargs),
        )

        self.assertNotIn(
            "super-secret-hash",
            repr(kwargs),
        )

        self.assertNotIn(
            "super-secret-token",
            repr(kwargs),
        )

        self.assertNotIn(
            "4111111111111111",
            repr(kwargs),
        )

        self.assertNotIn(
            "123",
            repr(kwargs),
        )


class AuthorizationAuditTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="authorization-audit-user",
            password="StrongPass123!",
        )

        self.factory = APIRequestFactory()

    @patch("api.exception_handlers.log_audit_event")
    def test_forbidden_request_is_audited(
        self,
        mock_audit,
    ):
        request = self.factory.get(
            "/api/protected/",
        )
        request.user = self.user

        force_authenticate(
            request,
            user=self.user,
        )

        from rest_framework.views import APIView

        response = custom_exception_handler(
            PermissionDenied(
                "You do not have permission."
            ),
            {
                "request": request,
                "view": APIView(),
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        mock_audit.assert_called_once()

        kwargs = mock_audit.call_args.kwargs

        self.assertEqual(
            kwargs["event"],
            "authorization.failed",
        )

        self.assertFalse(
            kwargs["success"],
        )

        self.assertEqual(
            kwargs["user"],
            self.user,
        )

        self.assertEqual(
            kwargs["status_code"],
            status.HTTP_403_FORBIDDEN,
        )

        self.assertEqual(
            kwargs["error_code"],
            "FORBIDDEN",
        )

        self.assertEqual(
            kwargs["view"],
            "APIView",
        )

    @patch("api.exception_handlers.log_audit_event")
    def test_forbidden_audit_does_not_log_sensitive_data(
        self,
        mock_audit,
    ):
        request = self.factory.get(
            "/api/protected/",
            HTTP_AUTHORIZATION=(
                "Bearer super-secret-token"
            ),
        )

        force_authenticate(
            request,
            user=self.user,
        )

        from rest_framework.views import APIView

        response = custom_exception_handler(
            PermissionDenied(
                "You do not have permission."
            ),
            {
                "request": request,
                "view": APIView(),
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        mock_audit.assert_called_once()

        logged_call = repr(
            mock_audit.call_args
        )

        self.assertNotIn(
            "super-secret-token",
            logged_call,
        )

