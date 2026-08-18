from django.conf import settings
from django.core.management.commands.test import Command as DjangoTestCommand


class Command(DjangoTestCommand):
    """
    Fleet App test command.

    Forces Django into a non-production security profile
    so local environment variables cannot accidentally
    enable HTTPS redirects during tests.
    """

    def handle(self, *test_labels, **options):
        settings.DJANGO_ENV = "test"

        settings.SECURE_SSL_REDIRECT = False
        settings.SESSION_COOKIE_SECURE = False
        settings.CSRF_COOKIE_SECURE = False

        settings.SECURE_HSTS_SECONDS = 0
        settings.SECURE_HSTS_INCLUDE_SUBDOMAINS = False
        settings.SECURE_HSTS_PRELOAD = False

        return super().handle(
            *test_labels,
            **options,
        )