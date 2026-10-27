import pytest
from rest_framework.exceptions import PermissionDenied

from apps.kitchen.models import KitchenTicket
from apps.kitchen.services import mark_preparing, mark_ready, mark_served


@pytest.mark.django_db(transaction=True)
def test_kitchen_workflow(chef_user, waiter_user, cashier_user, setup_approved_order):
    # setup_approved_order should create an order line
    order_line = setup_approved_order

    # 1. Chef marks preparing
    ticket, created = mark_preparing(order_line_id=order_line.id, actor=chef_user)
    assert created
    assert ticket.status == KitchenTicket.Status.PREPARING

    # 2. Chef marks ready
    ticket, created = mark_ready(order_line_id=order_line.id, actor=chef_user)
    assert ticket.status == KitchenTicket.Status.READY

    # Waiter cannot mark preparing
    with pytest.raises(PermissionDenied):
        mark_preparing(order_line_id=order_line.id, actor=waiter_user)

    # Chef cannot mark served
    with pytest.raises(PermissionDenied):
        mark_served(order_line_id=order_line.id, actor=chef_user)

    # 3. Waiter marks served
    ticket, updated = mark_served(order_line_id=order_line.id, actor=waiter_user)
    assert ticket.status == KitchenTicket.Status.SERVED

    # Test invalid transition (served -> ready is not allowed by API), it returns False
    ticket, updated = mark_ready(order_line_id=order_line.id, actor=chef_user)
    assert not updated
