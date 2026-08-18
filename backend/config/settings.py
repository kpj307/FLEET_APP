"""
Django settings for config project.

Production-hardened configuration with environment-based
secrets and environment-specific security settings.
"""

from pathlib import Path
from datetime import timedelta
import os
import sys

from dotenv import load_dotenv
import dj_database_url


# ============================================================
# BASE CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv()


# ============================================================
# ENVIRONMENT HELPERS
# ============================================================

def env_bool(name, default=False):
    """
    Read a boolean environment variable safely.

    Examples:
        true, 1, yes, on -> True
        false, 0, no, off -> False
    """
    value = os.environ.get(name)

    if value is None:
        return default

    return value.strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def env_list(name, default=""):
    """
    Read a comma-separated environment variable.
    """
    value = os.environ.get(name, default)

    return [
        item.strip()
        for item in value.split(",")
        if item.strip()
    ]


# ============================================================
# ENVIRONMENT
# ============================================================

DJANGO_ENV = os.environ.get(
    "DJANGO_ENV",
    "development",
).strip().lower()

IS_PRODUCTION = (
    DJANGO_ENV == "production"
)

# Detect Django test execution without relying on
# DJANGO_SETTINGS_MODULE being changed.
IS_TESTING = (
    "test" in sys.argv
)

DEBUG = env_bool(
    "DJANGO_DEBUG",
    DJANGO_ENV != "production",
)


# ============================================================
# SECURITY / SECRET KEY
# ============================================================

SECRET_KEY = os.environ.get("SECRET_KEY")

if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY environment variable is required."
    )

if IS_PRODUCTION and DEBUG and not IS_TESTING:
    raise RuntimeError(
        "DEBUG must be False in production."
    )


# ============================================================
# ALLOWED HOSTS
# ============================================================

ALLOWED_HOSTS = env_list(
    "ALLOWED_HOSTS",
)

if IS_PRODUCTION and not IS_TESTING:

    if not ALLOWED_HOSTS:
        raise RuntimeError(
            "ALLOWED_HOSTS must be configured "
            "in production."
        )

    if "*" in ALLOWED_HOSTS:
        raise RuntimeError(
            "Wildcard ALLOWED_HOSTS is not permitted "
            "in production."
        )


# ============================================================
# FRONTEND
# ============================================================

FRONTEND_URL = os.environ.get(
    "FRONTEND_URL",
    "http://localhost:5173",
).rstrip("/")


# ============================================================
# FLUTTERWAVE
# ============================================================

FLW_PUBLIC_KEY = os.environ.get(
    "FLW_PUBLIC_KEY",
    "",
)

FLW_SECRET_KEY = os.environ.get(
    "FLW_SECRET_KEY",
    "",
)

FLW_SECRET_HASH = os.environ.get(
    "FLW_SECRET_HASH",
    "",
)

FLW_PAYMENT_PLAN_MONTHLY_ID = os.environ.get(
    "FLW_PAYMENT_PLAN_MONTHLY_ID",
    "",
)

FLW_PAYMENT_PLAN_ANNUAL_ID = os.environ.get(
    "FLW_PAYMENT_PLAN_ANNUAL_ID",
    "",
)

FLW_REDIRECT_URL = os.environ.get(
    "FLW_REDIRECT_URL",
    f"{FRONTEND_URL}/payment/callback",
)


# ============================================================
# APPLICATION DEFINITION
# ============================================================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",

    "corsheaders",

    "api",
]


MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",

    "whitenoise.middleware.WhiteNoiseMiddleware",

    "api.middleware.RequestContextMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",

    "django.middleware.common.CommonMiddleware",

    "django.middleware.csrf.CsrfViewMiddleware",

    "django.contrib.auth.middleware.AuthenticationMiddleware",

    "django.contrib.messages.middleware.MessageMiddleware",

    "django.middleware.clickjacking.XFrameOptionsMiddleware",

    "corsheaders.middleware.CorsMiddleware",
]


ROOT_URLCONF = "config.urls"


