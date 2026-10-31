from rest_framework import serializers

from apps.inventory.models import InventoryItem, RecipeIngredient, StockMovement


class InventoryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryItem
        fields = (
            "id",
            "name",
            "category",
            "base_unit",
            "current_quantity",
            "min_stock_threshold",
            "is_active",
            "sku",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "current_quantity", "created_at", "updated_at")


class StockMovementSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.name", read_only=True)
    actor_name = serializers.CharField(source="actor.username", read_only=True)

    class Meta:
        model = StockMovement
        fields = (
            "id",
            "item",
            "item_name",
            "quantity_delta",
            "movement_type",
            "actor_name",
            "timestamp",
            "reference",
            "reason",
            "previous_balance",
            "new_balance",
        )
        read_only_fields = fields


class RecipeIngredientSerializer(serializers.ModelSerializer):
    inventory_item_name = serializers.CharField(source="inventory_item.name", read_only=True)

    class Meta:
        model = RecipeIngredient
        fields = ("id", "menu_item", "inventory_item", "inventory_item_name", "quantity", "unit")
        read_only_fields = ("id",)
