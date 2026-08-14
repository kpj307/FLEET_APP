from django.core.exceptions import ValidationError
from django.utils.text import slugify

from .models import Organization, Subscription


PLAN_LIMITS = {
    "free": {
        "max_vehicles": 3,
        "price_monthly": 0,
        "price_annual": 0,
        "reports": False,
        "exports": False,
    },
    "starter": {
        "max_vehicles": 5,
        "price_monthly": 25000,
        "price_annual": 250000,
        "reports": True,
        "exports": False,
    },
    "business": {
        "max_vehicles": 25,
        "price_monthly": 75000,
        "price_annual": 750000,
        "reports": True,
        "exports": True,
    },
    "professional": {
        "max_vehicles": 100,
        "price_monthly": 150000,
        "price_annual": 1500000,
        "reports": True,
        "exports": True,
    },
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
    limit = PLAN_LIMITS[organization.subscription.plan]["max_vehicles"]
    return organization.vehicles.count() < limit
