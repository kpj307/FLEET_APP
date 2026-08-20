import logging

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from rest_framework.exceptions import AuthenticationFailed

from .throttles import (
    LoginThrottle,
    TokenRefreshThrottle,
)

from .audit import log_audit_event

logger = logging.getLogger("api.audit")


class ThrottledTokenObtainPairView(TokenObtainPairView):
    """
    JWT login endpoint with dedicated brute-force protection
    and authentication audit logging.
    """

    throttle_classes = [
        LoginThrottle,
    ]

    def post(self, request, *args, **kwargs):
        try:
            response = super().post(
                request,
                *args,
                **kwargs,
            )

        except AuthenticationFailed:
            log_audit_event(
                event="authentication.failed",
                request=request,
                success=False,
                username=request.data.get("username"),
                reason="invalid_credentials",
            )
            raise

        log_audit_event(
            event="authentication.succeeded",
            request=request,
            success=True,
            username=request.data.get("username"),
        )

        return response

class ThrottledTokenRefreshView(
    TokenRefreshView
):
    """
    JWT refresh endpoint with dedicated
    rate limiting.
    """

    throttle_classes = [
        TokenRefreshThrottle,
    ]