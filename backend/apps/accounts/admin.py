from django.contrib import admin

from .models import User


@admin.register(User)
class AccountAdmin(admin.ModelAdmin):
    """Read-only account records; staff and PIN writes use secured APIs."""

    list_display = ("username", "role", "is_active", "must_change_pin")
    list_filter = ("role", "is_active")
    search_fields = ("username",)
    fields = (
        "username",
        "first_name",
        "last_name",
        "role",
        "is_active",
        "must_change_pin",
        "last_login",
        "date_joined",
    )
    readonly_fields = fields

    def has_view_permission(self, request, obj=None):
        return request.user.is_active and (
            request.user.role == User.Role.OWNER or request.user.is_superuser
        )

    def has_module_permission(self, request):
        return self.has_view_permission(request)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
