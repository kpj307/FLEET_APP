import secrets
from datetime import timedelta
from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings
from django.utils import timezone
from django.db import transaction

from .audit import log_audit_event
from .models import Payment, Subscription


FLUTTERWAVE_BASE_URL = "https://api.flutterwave.com/v3"

def audit_payment_status_change(
    *,
    payment,
    previous_status,
    new_status,
    request=None,
    **extra,
):
    """
    Record a payment lifecycle status change.

    Only business-safe payment metadata is included.

    Never include:
        - provider_payload
        - secret keys
        - authorization headers
        - payment signatures
        - card numbers
        - CVV
        - access/refresh tokens
    """

    if previous_status == new_status:
        return

    log_audit_event(
        event=f"payment.{new_status}",
        success=new_status == "successful",
        request=request,
        user_id=payment.organization.owner_id,
        organization_id=payment.organization_id,
        subscription_id=payment.subscription_id,
        payment_id=payment.id,

        # Safe payment identifiers
        tx_ref=payment.tx_ref,
        provider_transaction_id=(
            payment.provider_transaction_id
        ),
        provider_reference=(
            payment.provider_reference
        ),

        # Payment business information
        amount=str(payment.amount),
        currency=payment.currency,
        plan=payment.plan,
        billing_cycle=payment.billing_cycle,

        # Lifecycle information
        previous_status=previous_status,
        new_status=new_status,

        **extra,
    )
    
def set_payment_status(
    payment,
    new_status,
    *,
    request=None,
    update_fields=None,
):
    if payment.status == new_status:
        return payment

    if new_status == "successful":
        if not payment.provider_transaction_id:
            raise ValueError(
                "Successful payments require "
                "provider_transaction_id."
            )

    previous_status = payment.status

    payment.status = new_status

    fields = list(update_fields or [])

    if "status" not in fields:
        fields.append("status")

    if "updated_at" not in fields:
        fields.append("updated_at")

    payment.save(update_fields=fields)

    audit_payment_status_change(
        payment=payment,
        previous_status=previous_status,
        new_status=new_status,
        request=request,
    )

    return payment

