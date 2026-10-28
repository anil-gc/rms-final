import uuid
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.billing.services import generate_draft_bill
from apps.orders.models import DiningSession, Order, OrderBatch, OrderLine
from apps.restaurants.models import DiningTable, Restaurant


@pytest.fixture
def api_setup(db, django_user_model):
    waiter = django_user_model.objects.create(username="waiter", role="waiter")
    cashier = django_user_model.objects.create(username="cashier", role="cashier")

    restaurant = Restaurant.objects.create(name="RMS")
    table = DiningTable.objects.create(
        restaurant=restaurant, name="Table 1", status=DiningTable.Status.OCCUPIED
    )
    session = DiningSession.objects.create(table=table, opened_by=waiter)
    order = Order.objects.create(session=session, created_by=waiter)

    from apps.menu.models import Category, MenuItem

    cat = Category.objects.create(restaurant=restaurant, name="Mains")
    item = MenuItem.objects.create(category=cat, name="Momo", price=Decimal("150.00"))

    batch = OrderBatch.objects.create(
        order=order,
        sequence=1,
        submitted_by=waiter,
        idempotency_key=uuid.uuid4(),
        request_fingerprint="abc",
        status=OrderBatch.Status.APPROVED,
        reviewed_by=cashier,
        reviewed_at="2024-01-01T00:00:00Z",
    )

    oline = OrderLine.objects.create(
        batch=batch,
        menu_item=item,
        item_name="Momo",
        unit_price=Decimal("150.00"),
        quantity=2,
        line_total=Decimal("300.00"),
    )

    from apps.kitchen.models import KitchenTicket

    KitchenTicket.objects.create(order_line=oline, status=KitchenTicket.Status.SERVED)

    bill = generate_draft_bill(session_id=session.id)

    client = APIClient()
    return {"client": client, "cashier": cashier, "session": session, "bill": bill}


def test_active_tables_list(api_setup):
    client = api_setup["client"]
    client.force_authenticate(user=api_setup["cashier"])

    response = client.get("/api/v1/billing/active-tables/")
    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]["grand_total"] == "300.00"
    assert response.data[0]["status"] == "draft"


def test_finalize_bill(api_setup):
    client = api_setup["client"]
    client.force_authenticate(user=api_setup["cashier"])
    bill = api_setup["bill"]

    response = client.post(f"/api/v1/billing/bill/{bill.id}/finalize/")
    assert response.status_code == 200
    assert response.data["status"] == "finalized"


def test_payment_and_checkout(api_setup):
    client = api_setup["client"]
    client.force_authenticate(user=api_setup["cashier"])
    bill = api_setup["bill"]

    # Finalize first
    client.post(f"/api/v1/billing/bill/{bill.id}/finalize/")

    # Pay
    pay_resp = client.post(
        f"/api/v1/billing/bill/{bill.id}/payments/",
        {"amount": "300.00", "method": "cash", "idempotency_key": str(uuid.uuid4())},
        format="json",
    )

    assert pay_resp.status_code == 201
    assert pay_resp.data["amount"] == "300.00"

    # Checkout
    session = api_setup["session"]
    chk_resp = client.post(f"/api/v1/billing/session/{session.id}/checkout/")
    assert chk_resp.status_code == 200
    assert chk_resp.data["success"] is True
