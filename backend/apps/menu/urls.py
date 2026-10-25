from rest_framework.routers import SimpleRouter

from .views import CategoryViewSet, MenuItemViewSet

router = SimpleRouter()
router.register("categories", CategoryViewSet, basename="menu-category")
router.register("items", MenuItemViewSet, basename="menu-item")
urlpatterns = router.urls
