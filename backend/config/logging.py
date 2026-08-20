import os
from pathlib import Path


BASE_DIR = Path(
    os.environ.get(
        "DJANGO_BASE_DIR",
        Path(__file__).resolve().parent.parent,
    )
)

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
    "INFO",
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


LOGGING = {
    "version": 1,

    "disable_existing_loggers": False,

    "formatters": {
        "structured": {
            "()": (
                "config.logging_utils."
                "StructuredJSONFormatter"
            ),
        },
        "simple": {
            "format": (
                "{levelname} "
                "{asctime} "
                "{name} "
                "{message}"
            ),
            "style": "{",
        },
    },

    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "structured",
        },

        "application_file": {
            "class": (
                "logging.handlers."
                "RotatingFileHandler"
            ),
            "filename": str(
                LOG_DIR / "application.log"
            ),
            "maxBytes": LOG_MAX_BYTES,
            "backupCount": LOG_BACKUP_COUNT,
            "encoding": "utf-8",
            "formatter": "structured",
        },

        "error_file": {
            "class": (
                "logging.handlers."
                "RotatingFileHandler"
            ),
            "filename": str(
                LOG_DIR / "errors.log"
            ),
            "maxBytes": LOG_MAX_BYTES,
            "backupCount": LOG_BACKUP_COUNT,
            "encoding": "utf-8",
            "formatter": "structured",
            "level": "ERROR",
        },

        "security_file": {
            "class": (
                "logging.handlers."
                "RotatingFileHandler"
            ),
            "filename": str(
                LOG_DIR / "security.log"
            ),
            "maxBytes": LOG_MAX_BYTES,
            "backupCount": LOG_BACKUP_COUNT,
            "encoding": "utf-8",
            "formatter": "structured",
        },
    },

    "loggers": {
        "api": {
            "handlers": [
                "console",
                "application_file",
                "error_file",
            ],
            "level": LOG_LEVEL,
            "propagate": False,
        },

        "api.audit": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },

        "api.security": {
            "handlers": [
                "console",
                "security_file",
            ],
            "level": LOG_LEVEL,
            "propagate": False,
        },

        "api.payment_views": {
            "handlers": [
                "console",
                "application_file",
                "error_file",
            ],
            "level": LOG_LEVEL,
            "propagate": False,
        },

        "django.request": {
            "handlers": [
                "console",
                "application_file",
                "error_file",
            ],
            "level": "WARNING",
            "propagate": False,
        },
    },

    "root": {
        "handlers": [
            "console",
        ],
        "level": LOG_LEVEL,
    },
}