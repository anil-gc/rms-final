"""Catalogue and current availability; no ordering or price calculations."""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.functions import Lower, Trim


class Category(models.Model):
    restaurant = models.ForeignKey(
        "restaurants.Restaurant", on_delete=models.PROTECT, related_name="categories"
    )
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=500, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name", "id"]
        constraints = [
            models.UniqueConstraint(Lower(Trim("name")), name="category_name_unique_ci"),
            models.CheckConstraint(
                condition=models.Q(name__regex=r"\S"), name="category_name_nonblank"
            ),
        ]

    def __str__(self):
        return self.name


class MenuItem(models.Model):
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="items")
    name = models.CharField(max_length=150)
    description = models.CharField(max_length=1000, blank=True)
    price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    is_available = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category__sort_order", "category__name", "name", "id"]
        constraints = [
            models.UniqueConstraint(
                Lower(Trim("name")), "category", name="item_name_category_unique_ci"
            ),
            models.CheckConstraint(
                condition=models.Q(name__regex=r"\S"), name="item_name_nonblank"
            ),
            models.CheckConstraint(
                condition=models.Q(price__gt=0, price__lte=Decimal("99999999.99")),
                name="item_price_positive",
            ),
        ]

    def __str__(self):
        return self.name
