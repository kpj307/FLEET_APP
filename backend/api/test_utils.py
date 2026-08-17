from django.contrib.auth.models import User

from .models import Organization, Subscription


def create_test_owner(
    username="testowner",
    email="testowner@example.com",
):
    user = User.objects.create_user(
        username=username,
        email=email,
        password="CorrectPassword123!",
    )

    # Use the exact Organization/Subscription creation
    # logic currently used by test_payments.py.

    return user