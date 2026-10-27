"""Business entry points. All writes validate the actor, even outside HTTP."""

import hashlib
import json
from uuid import UUID

from django.db import transaction
from django.db.models import Max
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError

from apps.accounts.permissions import IsCashier, IsWaiter
from apps.menu.models import Category, MenuItem
from apps.restaurants.models import DiningTable, Restaurant

from .models import DiningSession, Order, OrderBatch, OrderEvent, OrderLine


class OrderConflict(APIException):
    status_code = 409
    default_detail = "The order changed. Refresh before trying again."
    default_code = "order_conflict"


def require_role(actor, permission):
    # Reuse existing role/PIN readiness rules without changing authentication.
    from types import SimpleNamespace

    if not permission().has_permission(SimpleNamespace(user=actor), None):
        raise PermissionDenied("Your role cannot perform this order action.")


def _event(order, actor, kind, batch=None, reason=""):
    return OrderEvent.objects.create(
        order=order, actor=actor, kind=kind, batch=batch, reason=reason
    )


@transaction.atomic
def open_session(*, table_id, actor):
    require_role(actor, IsWaiter)
    table = get_object_or_404(DiningTable.objects.select_for_update(), pk=table_id)
    restaurant = get_object_or_404(Restaurant.objects.select_for_update(), pk=table.restaurant_id)
    if not table.is_active or not restaurant.is_active:
        raise ValidationError({"detail": "This table or restaurant is unavailable."})
    session = DiningSession.objects.filter(table=table, state=DiningSession.State.OPEN).first()
    if session:
        return session.order, False
    if table.status != DiningTable.Status.AVAILABLE:
        raise OrderConflict(
            "This table was marked occupied manually. Ask management to reconcile it."
        )
    session = DiningSession.objects.create(table=table, opened_by=actor)
    order = Order.objects.create(session=session, created_by=actor)
    table.status = DiningTable.Status.OCCUPIED
    table.save(update_fields=["status", "updated_at"])
    _event(order, actor, OrderEvent.Kind.SESSION_OPENED)
    _event(order, actor, OrderEvent.Kind.ORDER_CREATED)
    return order, True


def validate_lines(lines):
    if not isinstance(lines, list) or not 1 <= len(lines) <= 50:
        raise ValidationError({"detail": "Submit between 1 and 50 distinct items."})
    result = []
    for line in lines:
        if not isinstance(line, dict) or set(line) != {"menu_item", "quantity"}:
            raise ValidationError({"detail": "Each item needs only menu_item and quantity."})
        item, quantity = line["menu_item"], line["quantity"]
        if (
            type(item) is not int
            or not 1 <= item <= 9223372036854775807
            or type(quantity) is not int
            or not 1 <= quantity <= 99
        ):
            raise ValidationError(
                {"detail": "Use valid item IDs and whole quantities from 1 to 99."}
            )
        result.append({"menu_item": item, "quantity": quantity})
    if len({line["menu_item"] for line in result}) != len(result):
        raise ValidationError({"detail": "Combine quantities for each item before submitting."})
    return sorted(result, key=lambda line: line["menu_item"])


