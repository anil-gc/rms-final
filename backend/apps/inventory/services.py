import logging
from decimal import Decimal
from typing import Dict, List, Optional

from django.db import transaction
from django.db.models import F

from apps.accounts.models import User
from apps.inventory.models import InventoryItem, RecipeIngredient, StockMovement
from apps.orders.models import OrderLine


logger = logging.getLogger(__name__)

# Mass and volume conversion rates to their base units (kg, L)
_CONVERSION_RATES: Dict[str, Dict[str, Decimal]] = {
    "kg": {"kg": Decimal("1"), "g": Decimal("1000")},
    "g": {"kg": Decimal("0.001"), "g": Decimal("1")},
    "L": {"L": Decimal("1"), "ml": Decimal("1000")},
    "ml": {"L": Decimal("0.001"), "ml": Decimal("1")},
    "pcs": {"pcs": Decimal("1")},
    "pkt": {"pkt": Decimal("1")},
}

def convert_quantity(quantity: Decimal, from_unit: str, to_unit: str) -> Decimal:
    """Converts a quantity from one unit to another, raising ValueError on dimension mismatch."""
    if from_unit == to_unit:
        return quantity

    rates = _CONVERSION_RATES.get(from_unit)
    if not rates or to_unit not in rates:
        raise ValueError(f"Cannot convert between {from_unit} and {to_unit}")

    multiplier = _CONVERSION_RATES[from_unit][to_unit]
    return (quantity * multiplier).quantize(Decimal("0.001"))


@transaction.atomic
def receive_stock(
    item_id: str,
    quantity: Decimal,
    unit: str,
    actor: User,
    unit_cost: Optional[Decimal] = None,
    total_cost: Optional[Decimal] = None,
    supplier: str = "",
    reference: str = "",
    notes: str = ""
) -> StockMovement:
    """Records a purchase receipt and increases stock balance atomically."""
    item = InventoryItem.objects.select_for_update().get(id=item_id)
    normalized_qty = convert_quantity(quantity, unit, item.base_unit)

    if normalized_qty <= 0:
        raise ValueError("Receipt quantity must be positive")

    previous_balance = item.current_quantity
    item.current_quantity = F("current_quantity") + normalized_qty
    item.save(update_fields=["current_quantity", "updated_at"])

    # Reload to get actual value for movement ledger
    item.refresh_from_db()

    return StockMovement.objects.create(
        item=item,
        quantity_delta=normalized_qty,
        movement_type=StockMovement.MovementType.RECEIPT,
        actor=actor,
        reference=reference,
        reason=notes,
        previous_balance=previous_balance,
        new_balance=item.current_quantity,
        unit_cost=unit_cost,
        total_cost=total_cost,
        supplier=supplier
    )


@transaction.atomic
def adjust_stock(
    item_id: str,
    new_quantity: Decimal,
    reason: str,
    actor: User,
) -> StockMovement:
    """Corrects physical stock count."""
    item = InventoryItem.objects.select_for_update().get(id=item_id)

    if new_quantity < 0:
        raise ValueError("Quantity cannot be negative")

    previous_balance = item.current_quantity
    delta = new_quantity - previous_balance

    if delta == 0:
        raise ValueError("New quantity matches current balance")

    item.current_quantity = new_quantity
    item.save(update_fields=["current_quantity", "updated_at"])

    return StockMovement.objects.create(
        item=item,
        quantity_delta=delta,
        movement_type=StockMovement.MovementType.ADJUSTMENT,
        actor=actor,
        reason=reason,
        previous_balance=previous_balance,
        new_balance=item.current_quantity
    )


@transaction.atomic
def process_recipe_consumption(order_line: OrderLine) -> List[StockMovement]:
    """
    Called strictly from kitchen.services.mark_served.
    Deducts inventory according to configured recipe.
    Rejects the transaction if stock is insufficient.
    Prevents duplicate deduction via idempotency check.
    """
    movements = []

    # Check idempotency: have we already consumed for this order line?
    if StockMovement.objects.filter(
        movement_type=StockMovement.MovementType.CONSUMPTION,
        reference=f"orderline:{order_line.id}"
    ).exists():
        return movements

    recipes = list(RecipeIngredient.objects.filter(menu_item=order_line.menu_item))
    if not recipes:
        return movements

    # Pre-sort items to avoid deadlocks in select_for_update
    item_ids = [r.inventory_item_id for r in recipes]
    # lock items
    items = {
        item.id: item
        for item in InventoryItem.objects.select_for_update().filter(id__in=item_ids)
    }

    for recipe in recipes:
        item = items[recipe.inventory_item_id]
        # Multiply per-serving recipe requirement by order line quantity
        required_qty = convert_quantity(recipe.quantity, recipe.unit, item.base_unit) * order_line.quantity

        if item.current_quantity < required_qty:
            raise ValueError(
                f"Insufficient stock for {item.name}. Required: {required_qty}, Available: {item.current_quantity}"
            )

        prev_balance = item.current_quantity
        item.current_quantity = F("current_quantity") - required_qty
        item.save(update_fields=["current_quantity", "updated_at"])
        item.refresh_from_db()

        mov = StockMovement.objects.create(
            item=item,
            quantity_delta=-required_qty,
            movement_type=StockMovement.MovementType.CONSUMPTION,
            actor=None,  # System action triggered by Waiter
            reference=f"orderline:{order_line.id}",
            reason=f"Consumed {required_qty} {item.base_unit} for {order_line.quantity}x {order_line.item_name}",
            previous_balance=prev_balance,
            new_balance=item.current_quantity
        )
        movements.append(mov)

    return movements
