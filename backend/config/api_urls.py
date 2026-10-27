"""Central API registry. Register future module URLs here within v1."""

from django.urls import include, path

app_name = "api"
urlpatterns = [
    path("", include("apps.core.urls")),
    path("accounts/", include("apps.accounts.urls")),
    path("", include("apps.restaurants.urls")),
    path("menu/", include("apps.menu.urls")),
    path("orders/", include("apps.orders.urls")),
    path("kitchen/", include("apps.kitchen.urls")),
]
