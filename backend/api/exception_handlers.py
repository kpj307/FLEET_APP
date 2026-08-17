import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


logger = logging.getLogger("api")


def custom_exception_handler(exc, context):
    """
    Centralized DRF exception handler.

    Expected DRF exceptions are converted to a consistent
    JSON structure.

    Unexpected exceptions are logged internally and converted
    into a safe 500 response.
    """

    request = context.get("request")
    view = context.get("view")

    request_id = getattr(
        request,
        "request_id",
        None,
    )

    response = exception_handler(
        exc,
        context,
    )

    method = getattr(
        request,
        "method",
        None,
    )

    path = getattr(
        request,
        "path",
        None,
    )

    view_name = (
        view.__class__.__name__
        if view
        else None
    )

    # ---------------------------------------------------------
    # Unexpected exception
    # ---------------------------------------------------------

    if response is None:
        logger.error(
            "Unhandled DRF exception",
            exc_info=(
                type(exc),
                exc,
                exc.__traceback__,
            ),
            extra={
                "request_id": request_id,
                "method": method,
                "path": path,
                "status_code": 500,
                "error_code": (
                    "INTERNAL_SERVER_ERROR"
                ),
                "exception_type": (
                    type(exc).__name__
                ),
                "view": view_name,
            },
        )

        return Response(
            {
                "error": {
                    "code": (
                        "INTERNAL_SERVER_ERROR"
                    ),
                    "message": (
                        "An unexpected error "
                        "occurred."
                    ),
                    "request_id": request_id,
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # ---------------------------------------------------------
    # Expected DRF exception
    # ---------------------------------------------------------

    status_code = response.status_code

    if status_code >= 500:
        logger.error(
            "API server error",
            extra={
                "request_id": request_id,
                "method": method,
                "path": path,
                "status_code": status_code,
                "error_code": (
                    "API_SERVER_ERROR"
                ),
                "view": view_name,
            },
        )

    elif status_code >= 400:
        logger.warning(
            "API client error",
            extra={
                "request_id": request_id,
                "method": method,
                "path": path,
                "status_code": status_code,
                "error_code": (
                    "API_CLIENT_ERROR"
                ),
                "view": view_name,
            },
        )

    original_data = response.data

    error_payload = {
        "code": _get_error_code(
            status_code
        ),
        "message": _get_error_message(
            original_data
        ),
        "request_id": request_id,
    }

    # Preserve the original DRF response fields.
    #
    # This is important for backwards compatibility:
    # existing API clients/tests may depend on fields such
    # as:
    #
    # {
    #     "plan": [...]
    # }
    #
    # or:
    #
    # {
    #     "detail": "..."
    # }
    #
    # The standardized error metadata is therefore additive
    # rather than destructive.
    if isinstance(original_data, dict):
        response.data = {
            **original_data,
            "error": error_payload,
        }

    else:
        response.data = {
            "detail": original_data,
            "error": error_payload,
        }

    return response


def _get_error_code(status_code):
    return {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        415: "UNSUPPORTED_MEDIA_TYPE",
        429: "RATE_LIMITED",
    }.get(
        status_code,
        "API_ERROR",
    )

def _get_error_message(data):
    if isinstance(data, dict):
        detail = data.get("detail")

        if detail:
            return str(detail)

        non_field_errors = data.get(
            "non_field_errors"
        )

        if non_field_errors:
            return str(non_field_errors)

        # Serializer validation errors.
        #
        # Example:
        #
        # {
        #     "plan": [
        #         "Vehicle limit reached..."
        #     ]
        # }
        #
        # Return a useful generic message while preserving
        # the original field-level errors in response.data.
        if data:
            return "Request validation failed."

    if isinstance(data, list):
        return "Request validation failed."

    return "Request could not be processed."