@transaction.atomic
def submit_batch(*, order_id, actor, idempotency_key, lines):
    require_role(actor, IsWaiter)
    lines = validate_lines(lines)
    try:
        key = UUID(str(idempotency_key))
    except (ValueError, TypeError, AttributeError) as error:
        raise ValidationError({"detail": "A valid UUID idempotency key is required."}) from error
    fingerprint = hashlib.sha256(json.dumps(lines, separators=(",", ":")).encode()).hexdigest()
    reference = get_object_or_404(Order.objects.select_related("session"), pk=order_id)
    table = DiningTable.objects.select_for_update().get(pk=reference.session.table_id)
    order = Order.objects.select_for_update().select_related("session").get(pk=order_id)
    existing = OrderBatch.objects.filter(
        order=order, submitted_by=actor, idempotency_key=key
    ).first()
    if existing:
        if existing.request_fingerprint != fingerprint:
            raise OrderConflict("This submission key was already used for different items.")
        return existing, False
    if order.session.state != DiningSession.State.OPEN:
        raise OrderConflict("This dining session is closed.")
    # Match catalogue update lock ordering: item -> category -> restaurant.
    items = list(
        MenuItem.objects.select_for_update()
        .filter(pk__in=[line["menu_item"] for line in lines])
        .order_by("pk")
    )
    categories = {
        category.pk: category
        for category in Category.objects.select_for_update()
        .filter(pk__in={item.category_id for item in items})
        .order_by("pk")
    }
    restaurant = Restaurant.objects.select_for_update().get(pk=table.restaurant_id)
    if (
        not table.is_active
        or table.status != DiningTable.Status.OCCUPIED
        or not restaurant.is_active
    ):
        raise ValidationError({"detail": "This table or restaurant is unavailable."})
    if len(items) != len(lines) or any(
        not (
            item.is_active
            and item.is_available
            and categories[item.category_id].is_active
            and categories[item.category_id].restaurant_id == restaurant.pk
        )
        for item in items
    ):
        raise ValidationError(
            {"detail": "Some items are unavailable. Refresh the menu and review."}
        )
    sequence = (order.batches.aggregate(last=Max("sequence"))["last"] or 0) + 1
    batch = OrderBatch.objects.create(
        order=order,
        sequence=sequence,
        submitted_by=actor,
        idempotency_key=key,
        request_fingerprint=fingerprint,
    )
    quantities = {line["menu_item"]: line["quantity"] for line in lines}
    OrderLine.objects.bulk_create(
        [
            OrderLine(
                batch=batch,
                menu_item=item,
                item_name=item.name,
                unit_price=item.price,
                quantity=quantities[item.pk],
                line_total=item.price * quantities[item.pk],
            )
            for item in items
        ]
    )
    _event(order, actor, OrderEvent.Kind.BATCH_SUBMITTED, batch=batch)
    return batch, True


@transaction.atomic
def review_batch(*, batch_id, actor, decision, reason=""):
    require_role(actor, IsCashier)
    if decision not in (OrderBatch.Status.APPROVED, OrderBatch.Status.REJECTED):
        raise ValidationError({"detail": "Choose approve or reject."})
    if not isinstance(reason, str) or len(reason.strip()) > 500:
        raise ValidationError({"reason": "Use a reason of at most 500 characters."})
    reason = reason.strip()
    if decision == OrderBatch.Status.REJECTED and not reason:
        raise ValidationError({"reason": "A rejection reason is required."})
    if decision == OrderBatch.Status.APPROVED and reason:
        raise ValidationError({"reason": "Approval does not accept a rejection reason."})
    batch = get_object_or_404(OrderBatch.objects.select_for_update(), pk=batch_id)
    if batch.status != OrderBatch.Status.PENDING:
        raise OrderConflict("This batch has already been reviewed. Refresh to see the decision.")
    if batch.order.session.state != DiningSession.State.OPEN:
        raise OrderConflict("This dining session is closed.")
    batch.status, batch.reviewed_by, batch.reviewed_at = decision, actor, timezone.now()
    batch.rejection_reason = reason
    batch.save(update_fields=["status", "reviewed_by", "reviewed_at", "rejection_reason"])
    _event(
        batch.order,
        actor,
        (
            OrderEvent.Kind.BATCH_APPROVED
            if decision == "approved"
            else OrderEvent.Kind.BATCH_REJECTED
        ),
        batch=batch,
        reason=reason,
    )
    return batch


def approved_lines():
    """Future kitchen integration boundary; no preparation/ready operations."""
    return OrderLine.objects.filter(
        batch__status=OrderBatch.Status.APPROVED, batch__order__session__state="open"
    ).select_related("batch__order__session__table")