TEMPLATES = [
    {
        "BACKEND": (
            "django.template.backends.django."
            "DjangoTemplates"
        ),
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                (
                    "django.template.context_processors."
                    "request"
                ),
                (
                    "django.contrib.auth.context_processors."
                    "auth"
                ),
                (
                    "django.contrib.messages.context_processors."
                    "messages"
                ),
            ],
        },
    },
]


WSGI_APPLICATION = "config.wsgi.application"


# ============================================================
# DATABASE
# ============================================================

DATABASE_URL = os.environ.get(
    "DATABASE_URL"
)

if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            ssl_require=(
                IS_PRODUCTION
                and not IS_TESTING
            ),
        )
    }

else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


# ============================================================
# PASSWORD VALIDATION
# ============================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        ),
    },
]


# ============================================================
# DJANGO REST FRAMEWORK
# ============================================================

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication."
        "JWTAuthentication",
    ),

    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],

    "EXCEPTION_HANDLER": (
        "api.exception_handlers."
        "custom_exception_handler"
    ),

    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),

    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/min",
        "user": "300/min",

        "registration": "5/hour",
        "login": "10/min",
        "token_refresh": "20/min",

        "payment_create": "10/hour",
        "payment_status": "30/min",
    },
}


# ============================================================
# JWT
# ============================================================

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=30
    ),

    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=1
    ),

    "ROTATE_REFRESH_TOKENS": True,

    "BLACKLIST_AFTER_ROTATION": True,

    "UPDATE_LAST_LOGIN": True,

    "AUTH_HEADER_TYPES": (
        "Bearer",
    ),

    "LEEWAY": 10,
}


# ============================================================
# REDIS CACHE
# ============================================================

REDIS_URL = os.environ.get(
    "REDIS_URL"
)

if REDIS_URL:

    CACHES = {
        "default": {
            "BACKEND": (
                "django.core.cache.backends.redis."
                "RedisCache"
            ),

            "LOCATION": REDIS_URL,
        }
    }

else:

    CACHES = {
        "default": {
            "BACKEND": (
                "django.core.cache.backends.locmem."
                "LocMemCache"
            ),

            "LOCATION": "fleet-app-cache",
        }
    }


# ============================================================
# CORS
# ============================================================

CORS_ALLOW_ALL_ORIGINS = False

CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:5173",
)

CORS_ALLOW_CREDENTIALS = env_bool(
    "CORS_ALLOW_CREDENTIALS",
    default=False,
)

if (
    IS_PRODUCTION
    and not IS_TESTING
    and CORS_ALLOW_ALL_ORIGINS
):
    raise RuntimeError(
        "CORS_ALLOW_ALL_ORIGINS must be False "
        "in production."
    )


CORS_URLS_REGEX = r"^/api/.*$"


# ============================================================
# CSRF
# ============================================================

CSRF_TRUSTED_ORIGINS = env_list(
    "CSRF_TRUSTED_ORIGINS",
)


# ============================================================
# HTTPS / BROWSER SECURITY
# ============================================================

if IS_PRODUCTION and not IS_TESTING:
    # Production security is mandatory.
    # Do not allow environment variables to disable these.

    SECURE_SSL_REDIRECT = True

    SESSION_COOKIE_SECURE = True

    CSRF_COOKIE_SECURE = True

    SECURE_HSTS_SECONDS = 31536000

    SECURE_HSTS_INCLUDE_SUBDOMAINS = True

    SECURE_HSTS_PRELOAD = True

else:
    # Development/test configuration.

    SECURE_SSL_REDIRECT = env_bool(
        "SECURE_SSL_REDIRECT",
        False,
    )

    SESSION_COOKIE_SECURE = env_bool(
        "SESSION_COOKIE_SECURE",
        False,
    )

    CSRF_COOKIE_SECURE = env_bool(
        "CSRF_COOKIE_SECURE",
        False,
    )

    SECURE_HSTS_SECONDS = int(
        os.environ.get(
            "SECURE_HSTS_SECONDS",
            "0",
        )
    )

    SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool(
        "SECURE_HSTS_INCLUDE_SUBDOMAINS",
        False,
    )

    SECURE_HSTS_PRELOAD = env_bool(
        "SECURE_HSTS_PRELOAD",
        False,
    )


SECURE_PROXY_SSL_HEADER = (
    "HTTP_X_FORWARDED_PROTO",
    "https",
)

