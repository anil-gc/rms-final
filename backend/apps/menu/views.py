from apps.core.api import WorkspaceModelViewSet, can_manage
from apps.restaurants.services import configured_restaurant

from .models import Category, MenuItem
from .serializers import CategorySerializer, MenuItemSerializer


class CategoryViewSet(WorkspaceModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset if can_manage(self.request.user) else queryset.filter(is_active=True)

    def perform_create(self, serializer):
        serializer.save(restaurant=configured_restaurant())


class MenuItemViewSet(WorkspaceModelViewSet):
    queryset = MenuItem.objects.select_related("category__restaurant")
    serializer_class = MenuItemSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if not can_manage(self.request.user):
            queryset = queryset.filter(is_active=True, category__is_active=True)
        return queryset
