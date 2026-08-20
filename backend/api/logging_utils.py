import json
import logging
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID


class JSONFormatter(logging.Formatter):
    """
    Format log records as structured JSON.
    """

    def format(self, record):
        payload = {
            "timestamp": datetime.now().astimezone().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include structured logging fields.
        for key in (
            "request_id",
            "method",
            "path",
            "status_code",
            "duration_ms",
            "error_code",
            "event",
            "success",
            "user_id",
            "view",
        ):
            value = getattr(record, key, None)

            if value is not None:
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(
            payload,
            default=self._json_default,
        )

    @staticmethod
    def _json_default(value):
        if isinstance(value, (datetime, date)):
            return value.isoformat()

        if isinstance(value, Decimal):
            return str(value)

        if isinstance(value, UUID):
            return str(value)

        return str(value)

"""
Utilities for safely preparing data for logs.
"""

SENSITIVE_KEYS = {
    "password",
    "password1",
    "password2",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "api_key",
    "secret",
    "secret_key",
    "signature",
    "flutterwave_secret_hash",
    "card_number",
    "cvv",
}

REDACTED_VALUE = "[REDACTED]"


def sanitize_log_data(data):
    """
    Recursively redact sensitive values from dictionaries,
    lists, and tuples.
    """

    if isinstance(data, dict):
        sanitized = {}

        for key, value in data.items():
            if str(key).lower() in SENSITIVE_KEYS:
                sanitized[key] = REDACTED_VALUE
            else:
                sanitized[key] = sanitize_log_data(value)

        return sanitized

    if isinstance(data, list):
        return [
            sanitize_log_data(value)
            for value in data
        ]

    if isinstance(data, tuple):
        return tuple(
            sanitize_log_data(value)
            for value in data
        )

    return data
