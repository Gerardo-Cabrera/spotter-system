from django.contrib import admin
from django.urls import include, path
from drf_spectacular.utils import OpenApiResponse, OpenApiTypes, extend_schema
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.decorators import api_view
from rest_framework.response import Response


@extend_schema(
    tags=["health"],
    summary="Liveness check",
    responses={200: OpenApiResponse(
        response=OpenApiTypes.OBJECT,
        description="Service is up.",
    )},
)
@api_view(["GET"])
def health(_request):
    return Response({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health),
    # OpenAPI schema + interactive docs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    path("api/", include("trips.urls")),
]
