import uuid
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class InventoryItem(models.Model):
    class Unit(models.TextChoices):
        KILOGRAM = "kg", "Kilogram (kg)"
        GRAM = "g", "Gram (g)"
        LITER = "L", "Liter (L)"
        MILLILITER = "ml", "Milliliter (ml)"
        PIECE = "pcs", "Piece (pcs)"
        PACKET = "pkt", "Packet (pkt)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=100)
    base_unit = models.CharField(max_length=3, choices=Unit.choices)
    current_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=Decimal("0.000"),
        validators=[MinValueValidator(Decimal("0.000"))],
    )
    min_stock_threshold = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=Decimal("0.000"),
        validators=[MinValueValidator(Decimal("0.000"))],
    )
    is_active = models.BooleanField(default=True)
    sku = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "sku"],
                condition=~models.Q(sku=""),
                name="unique_active_item_sku",
            ),
            models.CheckConstraint(
                condition=models.Q(current_quantity__gte=0),
                name="positive_current_quantity",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.current_quantity} {self.base_unit})"


class StockMovement(models.Model):
    class MovementType(models.TextChoices):
        OPENING_BALANCE = "opening_balance", "Opening Balance"
        RECEIPT = "receipt", "Purchase Receipt"
        MANUAL_IN = "manual_in", "Manual Stock In"
        MANUAL_OUT = "manual_out", "Manual Stock Out"
        WASTE = "waste", "Waste / Damage"
        ADJUSTMENT = "adjustment", "Physical Count Adjustment"
        CONSUMPTION = "consumption", "Recipe Consumption"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item = models.ForeignKey(InventoryItem, on_delete=models.RESTRICT, related_name="movements")
    quantity_delta = models.DecimalField(max_digits=12, decimal_places=3)
    movement_type = models.CharField(max_length=20, choices=MovementType.choices)
    actor = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(default=timezone.now)
    reference = models.CharField(max_length=255, blank=True)
    reason = models.TextField(blank=True)

    # Optional denormalized fields for auditing
    previous_balance = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    new_balance = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    supplier = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-timestamp"]


class RecipeIngredient(models.Model):
    menu_item = models.ForeignKey(
        "menu.MenuItem",
        on_delete=models.CASCADE,
        related_name="recipe_ingredients"
    )
    inventory_item = models.ForeignKey(InventoryItem, on_delete=models.RESTRICT)
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))]
    )
    unit = models.CharField(max_length=3, choices=InventoryItem.Unit.choices)

    class Meta:
        unique_together = (("menu_item", "inventory_item"),)

    def __str__(self):
        return f"{self.quantity} {self.unit} of {self.inventory_item.name} for {self.menu_item.name}"
