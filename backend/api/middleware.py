import logging
import uuid

from django.http import JsonResponse

from rest_framework import status


logger = logging.getLogger("api")


class RequestIDMiddleware:
    """
    Assign a request ID to every request.

    The request ID is:
    - generated when the client does not provide one
    - preserved when a valid X-Request-ID is supplied
    - attached to the request object
    - returned in the response headers
    """

    HEADER_NAME = "HTTP_X_REQUEST_ID"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.META.get(
            self.HEADER_NAME
        )

        if (
            not request_id
            or len(request_id) > 128
        ):
            request_id = str(uuid.uuid4())

        request.request_id = request_id

        try:
            response = self.get_response(request)

        except Exception as exc:
            return self._handle_exception(
                request,
                request_id,
                exc,
            )

        # Normalize API 404 responses.
        #
        # Django URL resolution can return a normal
        # HttpResponseNotFound instead of a DRF Response.
        if (
            response.status_code
            == status.HTTP_404_NOT_FOUND
            and request.path.startswith("/api/")
        ):
            response = JsonResponse(
                {
                    "error": {
                        "code": "NOT_FOUND",
                        "message": (
                            "The requested resource "
                            "was not found."
                        ),
                        "request_id": request_id,
                    }
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        response["X-Request-ID"] = request_id

        return response

    def _handle_exception(
        self,
        request,
        request_id,
        exc,
    ):
        """
        Final safety net for exceptions escaping
        the normal request/DRF processing.
        """

        user = getattr(
            request,
            "user",
            None,
        )

        user_id = None
        organization_id = None

        if getattr(
            user,
            "is_authenticated",
            False,
        ):
            user_id = getattr(
                user,
                "id",
                None,
            )

            try:
                organization_id = (
                    user.organization.id
                )
            except Exception:
                organization_id = None

        logger.exception(
            "Unhandled application exception",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.path,
                "status_code": 500,
                "user_id": user_id,
                "organization_id": organization_id,
                "error_code": (
                    "INTERNAL_SERVER_ERROR"
                ),
                "exception_type": (
                    type(exc).__name__
                ),
            },
        )

        if request.path.startswith("/api/"):
            response = JsonResponse(
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
                status=(
                    status.HTTP_500_INTERNAL_SERVER_ERROR
                ),
            )

            response["X-Request-ID"] = request_id

            return response

        # Non-API requests should retain Django's
        # normal exception behavior.
        raise exc


class APIExceptionMiddleware:
    """
    Optional final application-level safety net.

    DRF exceptions should normally be handled by the
    centralized DRF exception handler.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            response = self.get_response(request)

        except Exception as exc:
            request_id = getattr(
                request,
                "request_id",
                None,
            )

            if not request_id:
                request_id = str(
                    uuid.uuid4()
                )

            logger.exception(
                "Unhandled application exception",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.path,
                    "status_code": 500,
                    "error_code": (
                        "INTERNAL_SERVER_ERROR"
                    ),
                    "exception_type": (
                        type(exc).__name__
                    ),
                },
            )

            if request.path.startswith("/api/"):
                response = JsonResponse(
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
                    status=500,
                )

                response["X-Request-ID"] = (
                    request_id
                )

                return response

            raise

        request_id = getattr(
            request,
            "request_id",
            None,
        )

        if request_id:
            response["X-Request-ID"] = (
                request_id
            )

        return response