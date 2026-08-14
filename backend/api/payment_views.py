import hmac
import os
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django.shortcuts import get_object_or_404


import logging

from .models import Payment, Subscription
from .payment_services import (
    create_flutterwave_checkout,
    extend_subscription,
    verify_flutterwave_transaction,
    process_successful_payment,
)

logger = logging.getLogger(__name__)

class CreatePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        organization = request.user.organization

        plan = request.data.get("plan")
        billing_cycle = request.data.get(
            "billing_cycle",
            "monthly",
        )
        email = (
            request.data.get("email")
            or request.user.email
        )
        name = (
            request.data.get("name")
            or request.user.get_full_name()
            or request.user.username
        )

        if plan not in Subscription.PLAN_PRICES:
            return Response(
                {"detail": "Invalid subscription plan."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if plan == "free":
            return Response(
                {"detail": "The free plan does not require payment."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if billing_cycle not in {"monthly", "annual"}:
            return Response(
                {"detail": "Invalid billing cycle."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            tx_ref, amount, checkout_url = (
                create_flutterwave_checkout(
                    organization=organization,
                    plan=plan,
                    billing_cycle=billing_cycle,
                    email=email,
                    name=name,
                )
            )
        except Exception:
            logger.exception(
                "Flutterwave checkout initialization failed"
            )

            return Response(
                {
                    "detail": (
                        "We could not connect to the payment "
                        "provider. Please try again shortly."
                    )
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        payment = Payment.objects.create(
            organization=organization,
            subscription=organization.subscription,
            tx_ref=tx_ref,
            amount=amount,
            currency=organization.currency,
            plan=plan,
            billing_cycle=billing_cycle,
            checkout_url=checkout_url,
        )

        return Response(
            {
                "payment_id": payment.id,
                "tx_ref": payment.tx_ref,
                "amount": payment.amount,
                "currency": payment.currency,
                "checkout_url": payment.checkout_url,
                "status": payment.status,
            },
            status=status.HTTP_201_CREATED,
        )


class PaymentStatusView(APIView):
    permission_classes = [
        IsAuthenticated,
    ]

    def get(self, request, tx_ref):
        payment = get_object_or_404(
            Payment,
            tx_ref=tx_ref,
            organization=request.user.organization,
        )

        # Already processed.
        if payment.status == "successful":
            subscription = (
                payment.organization.subscription
            )

            return Response({
                "status": "successful",
                "plan": subscription.plan,
                "billing_cycle": (
                    subscription.billing_cycle
                ),
                "expires_at": (
                    subscription.expires_at
                ),
            })

        # Payment is still pending.
        #
        # Verify directly with Flutterwave. This is our
        # redirect/callback fallback in case the webhook
        # has not arrived yet.
        if payment.status == "pending":

            transaction_id = (
                request.query_params.get(
                    "transaction_id"
                )
            )

            if transaction_id:
                transaction_data = (
                    verify_flutterwave_transaction(
                        transaction_id
                    )
                )

                subscription = (
                    process_successful_payment(
                        payment,
                        transaction_data,
                    )
                )

                return Response({
                    "status": "successful",
                    "plan": subscription.plan,
                    "billing_cycle": (
                        subscription.billing_cycle
                    ),
                    "expires_at": (
                        subscription.expires_at
                    ),
                })

        return Response({
            "status": payment.status,
            "plan": payment.plan,
            "billing_cycle": (
                payment.billing_cycle
            ),
        })


class FlutterwaveWebhookView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @transaction.atomic
    def post(self, request):
        expected = os.environ.get(
            "FLW_SECRET_HASH",
            "",
        )
        received = request.headers.get("verif-hash", "")

        if not expected or not hmac.compare_digest(
            received,
            expected,
        ):
            return HttpResponse(
                status=401,
            )

        payload = request.data
        data = payload.get("data") or {}

        tx_ref = data.get("tx_ref")
        transaction_id = data.get("id")

        if not tx_ref or not transaction_id:
            return HttpResponse(status=400)

        payment = (
            Payment.objects.select_for_update()
            .filter(tx_ref=tx_ref)
            .first()
        )

        if not payment:
            # Do not create subscriptions from unknown references.
            return HttpResponse(status=200)

        if payment.status == "successful":
            return HttpResponse(status=200)

        try:
            verified = verify_flutterwave_transaction(
                transaction_id
            )
        except Exception:
            return HttpResponse(status=502)

        provider_status = str(
            verified.get("status", "")
        ).lower()

        if provider_status != "successful":
            payment.status = (
                "cancelled"
                if provider_status == "cancelled"
                else "failed"
            )
            payment.provider_transaction_id = str(
                verified.get("id", transaction_id)
            )
            payment.provider_reference = verified.get(
                "flw_ref",
                "",
            )
            payment.provider_payload = verified
            payment.save(
                update_fields=[
                    "status",
                    "provider_transaction_id",
                    "provider_reference",
                    "provider_payload",
                    "updated_at",
                ]
            )
            return HttpResponse(status=200)

        try:
            verified_amount = Decimal(
                str(verified.get("amount"))
            )
        except (InvalidOperation, TypeError):
            return HttpResponse(status=400)

        verified_currency = verified.get("currency")

        if (
            verified_amount != payment.amount
            or verified_currency != payment.currency
            or verified.get("tx_ref") != payment.tx_ref
        ):
            return HttpResponse(status=400)

        subscription = payment.subscription

        if not subscription:
            subscription = payment.organization.subscription

        subscription.plan = payment.plan
        subscription.billing_cycle = payment.billing_cycle

        # Extend from the existing expiry when the customer renews
        # before expiration; otherwise start from now.
        extend_subscription(
            subscription,
            payment.billing_cycle,
        )
        subscription.save(
            update_fields=[
                "plan",
                "billing_cycle",
                "status",
                "expires_at",
            ]
        )

        payment.status = "successful"
        payment.provider_transaction_id = str(
            verified.get("id", transaction_id)
        )
        payment.provider_reference = verified.get(
            "flw_ref",
            "",
        )
        payment.provider_payload = verified
        payment.paid_at = timezone.now()
        payment.save(
            update_fields=[
                "status",
                "provider_transaction_id",
                "provider_reference",
                "provider_payload",
                "paid_at",
                "updated_at",
            ]
        )

        return HttpResponse(status=200)
