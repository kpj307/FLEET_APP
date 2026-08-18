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

# DEBUG = env_bool(
#     "DJANGO_DEBUG",
#     default=False,
# )

DJANGO_ENV = os.environ.get(
    "DJANGO_ENV",
    "development",
).strip().lower()

IS_PRODUCTION = (
    DJANGO_ENV == "production"
)

IS_TESTING = (
    "test" in os.environ.get(
        "DJANGO_SETTINGS_MODULE",
        ""
    ).lower()
)

DEBUG = env_bool(
    "DEBUG",
    DJANGO_ENV != "production",
)

# ============================================================
# SECURITY
# ============================================================

# IMPORTANT:
# Generate a new production SECRET_KEY.
#
# Do NOT commit it to Git.
SECRET_KEY = os.environ.get("SECRET_KEY")

if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY environment variable is required."
    )

if IS_PRODUCTION and DEBUG:
    raise RuntimeError(
        "DEBUG must be False in production."
    )

ALLOWED_HOSTS = env_list(
    "DJANGO_ALLOWED_HOSTS",
    "localhost,127.0.0.1",
)

if IS_PRODUCTION:
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

CORS_ALLOW_ALL_ORIGINS = False

CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
)

CORS_ALLOW_CREDENTIALS = env_bool(
    "CORS_ALLOW_CREDENTIALS",
    default=False,
)

if (
    IS_PRODUCTION
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
    "http://localhost:5173,http://127.0.0.1:5173",
)


# ============================================================
# SECURITY HEADERS
# ============================================================

SECURE_CONTENT_TYPE_NOSNIFF = True

X_FRAME_OPTIONS = "DENY"

SECURE_REFERRER_POLICY = "same-origin"

SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"


# --------------------------------------------------
# HTTPS / browser security
# --------------------------------------------------

SECURE_SSL_REDIRECT = env_bool(
    "SECURE_SSL_REDIRECT",
    DJANGO_ENV == "production" and not IS_TESTING,
)

SECURE_PROXY_SSL_HEADER = (
    "HTTP_X_FORWARDED_PROTO",
    "https",
)

SESSION_COOKIE_SECURE = env_bool(
    "SESSION_COOKIE_SECURE",
    DJANGO_ENV == "production" and not IS_TESTING,
)

CSRF_COOKIE_SECURE = env_bool(
    "CSRF_COOKIE_SECURE",
    DJANGO_ENV == "production" and not IS_TESTING,
)

if IS_PRODUCTION:
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

SECURE_HSTS_SECONDS = int(
    os.getenv(
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

if IS_PRODUCTION:
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

SECURE_CONTENT_TYPE_NOSNIFF = True

SECURE_REFERRER_POLICY = (
    "strict-origin-when-cross-origin"
)

SECURE_CROSS_ORIGIN_OPENER_POLICY = (
    "same-origin"
)

X_FRAME_OPTIONS = "DENY"

if IS_PRODUCTION:
    if not ALLOWED_HOSTS:
        raise RuntimeError(
            "ALLOWED_HOSTS must be configured "
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

def validate_production_security():
    if not IS_PRODUCTION:
        return

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

    if CORS_ALLOW_ALL_ORIGINS:
        raise RuntimeError(
            "CORS_ALLOW_ALL_ORIGINS must be False "
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
            "SECURE_HSTS_INCLUDE_SUBDOMAINS must be True "
            "in production."
        )

    if not SECURE_HSTS_PRELOAD:
        raise RuntimeError(
            "SECURE_HSTS_PRELOAD must be True "
            "in production."
        )