def flutterwave_headers():
    secret = getattr(
        settings,
        "FLW_SECRET_KEY",
        "",
    ).strip()

    if not secret:
        raise RuntimeError(
            "FLW_SECRET_KEY is not configured."
        )

    return {
        "Authorization": f"Bearer {secret}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

def plan_amount(plan, billing_cycle):
    subscription = Subscription.PLAN_PRICES.get(plan)
    if not subscription:
        raise ValueError("Invalid subscription plan.")

    return (
        subscription["annual"]
        if billing_cycle == "annual"
        else subscription["monthly"]
    )

def create_transaction_reference(organization_id):
    return (
        f"fleet-{organization_id}-"
        f"{timezone.now().strftime('%Y%m%d%H%M%S')}-"
        f"{secrets.token_urlsafe(8)}"
    )

def create_flutterwave_checkout(
    *,
    organization,
    plan,
    billing_cycle,
    email,
    name,
):
    amount = plan_amount(plan, billing_cycle)
    tx_ref = create_transaction_reference(organization.id)

    payload = {
        "tx_ref": tx_ref,
        "amount": str(amount),
        "currency": organization.currency,
        "redirect_url": settings.FLW_REDIRECT_URL,
        "customer": {
            "email": email,
            "name": name,
        },
        "payment_options": "card,mobilemoneyuganda",
        "customizations": {
            "title": "Fleet Tracker",
            "description": f"{plan.title()} fleet subscription",
        },
        "meta": {
            "organization_id": organization.id,
            "plan": plan,
            "billing_cycle": billing_cycle,
        },
    }

    # Optional Flutterwave payment-plan IDs can be supplied for recurring
    # card subscriptions. Mobile-money customers can use the same checkout
    # for renewal, subject to the payment methods supported on the account.
    payment_plan = (
        settings.FLW_PAYMENT_PLAN_MONTHLY_ID
        if billing_cycle == "monthly"
        else settings.FLW_PAYMENT_PLAN_ANNUAL_ID
    )

    if payment_plan:
        payload["payment_plan"] = payment_plan

    try:
        response = requests.post(
            f"{FLUTTERWAVE_BASE_URL}/payments",
            headers=flutterwave_headers(),
            json=payload,
            timeout=30,
        )
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(
            "Unable to connect to Flutterwave."
        ) from exc

    if not response.ok:
        try:
            error_data = response.json()
        except ValueError:
            error_data = {}

        raise RuntimeError(
            error_data.get("message")
            or "Flutterwave payment initialization failed."
        )
    data = response.json()

    if data.get("status") != "success":
        raise RuntimeError(
            data.get("message") or "Flutterwave checkout creation failed."
        )

    return tx_ref, amount, data["data"]["link"]

def verify_flutterwave_transaction(transaction_id):
    """
    Verify a Flutterwave transaction by transaction ID.
    """

    if not transaction_id:
        raise ValueError(
            "Flutterwave transaction ID is required."
        )

    response = requests.get(
        f"{FLUTTERWAVE_BASE_URL}/transactions/"
        f"{transaction_id}/verify",
        headers=flutterwave_headers(),
        timeout=30,
    )

    if not response.ok:
        try:
            data = response.json()
        except ValueError:
            data = {}

        raise RuntimeError(
            data.get("message")
            or "Flutterwave transaction verification failed."
        )

    data = response.json()

    if data.get("status") != "success":
        raise RuntimeError(
            data.get("message")
            or "Transaction verification failed."
        )

    transaction_data = data.get("data")

    if not transaction_data:
        raise RuntimeError(
            "Flutterwave returned no transaction data."
        )

    return transaction_data

def verify_flutterwave_transaction_by_reference(tx_ref):
    """
    Verify a Flutterwave transaction using our transaction reference.
    """

    if not tx_ref:
        raise ValueError(
            "Transaction reference is required."
        )

    response = requests.get(
        f"{FLUTTERWAVE_BASE_URL}/transactions/"
        "verify_by_reference",
        params={
            "tx_ref": tx_ref,
        },
        headers=flutterwave_headers(),
        timeout=30,
    )

    if not response.ok:
        try:
            data = response.json()
        except ValueError:
            data = {}

        raise RuntimeError(
            data.get("message")
            or "Flutterwave transaction verification failed."
        )

    response_data = response.json()

    if response_data.get("status") != "success":
        raise RuntimeError(
            response_data.get("message")
            or "Flutterwave transaction verification failed."
        )

    transaction_data = response_data.get("data")

    if not transaction_data:
        raise RuntimeError(
            "Flutterwave returned no transaction data."
        )

    return transaction_data

@transaction.atomic
def activate_subscription_for_payment(payment):
    """
    Activate the organization's subscription after a
    successfully verified payment.

    Safe to call repeatedly for the same successful payment.
    """

    if payment.status != "successful":
        raise ValueError(
            "Payment must be successful before activation."
        )

    subscription = (
        Subscription.objects
        .select_for_update()
        .get(
            pk=payment.subscription_id
        )
    )
    previous_plan = subscription.plan

    previous_billing_cycle = subscription.billing_cycle
    previous_status = subscription.status
    previous_expires_at = subscription.expires_at

    organization = payment.organization

    current_time = timezone.now()

    if payment.billing_cycle == "annual":
        duration = timedelta(days=365)
    else:
        duration = timedelta(days=30)

    if (
        subscription.status == "active"
        and subscription.expires_at
        and subscription.expires_at > current_time
    ):
        expires_at = (
            subscription.expires_at + duration
        )
    else:
        expires_at = current_time + duration

    subscription.plan = payment.plan
    subscription.billing_cycle = (
        payment.billing_cycle
    )
    subscription.status = "active"
    subscription.expires_at = expires_at

    subscription.save(
        update_fields=[
            "plan",
            "billing_cycle",
            "status",
            "expires_at",
        ]
    )

    if previous_plan == "free" and subscription.plan != "free":
        event = "subscription.activated"
    elif previous_plan != subscription.plan:
        event = "subscription.plan_changed"
    else:
        event = "subscription.changed"

    log_audit_event(
        event=event,
        success=True,
        request=getattr(payment, "_request", None),
        user_id=payment.organization.owner_id,
        organization_id=payment.organization_id,
        subscription_id=subscription.id,
        payment_id=payment.id,
        previous_plan=previous_plan,
        new_plan=subscription.plan,
    )

    if payment.subscription_id != subscription.id:
        payment.subscription = subscription

        payment.save(
            update_fields=[
                "subscription",
                "updated_at",
            ]
        )

    return subscription

@transaction.atomic
def process_successful_payment(
    payment,
    transaction_data,
):
    """
    Process a verified Flutterwave transaction exactly once.

    This function is idempotent:
    processing the same local Payment repeatedly will not
    extend the subscription repeatedly.
    """

    # Lock the local payment row.
    payment = (
        Payment.objects
        .select_for_update()
        .select_related(
            "organization",
            "subscription",
        )
        .get(pk=payment.pk)
    )

    # --------------------------------------------------
    # IDEMPOTENCY
    # --------------------------------------------------

    if payment.status == "successful":
        subscription = payment.subscription

        if subscription is None:
            subscription = (
                payment.organization.subscription
            )

        return subscription

    # --------------------------------------------------
    # VALIDATE PROVIDER RESPONSE
    # --------------------------------------------------

    provider_status = str(
        transaction_data.get("status", "")
    ).lower()

    if provider_status != "successful":
        raise ValueError(
            "Flutterwave transaction is not successful."
        )

    provider_tx_ref = (
        transaction_data.get("tx_ref")
    )

    if provider_tx_ref != payment.tx_ref:
        raise ValueError(
            "Transaction reference does not match."
        )

    provider_currency = (
        transaction_data.get("currency")
    )

    if provider_currency != payment.currency:
        raise ValueError(
            "Transaction currency does not match."
        )

    try:
        provider_amount = Decimal(
            str(
                transaction_data.get(
                    "amount",
                    "0",
                )
            )
        )
    except (
        InvalidOperation,
        TypeError,
    ):
        raise ValueError(
            "Invalid transaction amount."
        )

    if provider_amount != payment.amount:
        raise ValueError(
            "Transaction amount does not match."
        )

    provider_transaction_id = str(
        transaction_data.get("id", "")
    ).strip()

    if not provider_transaction_id:
        raise ValueError(
            "Flutterwave transaction ID is missing."
        )

    # --------------------------------------------------
    # PROVIDER TRANSACTION INTEGRITY
    # --------------------------------------------------

    existing_payment = (
        Payment.objects
        .select_for_update()
        .filter(
            provider_transaction_id=
            provider_transaction_id,
        )
        .exclude(pk=payment.pk)
        .first()
    )

    if existing_payment:
        raise ValueError(
            "Flutterwave transaction has already "
            "been associated with another payment."
        )

    # --------------------------------------------------
    # RECORD PAYMENT
    # --------------------------------------------------

    payment.status = "successful"

    payment.provider_transaction_id = (
        provider_transaction_id
    )

    payment.provider_reference = (
        transaction_data.get(
            "flw_ref",
            "",
        )
        or ""
    )

    payment.provider_payload = transaction_data
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

    # --------------------------------------------------
    # LOCK SUBSCRIPTION
    # --------------------------------------------------

    subscription = (
        Subscription.objects
        .select_for_update()
        .get(
            pk=payment.subscription_id
        )
    )

    # Attach the locked instance to the payment object
    # used by the activation function.
    payment.subscription = subscription

    # --------------------------------------------------
    # ACTIVATE ONCE
    # --------------------------------------------------

    return activate_subscription_for_payment(
        payment
    )

def subscription_period(billing_cycle):
    if billing_cycle == "annual":
        return timedelta(days=365)

    return timedelta(days=30)

def extend_subscription(subscription, billing_cycle):
    current = subscription.expires_at
    now = timezone.now()

    start = current if current and current > now else now

    subscription.expires_at = (
        start + subscription_period(billing_cycle)
    )
    subscription.status = "active"
    subscription.billing_cycle = billing_cycle
    return subscription
