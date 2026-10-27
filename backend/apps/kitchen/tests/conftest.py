import pytest

from apps.accounts.models import User
from apps.menu.models import Category, MenuItem
from apps.orders.models import DiningSession, Order, OrderBatch, OrderLine
from apps.restaurants.models import DiningTable, Restaurant


@pytest.fixture
def owner_user():
    return User.objects.create_user(
        username="owner", role="owner", password="x", must_change_pin=False
    )


@pytest.fixture
def manager_user():
    return User.objects.create_user(
        username="manager", role="manager", password="x", must_change_pin=False
    )


@pytest.fixture
def cashier_user():
    return User.objects.create_user(
        username="cashier", role="cashier", password="x", must_change_pin=False
    )


@pytest.fixture
def waiter_user():
    return User.objects.create_user(
        username="waiter", role="waiter", password="x", must_change_pin=False
    )


@pytest.fixture
def chef_user():
    return User.objects.create_user(
        username="chef", role="chef", password="x", must_change_pin=False
    )


@pytest.fixture
def setup_restaurant():
    return Restaurant.objects.get_or_create(id=1, defaults={"name": "T", "currency": "NPR"})[0]


@pytest.fixture
def setup_approved_order(owner_user, waiter_user, cashier_user, setup_restaurant):
    t = DiningTable.objects.create(restaurant=setup_restaurant, name="Table 1")
    cat = Category.objects.create(restaurant=setup_restaurant, name="Drinks")
    item = MenuItem.objects.create(category=cat, name="Tea", price="100.00")

    session = DiningSession.objects.create(table=t, opened_by=waiter_user)
    order = Order.objects.create(session=session, created_by=waiter_user)

    batch = OrderBatch.objects.create(
        order=order,
        sequence=1,
        submitted_by=waiter_user,
        idempotency_key="00000000-0000-0000-0000-000000000000",
        request_fingerprint="abc",
        status=OrderBatch.Status.APPROVED,
        reviewed_by=cashier_user,
        reviewed_at="2026-10-25T12:00:00Z",
    )
    line = OrderLine.objects.create(
        batch=batch,
        menu_item=item,
        item_name="Tea",
        unit_price="100.00",
        quantity=2,
        line_total="200.00",
    )
    return line


@pytest.fixture
def setup_pending_order(owner_user, waiter_user, setup_restaurant):
    t = DiningTable.objects.create(restaurant=setup_restaurant, name="Table 2")
    cat = Category.objects.create(restaurant=setup_restaurant, name="Food")
    item = MenuItem.objects.create(category=cat, name="Momo", price="200.00")

    session = DiningSession.objects.create(table=t, opened_by=waiter_user)
    order = Order.objects.create(session=session, created_by=waiter_user)

    batch = OrderBatch.objects.create(
        order=order,
        sequence=1,
        submitted_by=waiter_user,
        idempotency_key="10000000-0000-0000-0000-000000000000",
        request_fingerprint="def",
        status=OrderBatch.Status.PENDING,
    )
    line = OrderLine.objects.create(
        batch=batch,
        menu_item=item,
        item_name="Momo",
        unit_price="200.00",
        quantity=1,
        line_total="200.00",
    )
    return line
