from django.core.exceptions import ValidationError
from django.utils.text import slugify

from .models import Organization, Subscription

PLAN_LIMITS = {
    plan: {
        "max_vehicles": int(values["max_vehicles"]),
        "price_monthly": values["monthly"],
        "price_annual": values["annual"],
        "reports": plan != "free",
        "exports": plan in {
            "business",
            "professional",
        },
    }
    for plan, values in Subscription.PLAN_PRICES.items()
}

def unique_slug(name):
    base = slugify(name) or "fleet"
    slug = base
    counter = 2

    while Organization.objects.filter(slug=slug).exists():
        slug = f"{base}-{counter}"
        counter += 1

    return slug


def create_owner_organization(user, business_name):
    name = business_name.strip()

    if not name:
        raise ValidationError(
            {"business_name": "Business name is required."}
        )

    organization = Organization.objects.create(
        owner=user,
        name=name,
        slug=unique_slug(name),
    )

    Subscription.objects.create(
        organization=organization,
        plan="free",
    )

    return organization


def can_add_vehicle(organization):
    subscription = organization.subscription

    # Make sure expired subscriptions are downgraded
    # before calculating the vehicle limit.
    subscription.refresh_status()

    limit = PLAN_LIMITS[
        subscription.plan
    ]["max_vehicles"]

    return organization.vehicles.count() < limit
