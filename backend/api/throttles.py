from rest_framework.throttling import (
    AnonRateThrottle,
    SimpleRateThrottle,
    UserRateThrottle,
)


class RegistrationThrottle(AnonRateThrottle):
    """
    Protect public account registration.

    Rate:
        5 requests / hour
    """

    scope = "registration"


class LoginThrottle(AnonRateThrottle):
    """
    Protect username/password authentication.

    Rate:
        10 requests / minute
    """

    scope = "login"


class TokenRefreshThrottle(AnonRateThrottle):
    """
    Protect refresh-token endpoint.

    Rate:
        20 requests / minute
    """

    scope = "token_refresh"


class PaymentCreateThrottle(UserRateThrottle):
    """
    Protect payment checkout creation.

    Rate:
        10 requests / hour
    """

    scope = "payment_create"


class PaymentStatusThrottle(UserRateThrottle):
    """
    Protect payment verification/status polling.

    Rate:
        30 requests / minute
    """

    scope = "payment_status"