SECURE_CONTENT_TYPE_NOSNIFF = True

SECURE_REFERRER_POLICY = (
    "strict-origin-when-cross-origin"
)

SECURE_CROSS_ORIGIN_OPENER_POLICY = (
    "same-origin"
)

X_FRAME_OPTIONS = "DENY"


# ============================================================
# PRODUCTION SECURITY VALIDATION
# ============================================================

if IS_PRODUCTION and not IS_TESTING:

    if DEBUG:
        raise RuntimeError(
            "DEBUG must be False in production."
        )

    if not SECRET_KEY:
        raise RuntimeError(
            "SECRET_KEY is required in production."
        )

    if not ALLOWED_HOSTS:
        raise RuntimeError(
            "ALLOWED_HOSTS must be configured "
            "in production."
        )

    if "*" in ALLOWED_HOSTS:
        raise RuntimeError(
            "Wildcard ALLOWED_HOSTS is not permitted "
            "in production."
        )

    if not SECURE_SSL_REDIRECT:
        raise RuntimeError(
            "SECURE_SSL_REDIRECT must be True "
            "in production."
        )

    if not SESSION_COOKIE_SECURE:
        raise RuntimeError(
            "SESSION_COOKIE_SECURE must be True "
            "in production."
        )

    if not CSRF_COOKIE_SECURE:
        raise RuntimeError(
            "CSRF_COOKIE_SECURE must be True "
            "in production."
        )

    if SECURE_HSTS_SECONDS < 31536000:
        raise RuntimeError(
            "SECURE_HSTS_SECONDS must be at least "
            "31536000 in production."
        )

    if not SECURE_HSTS_INCLUDE_SUBDOMAINS:
        raise RuntimeError(
            "SECURE_HSTS_INCLUDE_SUBDOMAINS must be "
            "True in production."
        )

    if not SECURE_HSTS_PRELOAD:
        raise RuntimeError(
            "SECURE_HSTS_PRELOAD must be True "
            "in production."
        )

    if not CORS_ALLOWED_ORIGINS:
        raise RuntimeError(
            "CORS_ALLOWED_ORIGINS must be configured "
            "in production."
        )

    if not CSRF_TRUSTED_ORIGINS:
        raise RuntimeError(
            "CSRF_TRUSTED_ORIGINS must be configured "
            "in production."
        )


# ============================================================
# INTERNATIONALIZATION
# ============================================================

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# ============================================================
# STATIC FILES
# ============================================================

STATIC_URL = "/static/"

STATIC_ROOT = BASE_DIR / "staticfiles"


STORAGES = {
    "default": {
        "BACKEND": (
            "django.core.files.storage."
            "FileSystemStorage"
        ),
    },

    "staticfiles": {
        "BACKEND": (
            "whitenoise.storage."
            "CompressedManifestStaticFilesStorage"
        ),
    },
}


# ============================================================
# DEFAULT PRIMARY KEY
# ============================================================

DEFAULT_AUTO_FIELD = (
    "django.db.models.BigAutoField"
)


# ============================================================
# APPLICATION METADATA
# ============================================================

APP_NAME = os.environ.get(
    "APP_NAME",
    "Fleet App",
)

APP_VERSION = os.environ.get(
    "APP_VERSION",
    "1.0.0",
)


# ============================================================
# OBSERVABILITY / LOGGING
# ============================================================

LOG_DIR = BASE_DIR / os.environ.get(
    "LOG_DIR",
    "logs",
)

LOG_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


LOG_LEVEL = os.environ.get(
    "LOG_LEVEL",
    "INFO" if DEBUG else "WARNING",
).upper()


LOG_MAX_BYTES = int(
    os.environ.get(
        "LOG_MAX_BYTES",
        10 * 1024 * 1024,
    )
)


LOG_BACKUP_COUNT = int(
    os.environ.get(
        "LOG_BACKUP_COUNT",
        5,
    )
)


SLOW_REQUEST_THRESHOLD_MS = int(
    os.environ.get(
        "SLOW_REQUEST_THRESHOLD_MS",
        "1000",
    )
)


LOGGING_CONFIG = (
    "logging.config.dictConfig"
)


from .logging import LOGGING