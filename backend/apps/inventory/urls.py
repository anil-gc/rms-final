from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.inventory.views import (
    InventoryItemViewSet,
    RecipeIngredientViewSet,
    StockMovementViewSet,
)

router = DefaultRouter()
router.register("items", InventoryItemViewSet, basename="inventoryitem")
router.register("movements", StockMovementViewSet, basename="stockmovement")
router.register("recipes", RecipeIngredientViewSet, basename="recipeingredient")

app_name = "inventory"

urlpatterns = [
    path("", include(router.urls)),
]
