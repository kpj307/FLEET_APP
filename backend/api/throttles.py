from rest_framework.throttling import (
    AnonRateThrottle,
    UserRateThrottle,
)


class ConfigurableRateThrottleMixin:
    """
    Allows each dedicated throttle class to define its own rate.

    Tests can override THROTTLE_RATES on an individual throttle
    without modifying global REST_FRAMEWORK settings.
    """

    THROTTLE_RATES = {}

    def get_rate(self):
        rate = self.THROTTLE_RATES.get(self.scope)

        if rate:
            return rate

        return super().get_rate()


class RegistrationThrottle(
    ConfigurableRateThrottleMixin,
    AnonRateThrottle,
):
    """
    Protect public account registration.

    Production rate:
        5 requests / hour
    """

    scope = "registration"

    THROTTLE_RATES = {
        "registration": "5/hour",
    }


class LoginThrottle(
    ConfigurableRateThrottleMixin,
    AnonRateThrottle,
):
    """
    Protect username/password authentication.

    Production rate:
        10 requests / minute
    """

    scope = "login"

    THROTTLE_RATES = {
        "login": "10/minute",
    }


class TokenRefreshThrottle(
    ConfigurableRateThrottleMixin,
    AnonRateThrottle,
):
    """
    Protect refresh-token endpoint.

    Production rate:
        20 requests / minute
    """

    scope = "token_refresh"

    THROTTLE_RATES = {
        "token_refresh": "20/minute",
    }


class PaymentCreateThrottle(
    ConfigurableRateThrottleMixin,
    UserRateThrottle,
):
    """
    Protect payment checkout creation.

    Production rate:
        10 requests / hour
    """

    scope = "payment_create"

    THROTTLE_RATES = {
        "payment_create": "10/hour",
    }


class PaymentStatusThrottle(
    ConfigurableRateThrottleMixin,
    UserRateThrottle,
):
    """
    Protect payment verification/status polling.

    Production rate:
        30 requests / minute
    """

    scope = "payment_status"

    THROTTLE_RATES = {
        "payment_status": "30/minute",
    }