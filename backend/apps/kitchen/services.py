from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.permissions import IsChef, IsWaiter
from apps.kitchen.models import KitchenEvent, KitchenTicket
from apps.orders.models import OrderBatch, OrderLine


def require_role(actor, permission):
    from types import SimpleNamespace

    if not permission().has_permission(SimpleNamespace(user=actor), None):
        raise PermissionDenied("Your role cannot perform this kitchen action.")


@transaction.atomic
def mark_preparing(*, order_line_id, actor):
    require_role(actor, IsChef)
    line = get_object_or_404(OrderLine.objects.select_for_update(), pk=order_line_id)
    if line.batch.status != OrderBatch.Status.APPROVED:
        raise ValidationError({"detail": "Only approved items can be prepared."})
    if line.batch.order.session.state != "open":
        raise ValidationError({"detail": "This dining session is closed."})

    ticket, created = KitchenTicket.objects.select_for_update().get_or_create(
        order_line=line, defaults={"status": KitchenTicket.Status.PREPARING}
    )
    if not created:
        return ticket, False  # Already transitioned or past preparing

    KitchenEvent.objects.create(ticket=ticket, actor=actor, kind=KitchenEvent.Kind.MARKED_PREPARING)
    return ticket, True


@transaction.atomic
def mark_ready(*, order_line_id, actor):
    require_role(actor, IsChef)
    line = get_object_or_404(OrderLine.objects.select_for_update(), pk=order_line_id)

    ticket = get_object_or_404(KitchenTicket.objects.select_for_update(), order_line=line)
    if ticket.status == KitchenTicket.Status.READY or ticket.status == KitchenTicket.Status.SERVED:
        return ticket, False
    if ticket.status != KitchenTicket.Status.PREPARING:
        raise ValidationError({"detail": "Item must be preparing before it can be marked ready."})

    ticket.status = KitchenTicket.Status.READY
    ticket.save(update_fields=["status", "updated_at"])

    KitchenEvent.objects.create(ticket=ticket, actor=actor, kind=KitchenEvent.Kind.MARKED_READY)
    return ticket, True


@transaction.atomic
def mark_served(*, order_line_id, actor):
    require_role(actor, IsWaiter)
    line = get_object_or_404(OrderLine.objects.select_for_update(), pk=order_line_id)

    ticket = get_object_or_404(KitchenTicket.objects.select_for_update(), order_line=line)
    if ticket.status == KitchenTicket.Status.SERVED:
        return ticket, False
    if ticket.status != KitchenTicket.Status.READY:
        raise ValidationError({"detail": "Item must be ready before it can be served."})

    ticket.status = KitchenTicket.Status.SERVED
    ticket.save(update_fields=["status", "updated_at"])

    KitchenEvent.objects.create(ticket=ticket, actor=actor, kind=KitchenEvent.Kind.MARKED_SERVED)
    return ticket, True
