import json
import logging
from datetime import datetime


class StructuredJSONFormatter(
    logging.Formatter
):
    """
    JSON formatter for production logs.

    Keeps structured fields while avoiding
    sensitive request information.
    """

    RESERVED = {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "message",
    }

    def format(self, record):
        payload = {
            "timestamp": (
                datetime.fromtimestamp(
                    record.created
                ).astimezone().isoformat()
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for key, value in record.__dict__.items():
            if key in self.RESERVED:
                continue

            if key.startswith("_"):
                continue

            if key.lower() in {
                "authorization",
                "cookie",
                "token",
                "password",
                "secret",
                "secret_key",
            }:
                continue

            payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(
                record.exc_info
            )

        return json.dumps(
            payload,
            default=str,
        )