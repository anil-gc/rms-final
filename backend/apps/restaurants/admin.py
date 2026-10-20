"""Read-only operator inspection; workspace writes use the permission-checked API."""

from django.contrib import admin

from .models import DiningTable, Restaurant


class ReadOnlyWorkspaceAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return (
            request.user.is_active
            and request.user.role in {"owner", "manager"}
            and not request.user.must_change_pin
        )


@admin.register(Restaurant)
class RestaurantAdmin(ReadOnlyWorkspaceAdmin):
    list_display = ["name", "currency", "is_active"]
    exclude = ["logo"]


@admin.register(DiningTable)
class DiningTableAdmin(ReadOnlyWorkspaceAdmin):
    list_display = ["name", "capacity", "status", "is_active"]
