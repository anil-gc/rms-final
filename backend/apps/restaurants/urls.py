from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .views import DiningTableViewSet, RestaurantLogoView, RestaurantProfileView

router = SimpleRouter()
router.register("tables", DiningTableViewSet, basename="table")

urlpatterns = [
    path("restaurant/", RestaurantProfileView.as_view(), name="restaurant-profile"),
    path("restaurant/logo/", RestaurantLogoView.as_view(), name="restaurant-logo"),
    path("", include(router.urls)),
]
