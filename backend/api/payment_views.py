import hmac
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django.shortcuts import get_object_or_404


import logging

from .models import Payment, Subscription
from .payment_services import (
    create_flutterwave_checkout,
    process_successful_payment,
    verify_flutterwave_transaction,
    verify_flutterwave_transaction_by_reference,
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
            transaction_id = request.query_params.get(
                "transaction_id"
            )

            # Flutterwave has not supplied a transaction ID yet.
            # Keep the payment pending rather than making an
            # unnecessary provider request.
            if not transaction_id:
                return Response(
                    {
                        "status": payment.status,
                        "plan": payment.plan,
                        "billing_cycle": payment.billing_cycle,
                    }
                )

            try:
                transaction_data = (
                    verify_flutterwave_transaction(
                        transaction_id
                    )
                )

                subscription = process_successful_payment(
                    payment,
                    transaction_data,
                )

                return Response(
                    {
                        "status": "successful",
                        "plan": subscription.plan,
                        "billing_cycle": (
                            subscription.billing_cycle
                        ),
                        "expires_at": (
                            subscription.expires_at
                        ),
                    }
                )

            except ValueError as exc:
                logger.warning(
                    "Payment verification failed for %s: %s",
                    payment.tx_ref,
                    exc,
                )

                return Response(
                    {
                        "status": payment.status,
                        "detail": str(exc),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            except Exception:
                logger.exception(
                    "Payment verification error for %s",
                    payment.tx_ref,
                )

                return Response(
                    {
                        "status": payment.status,
                        "detail": (
                            "Payment verification is temporarily "
                            "unavailable."
                        ),
                    },
                    status=status.HTTP_502_BAD_GATEWAY,
                )

        try:
            if transaction_id:
                transaction_data = (
                    verify_flutterwave_transaction(
                        transaction_id
                    )
                )
            else:
                transaction_data = (
                    verify_flutterwave_transaction_by_reference(
                        payment.tx_ref
                    )
                )

                subscription = process_successful_payment(
                    payment,
                    transaction_data,
                )

            return Response(
                {
                    "status": "successful",
                    "plan": subscription.plan,
                    "billing_cycle": (
                        subscription.billing_cycle
                    ),
                    "expires_at": (
                        subscription.expires_at
                    ),
                }
            )

        except ValueError as exc:
            logger.warning(
                "Payment verification failed for %s: %s",
                payment.tx_ref,
                exc,
            )

            return Response(
                {
                    "status": payment.status,
                    "detail": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception:
            logger.exception(
                "Payment verification error for %s",
                payment.tx_ref,
            )

            return Response(
                {
                    "status": payment.status,
                    "detail": (
                        "Payment verification is temporarily "
                        "unavailable."
                    ),
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )


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

    def post(self, request):
        expected = getattr(
            settings,
            "FLW_SECRET_HASH",
            "",
        ).strip()

        received = request.headers.get(
            "verif-hash",
            "",
        ).strip()

        if (
            not expected
            or not received
            or not hmac.compare_digest(
                received,
                expected,
            )
        ):
            return HttpResponse(
                status=401
            )

        payload = request.data
        data = payload.get("data") or {}

        tx_ref = data.get("tx_ref")
        transaction_id = data.get("id")

        if not tx_ref:
            return HttpResponse(
                status=400
            )

        payment = (
            Payment.objects
            .select_for_update()
            .filter(tx_ref=tx_ref)
            .first()
        )

        # Unknown transaction references must never
        # create a subscription.
        if not payment:
            return HttpResponse(
                status=200
            )

        # Webhook retries are expected.
        if payment.status == "successful":
            return HttpResponse(
                status=200
            )

        if not transaction_id:
            return HttpResponse(
                status=400
            )

        try:
            verified = (
                verify_flutterwave_transaction(
                    transaction_id
                )
            )

        except Exception:
            logger.exception(
                "Flutterwave verification failed for %s",
                tx_ref,
            )

            return HttpResponse(
                status=502
            )

        provider_status = str(
            verified.get("status", "")
        ).lower()

        # -------------------------------------------------
        # FAILED / CANCELLED PAYMENT
        # -------------------------------------------------

        if provider_status != "successful":
            payment.status = (
                "cancelled"
                if provider_status == "cancelled"
                else "failed"
            )

            payment.provider_transaction_id = str(
                verified.get(
                    "id",
                    transaction_id,
                )
            )

            payment.provider_reference = (
                verified.get(
                    "flw_ref",
                    "",
                )
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

            # This was a valid webhook. The payment simply
            # wasn't successful.
            return HttpResponse(
                status=200
            )

        # -------------------------------------------------
        # SUCCESSFUL PAYMENT
        # -------------------------------------------------

        try:
            verified_amount = Decimal(
                str(
                    verified.get("amount")
                )
            )

        except (
            InvalidOperation,
            TypeError,
        ):
            return HttpResponse(
                status=400
            )

        verified_currency = (
            verified.get("currency")
        )

        verified_tx_ref = (
            verified.get("tx_ref")
        )

        # Never trust the amount/currency/reference
        # supplied by the client or webhook alone.
        if verified_amount != payment.amount:
            logger.warning(
                "Payment amount mismatch for %s",
                tx_ref,
            )
            return HttpResponse(
                status=400
            )

        if verified_currency != payment.currency:
            logger.warning(
                "Payment currency mismatch for %s",
                tx_ref,
            )
            return HttpResponse(
                status=400
            )

        if verified_tx_ref != payment.tx_ref:
            logger.warning(
                "Payment reference mismatch for %s",
                tx_ref,
            )
            return HttpResponse(
                status=400
            )

        try:
            process_successful_payment(
                payment,
                verified,
            )

        except ValueError as exc:
            logger.warning(
                "Invalid Flutterwave payment %s: %s",
                tx_ref,
                exc,
            )

            return HttpResponse(
                status=400
            )

        except Exception:
            logger.exception(
                "Payment processing failed for %s",
                tx_ref,
            )

            return HttpResponse(
                status=500
            )

        return HttpResponse(
            status=200
        )

