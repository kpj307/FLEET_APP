"""
Django settings for config project.

Production-hardened configuration with environment-based secrets
and environment-specific security settings.
"""

from pathlib import Path
from datetime import timedelta
import os

from dotenv import load_dotenv
import dj_database_url


# ============================================================
# BASE CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv()


def env_bool(name, default=False):
    """
    Read a boolean environment variable safely.

    Examples:
        TRUE, true, 1, yes, on -> True
        FALSE, false, 0, no, off -> False
    """
    value = os.environ.get(name)

    if value is None:
        return default

    return value.strip().lower() in {
        "true",
        "1",
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

DEBUG = env_bool(
    "DJANGO_DEBUG",
    default=False,
)

ENVIRONMENT = os.environ.get(
    "DJANGO_ENVIRONMENT",
    "development",
).strip().lower()


# ============================================================
# SECURITY
# ============================================================

# IMPORTANT:
# Generate a new production SECRET_KEY.
#
# Do NOT commit it to Git.
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
)

if not SECRET_KEY:
    if DEBUG:
        raise RuntimeError(
            "DJANGO_SECRET_KEY must be configured."
        )

    raise RuntimeError(
        "DJANGO_SECRET_KEY is required in production."
    )


ALLOWED_HOSTS = env_list(
    "DJANGO_ALLOWED_HOSTS",
    "localhost,127.0.0.1",
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
    "corsheaders",
    "api",

    "rest_framework_simplejwt.token_blacklist",
]


MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",

    # Request ID must be available to all downstream
    # middleware and application code.
    "api.middleware.RequestIDMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",

    "corsheaders.middleware.CorsMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
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
    "DATABASE_URL",
)

if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
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
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),

    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],

    "EXCEPTION_HANDLER": (
        "api.exception_handlers.custom_exception_handler"
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

    "AUTH_HEADER_TYPES": ("Bearer",),

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

CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
)

CORS_ALLOW_CREDENTIALS = env_bool(
    "CORS_ALLOW_CREDENTIALS",
    default=False,
)

CORS_URLS_REGEX = r"^/api/.*$"


# ============================================================
# CSRF
# ============================================================

CSRF_TRUSTED_ORIGINS = env_list(
    "CSRF_TRUSTED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
)


# ============================================================
# SECURITY HEADERS
# ============================================================

SECURE_CONTENT_TYPE_NOSNIFF = True

X_FRAME_OPTIONS = "DENY"

SECURE_REFERRER_POLICY = "same-origin"

SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"


# ------------------------------------------------------------
# HTTPS settings
# ------------------------------------------------------------
#
# Keep these disabled for local HTTP development.
# Enable them in production behind HTTPS.
#

SECURE_SSL_REDIRECT = env_bool(
    "SECURE_SSL_REDIRECT",
    default=False,
)

SESSION_COOKIE_SECURE = env_bool(
    "SESSION_COOKIE_SECURE",
    default=False,
)

CSRF_COOKIE_SECURE = env_bool(
    "CSRF_COOKIE_SECURE",
    default=False,
)

SECURE_HSTS_SECONDS = int(
    os.environ.get(
        "SECURE_HSTS_SECONDS",
        "0",
    )
)

SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool(
    "SECURE_HSTS_INCLUDE_SUBDOMAINS",
    default=False,
)

SECURE_HSTS_PRELOAD = env_bool(
    "SECURE_HSTS_PRELOAD",
    default=False,
)


# If deployed behind a reverse proxy such as nginx,
# configure this only when the proxy is trusted to set
# X-Forwarded-Proto correctly.
#
# SECURE_PROXY_SSL_HEADER = (
#     "HTTP_X_FORWARDED_PROTO",
#     "https",
# )


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

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOG_LEVEL = os.environ.get(
    "DJANGO_LOG_LEVEL",
    "INFO" if DEBUG else "WARNING",
)

LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


LOGGING = {
    "version": 1,

    "disable_existing_loggers": False,

    "formatters": {
        "json": {
            "()": (
                "api.logging_utils.JSONFormatter"
            ),
        },
    },

    "handlers": {
        "console_json": {
            "class": (
                "logging.StreamHandler"
            ),
            "formatter": "json",
        },

        "file_json": {
            "class": (
                "logging.handlers."
                "RotatingFileHandler"
            ),
            "filename": (
                LOG_DIR / "application.log"
            ),
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "json",
        },
    },

    "loggers": {
        "api": {
            "handlers": [
                "console_json",
                "file_json",
            ],
            "level": LOG_LEVEL,
            "propagate": False,
        },

        "django.request": {
            "handlers": [
                "console_json",
                "file_json",
            ],
            "level": "WARNING",
            "propagate": False,
        },

        "django.security": {
            "handlers": [
                "console_json",
                "file_json",
            ],
            "level": "WARNING",
            "propagate": False,
        },
    },
}