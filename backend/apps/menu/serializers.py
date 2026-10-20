from rest_framework import serializers

from apps.core.api import StrictModelSerializer

from .models import Category, MenuItem


class CategorySerializer(StrictModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "description", "sort_order", "is_active", "updated_at"]
        read_only_fields = ["id", "updated_at"]

    def validate_name(self, value):
        query = Category.objects.filter(name__iexact=value)
        if self.instance:
            query = query.exclude(pk=self.instance.pk)
        if query.exists():
            raise serializers.ValidationError(
                "A category with this name already exists, including archived categories."
            )
        return value


class MenuItemSerializer(StrictModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    effective_available = serializers.SerializerMethodField()

    class Meta:
        model = MenuItem
        fields = [
            "id",
            "name",
            "description",
            "category",
            "category_name",
            "price",
            "is_available",
            "is_active",
            "effective_available",
            "updated_at",
        ]
        read_only_fields = ["id", "updated_at"]

    def get_effective_available(self, obj):
        return (
            obj.is_active
            and obj.is_available
            and obj.category.is_active
            and obj.category.restaurant.is_active
        )

    def validate(self, attrs):
        name = attrs.get("name", getattr(self.instance, "name", None))
        category = attrs.get("category", getattr(self.instance, "category", None))
        if name and category:
            query = MenuItem.objects.filter(name__iexact=name, category=category)
            if self.instance:
                query = query.exclude(pk=self.instance.pk)
            if query.exists():
                raise serializers.ValidationError(
                    {
                        "name": "This item name already exists in the category, "
                        "including archived items."
                    }
                )
        return attrs
