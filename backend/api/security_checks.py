from django.conf import settings


def validate_production_settings():
    """
    Validate security-critical settings.

    Intended for deployment/startup checks.
    """

    errors = []

    if settings.DEBUG:
        errors.append(
            "DEBUG must be False in production."
        )

    if not settings.SECRET_KEY:
        errors.append(
            "SECRET_KEY must be configured."
        )

    if "*" in settings.ALLOWED_HOSTS:
        errors.append(
            "ALLOWED_HOSTS must not contain '*' "
            "in production."
        )

    if getattr(
        settings,
        "CORS_ALLOW_ALL_ORIGINS",
        False,
    ):
        errors.append(
            "CORS_ALLOW_ALL_ORIGINS must be False "
            "in production."
        )

    return errors