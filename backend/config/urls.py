from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from api.views import CreateUserView
from api.version_views import VersionView

from api.auth_views import (
    ThrottledTokenObtainPairView,
    ThrottledTokenRefreshView,
)
from api.health_views import (
    HealthCheckView,
    ReadinessCheckView,
)


urlpatterns = [
    path(
        "admin/",
        admin.site.urls,
    ),

    path(
        "api/user/register/",
        CreateUserView.as_view(),
        name="register",
    ),

    path(
        "api/token/",
        ThrottledTokenObtainPairView.as_view(),
        name="get_token",
    ),

    path(
        "api/token/refresh/",
        ThrottledTokenRefreshView.as_view(),
        name="refresh",
    ),

    path(
        "api/",
        include("api.urls"),
    ),

    path(
        "health/",
        HealthCheckView.as_view(),
        name="health",
    ),

    path(
        "ready/",
        ReadinessCheckView.as_view(),
        name="ready",
    ),

    path(
        "version/",
        VersionView.as_view(),
        name="version",
    ),
]

handler404 = "api.exception_handlers.api_404_handler"

if settings.DEBUG:
    urlpatterns += [
        path(
            "api-auth/",
            include("rest_framework.urls"),
        ),
    ]