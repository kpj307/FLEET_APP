import json
import logging
from datetime import date, datetime
from decimal import Decimal


SENSITIVE_KEYS = {
    "password",
    "token",
    "access",
    "refresh",
    "authorization",
    "cookie",
    "secret",
    "secret_key",
    "api_key",
    "private_key",
    "card_number",
    "cvv",
}


def _safe_value(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, Decimal):
        return str(value)

    if isinstance(value, dict):
        return {
            str(key): _safe_value(item)
            for key, item in value.items()
            if str(key).lower() not in SENSITIVE_KEYS
        }

    if isinstance(value, (list, tuple)):
        return [_safe_value(item) for item in value]

    if isinstance(value, (str, int, float, bool)) or value is None:
        return value

    return str(value)


class JSONFormatter(logging.Formatter):
    """
    Structured JSON formatter for production logs.
    """

    def format(self, record):
        payload = {
            "timestamp": datetime.now().astimezone().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if hasattr(record, "request_id"):
            payload["request_id"] = record.request_id

        if hasattr(record, "method"):
            payload["method"] = record.method

        if hasattr(record, "path"):
            payload["path"] = record.path

        if hasattr(record, "status_code"):
            payload["status_code"] = record.status_code

        if hasattr(record, "user_id"):
            payload["user_id"] = record.user_id

        if hasattr(record, "organization_id"):
            payload["organization_id"] = record.organization_id

        if hasattr(record, "error_code"):
            payload["error_code"] = record.error_code

        if hasattr(record, "exception_type"):
            payload["exception_type"] = record.exception_type

        if record.exc_info:
            payload["exception"] = self.formatException(
                record.exc_info
            )

        return json.dumps(
            _safe_value(payload),
            ensure_ascii=False,
        )