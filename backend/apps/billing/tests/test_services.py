import uuid
from decimal import Decimal

import pytest

from apps.billing.models import Bill, Payment
from apps.billing.services import (
    checkout_table,
    finalize_bill,
    generate_draft_bill,
    record_payment,
)
from apps.orders.models import DiningSession, Order, OrderBatch, OrderLine
from apps.restaurants.models import DiningTable, Restaurant


@pytest.fixture
def checkout_setup(db, django_user_model):
    waiter = django_user_model.objects.create(username="waiter", role="waiter")
    cashier = django_user_model.objects.create(username="cashier", role="cashier")
    restaurant = Restaurant.objects.create(name="RMS")
    table = DiningTable.objects.create(
        restaurant=restaurant, name="Table 1", status=DiningTable.Status.OCCUPIED
    )
    session = DiningSession.objects.create(table=table, opened_by=waiter)
    order = Order.objects.create(session=session, created_by=waiter)
    return {
        "waiter": waiter,
        "cashier": cashier,
        "table": table,
        "session": session,
        "order": order,
    }


@pytest.fixture
def mock_menu_item(db, checkout_setup):
    from apps.menu.models import Category, MenuItem

    restaurant = checkout_setup["table"].restaurant
    cat = Category.objects.create(restaurant=restaurant, name="Mains")
    return MenuItem.objects.create(category=cat, name="Momo", price=Decimal("150.00"))


def test_generate_draft_bill_unresolved_ignored(checkout_setup, mock_menu_item):
    session = checkout_setup["session"]
    order = checkout_setup["order"]
    waiter = checkout_setup["waiter"]

    batch = OrderBatch.objects.create(
        order=order,
        sequence=1,
        submitted_by=waiter,
        idempotency_key=uuid.uuid4(),
        request_fingerprint="abc",
        status=OrderBatch.Status.APPROVED,
        reviewed_by=checkout_setup["cashier"],
        reviewed_at="2024-01-01T00:00:00Z",
    )

    # Create order line but don't mark it served in kitchen
    OrderLine.objects.create(
        batch=batch,
        menu_item=mock_menu_item,
        item_name="Momo",
        unit_price=Decimal("150.00"),
        quantity=2,
        line_total=Decimal("300.00"),
    )

    bill = generate_draft_bill(session_id=session.id)
    assert bill.status == Bill.Status.DRAFT
    assert bill.grand_total == Decimal("0.00")  # Because it hasn't been served
    assert bill.lines.count() == 0


def test_generate_draft_bill_served(checkout_setup, mock_menu_item):
    session = checkout_setup["session"]
    order = checkout_setup["order"]
    waiter = checkout_setup["waiter"]

    batch = OrderBatch.objects.create(
        order=order,
        sequence=1,
        submitted_by=waiter,
        idempotency_key=uuid.uuid4(),
        request_fingerprint="abc",
        status=OrderBatch.Status.APPROVED,
        reviewed_by=checkout_setup["cashier"],
        reviewed_at="2024-01-01T00:00:00Z",
    )

    oline = OrderLine.objects.create(
        batch=batch,
        menu_item=mock_menu_item,
        item_name="Momo",
        unit_price=Decimal("150.00"),
        quantity=2,
        line_total=Decimal("300.00"),
    )

    from apps.kitchen.models import KitchenTicket

    KitchenTicket.objects.create(order_line=oline, status=KitchenTicket.Status.SERVED)

    bill = generate_draft_bill(session_id=session.id)
    assert bill.status == Bill.Status.DRAFT
    assert bill.grand_total == Decimal("300.00")
    assert bill.lines.count() == 1


def test_payment_idempotency_and_checkout(checkout_setup, mock_menu_item):
    session = checkout_setup["session"]
    order = checkout_setup["order"]
    waiter = checkout_setup["waiter"]
    cashier = checkout_setup["cashier"]

    batch = OrderBatch.objects.create(
        order=order,
        sequence=1,
        submitted_by=waiter,
        idempotency_key=uuid.uuid4(),
        request_fingerprint="abc",
        status=OrderBatch.Status.APPROVED,
        reviewed_by=checkout_setup["cashier"],
        reviewed_at="2024-01-01T00:00:00Z",
    )

    oline = OrderLine.objects.create(
        batch=batch,
        menu_item=mock_menu_item,
        item_name="Momo",
        unit_price=Decimal("150.00"),
        quantity=2,
        line_total=Decimal("300.00"),
    )

    from apps.kitchen.models import KitchenTicket

    KitchenTicket.objects.create(order_line=oline, status=KitchenTicket.Status.SERVED)

    generate_draft_bill(session_id=session.id)
    bill = finalize_bill(bill_id=Bill.objects.get(session=session).id, actor=cashier)

    assert bill.status == Bill.Status.FINALIZED

    key = uuid.uuid4()
    p1 = record_payment(
        bill_id=bill.id,
        actor=cashier,
        amount=Decimal("300.00"),
        method=Payment.Method.CASH,
        idempotency_key=key,
    )
    p2 = record_payment(
        bill_id=bill.id,
        actor=cashier,
        amount=Decimal("300.00"),
        method=Payment.Method.CASH,
        idempotency_key=key,
    )

    assert p1.id == p2.id  # Idempotent return
    bill.refresh_from_db()
    assert bill.status == Bill.Status.PAID

    s_ret, _ = checkout_table(session_id=session.id, actor=cashier)
    assert s_ret.state == DiningSession.State.CLOSED

    # Table should be available
    checkout_setup["table"].refresh_from_db()
    assert checkout_setup["table"].status == DiningTable.Status.AVAILABLE
