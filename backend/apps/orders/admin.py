"""Read-only order/audit inspection; writes go through domain services."""

from django.contrib import admin

from apps.restaurants.admin import ReadOnlyWorkspaceAdmin

from .models import DiningSession, Order, OrderBatch, OrderEvent, OrderLine

for model in (DiningSession, Order, OrderBatch, OrderLine, OrderEvent):
    admin.site.register(model, ReadOnlyWorkspaceAdmin)
