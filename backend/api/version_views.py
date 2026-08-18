from django.conf import settings

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class VersionView(APIView):
    """
    Public application metadata endpoint.

    Does not expose secrets or infrastructure details.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response(
            {
                "name": settings.APP_NAME,
                "version": settings.APP_VERSION,
                "environment": settings.DJANGO_ENV,
            }
        )