"""Project entry points: Django admin and versioned API."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("config.api_urls", namespace="v1")),
]
