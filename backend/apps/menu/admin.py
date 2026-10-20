from django.contrib import admin

from apps.restaurants.admin import ReadOnlyWorkspaceAdmin

from .models import Category, MenuItem


@admin.register(Category)
class CategoryAdmin(ReadOnlyWorkspaceAdmin):
    list_display = ["name", "sort_order", "is_active"]


@admin.register(MenuItem)
class MenuItemAdmin(ReadOnlyWorkspaceAdmin):
    list_display = ["name", "category", "price", "is_available", "is_active"]
