from django.conf import settings
from django.test import SimpleTestCase
from django.test.utils import override_settings


class ProductionSecuritySettingsTests(
    SimpleTestCase
):

    @override_settings(
        DEBUG=False,
        ALLOWED_HOSTS=[
            "api.example.com",
        ],
        CORS_ALLOW_ALL_ORIGINS=False,
        CORS_ALLOWED_ORIGINS=[
            "https://app.example.com",
        ],
        CSRF_TRUSTED_ORIGINS=[
            "https://app.example.com",
        ],
        SECURE_SSL_REDIRECT=True,
        SESSION_COOKIE_SECURE=True,
        CSRF_COOKIE_SECURE=True,
        SECURE_HSTS_SECONDS=31536000,
        SECURE_HSTS_INCLUDE_SUBDOMAINS=True,
        SECURE_HSTS_PRELOAD=False,
    )
    def test_production_security_configuration(self):
        from django.conf import settings

        self.assertFalse(settings.DEBUG)

        self.assertNotIn(
            "*",
            settings.ALLOWED_HOSTS,
        )

        self.assertFalse(
            settings.CORS_ALLOW_ALL_ORIGINS
        )

        self.assertTrue(
            settings.SECURE_SSL_REDIRECT
        )

        self.assertTrue(
            settings.SESSION_COOKIE_SECURE
        )

        self.assertTrue(
            settings.CSRF_COOKIE_SECURE
        )

        self.assertEqual(
            settings.SECURE_HSTS_SECONDS,
            31536000,
        )

        self.assertTrue(
            settings.SECURE_HSTS_INCLUDE_SUBDOMAINS
        )

    @override_settings(
        ALLOWED_HOSTS=["*"],
    )
    def test_wildcard_hosts_are_not_production_safe(self):
        from django.conf import settings

        self.assertIn(
            "*",
            settings.ALLOWED_HOSTS,
        )

    @override_settings(
        CORS_ALLOW_ALL_ORIGINS=True,
    )
    def test_wildcard_cors_is_not_production_safe(self):
        from django.conf import settings

        self.assertTrue(
            settings.CORS_ALLOW_ALL_ORIGINS
        )


class TestEnvironmentIsolationTests(
    SimpleTestCase
):

    def test_test_environment_disables_https_redirect(self):
        self.assertFalse(
            settings.SECURE_SSL_REDIRECT
        )

    def test_test_environment_disables_secure_session_cookie(
        self,
    ):
        self.assertFalse(
            settings.SESSION_COOKIE_SECURE
        )

    def test_test_environment_disables_secure_csrf_cookie(
        self,
    ):
        self.assertFalse(
            settings.CSRF_COOKIE_SECURE
        )

    def test_test_environment_disables_hsts(self):
        self.assertEqual(
            settings.SECURE_HSTS_SECONDS,
            0,
        )


class ProductionSecurityTests(SimpleTestCase):

    @override_settings(
        DEBUG=False,
        ALLOWED_HOSTS=["api.example.com"],
        CORS_ALLOW_ALL_ORIGINS=False,
        CORS_ALLOWED_ORIGINS=[
            "https://app.example.com",
        ],
        CSRF_TRUSTED_ORIGINS=[
            "https://app.example.com",
        ],
        SECURE_SSL_REDIRECT=True,
        SESSION_COOKIE_SECURE=True,
        CSRF_COOKIE_SECURE=True,
        SECURE_HSTS_SECONDS=31536000,
        SECURE_HSTS_INCLUDE_SUBDOMAINS=True,
        SECURE_HSTS_PRELOAD=True,
    )
    def test_production_security_profile(self):
        from django.conf import settings

        self.assertFalse(settings.DEBUG)

        self.assertNotIn(
            "*",
            settings.ALLOWED_HOSTS,
        )

        self.assertFalse(
            settings.CORS_ALLOW_ALL_ORIGINS
        )

        self.assertTrue(
            settings.SECURE_SSL_REDIRECT
        )

        self.assertTrue(
            settings.SESSION_COOKIE_SECURE
        )

        self.assertTrue(
            settings.CSRF_COOKIE_SECURE
        )

        self.assertGreaterEqual(
            settings.SECURE_HSTS_SECONDS,
            31536000,
        )

        self.assertTrue(
            settings.SECURE_HSTS_INCLUDE_SUBDOMAINS
        )

        self.assertTrue(
            settings.SECURE_HSTS_PRELOAD
        )


class InsecureProductionConfigurationTests(
    SimpleTestCase
):

    @override_settings(
        DEBUG=True,
    )
    def test_debug_must_not_be_enabled_in_production(self):
        from django.conf import settings

        self.assertTrue(settings.DEBUG)

    @override_settings(
        ALLOWED_HOSTS=["*"],
    )
    def test_wildcard_hosts_are_detectable(self):
        from django.conf import settings

        self.assertIn(
            "*",
            settings.ALLOWED_HOSTS,
        )

    @override_settings(
        CORS_ALLOW_ALL_ORIGINS=True,
    )
    def test_wildcard_cors_is_detectable(self):
        from django.conf import settings

        self.assertTrue(
            settings.CORS_ALLOW_ALL_ORIGINS
        )

    @override_settings(
        SECURE_SSL_REDIRECT=False,
    )
    def test_missing_https_redirect_is_detectable(self):
        from django.conf import settings

        self.assertFalse(
            settings.SECURE_SSL_REDIRECT
        )

    @override_settings(
        SESSION_COOKIE_SECURE=False,
    )
    def test_insecure_session_cookie_is_detectable(self):
        from django.conf import settings

        self.assertFalse(
            settings.SESSION_COOKIE_SECURE
        )

    @override_settings(
        CSRF_COOKIE_SECURE=False,
    )
    def test_insecure_csrf_cookie_is_detectable(self):
        from django.conf import settings

        self.assertFalse(
            settings.CSRF_COOKIE_SECURE
        )