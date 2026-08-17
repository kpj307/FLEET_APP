from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from .throttles import (
    LoginThrottle,
    TokenRefreshThrottle,
)


class ThrottledTokenObtainPairView(
    TokenObtainPairView
):
    """
    JWT login endpoint with dedicated
    brute-force protection.
    """

    throttle_classes = [
        LoginThrottle,
    ]


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