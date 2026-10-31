import uuid
import pytest
from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.inventory.models import InventoryItem, RecipeIngredient, StockMovement
from apps.inventory.services import receive_stock
from apps.kitchen.services import mark_served, mark_preparing, mark_ready
from apps.orders.models import DiningSession, Order, OrderBatch, OrderLine
from apps.menu.models import Category, MenuItem
from apps.restaurants.models import DiningTable, Restaurant

User = get_user_model()

@pytest.fixture
def owner(db):
    user = User.objects.create_user(username="owner", role=User.Role.OWNER)
    user.is_active = True
    user.must_change_pin = False
    user.save()
    return user

@pytest.fixture
def waiter(db):
    user = User.objects.create_user(username="waiter", role=User.Role.WAITER)
    user.is_active = True
    user.must_change_pin = False
    user.save()
    return user

@pytest.fixture
def chef(db):
    user = User.objects.create_user(username="chef", role=User.Role.CHEF)
    user.is_active = True
    user.must_change_pin = False
    user.save()
    return user

@pytest.fixture
def base_inventory_item(db):
    return InventoryItem.objects.create(
        name="Test Rice",
        category="Grains",
        base_unit=InventoryItem.Unit.KILOGRAM,
        current_quantity=Decimal("10.000"),
        min_stock_threshold=Decimal("5.000")
    )

@pytest.fixture
def menu_item_setup(db, waiter):
    restaurant = Restaurant.objects.create(name="Test Rest")
    table = DiningTable.objects.create(restaurant=restaurant, name="Table 1")
    cat = Category.objects.create(name="Mains", restaurant=restaurant)
    menu_item = MenuItem.objects.create(name="Rice Bowl", category=cat, price=Decimal("100.00"))

    session = DiningSession.objects.create(table=table, opened_by=waiter)
    order = Order.objects.create(session=session, created_by=waiter)
    batch = OrderBatch.objects.create(order=order, status=OrderBatch.Status.APPROVED, sequence=1, idempotency_key=str(uuid.uuid4()), submitted_by=waiter, reviewed_by=waiter, reviewed_at=timezone.now())

    line = OrderLine.objects.create(batch=batch, menu_item=menu_item, item_name=menu_item.name, unit_price=menu_item.price, quantity=2, line_total=menu_item.price * 2)
    return line

@pytest.mark.django_db
def test_create_inventory_item(api_client, owner):
    api_client.force_authenticate(user=owner)
    response = api_client.post(reverse("api:inventory:inventoryitem-list"), {
        "name": "Chicken",
        "category": "Meat",
        "base_unit": "kg",
        "min_stock_threshold": "1.500"
    }, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    assert InventoryItem.objects.count() == 1

@pytest.mark.django_db
def test_receive_stock(base_inventory_item, owner):
    receive_stock(
        item_id=base_inventory_item.id,
        quantity=Decimal("5"),
        unit="kg",
        actor=owner,
        notes="Delivery"
    )
    base_inventory_item.refresh_from_db()
    assert base_inventory_item.current_quantity == Decimal("15.000")

@pytest.mark.django_db
def test_receive_stock_unit_conversion(base_inventory_item, owner):
    receive_stock(
        item_id=base_inventory_item.id,
        quantity=Decimal("500"),
        unit="g",
        actor=owner,
    )
    base_inventory_item.refresh_from_db()
    assert base_inventory_item.current_quantity == Decimal("10.500")

@pytest.mark.django_db
def test_kitchen_consumption(menu_item_setup, base_inventory_item, chef, waiter):
    # Setup recipe: 1 Rice Bowl uses 200g Rice
    RecipeIngredient.objects.create(
        menu_item=menu_item_setup.menu_item,
        inventory_item=base_inventory_item,
        quantity=Decimal("200"),
        unit="g"
    )

    # Progress through kitchen
    mark_preparing(order_line_id=menu_item_setup.id, actor=chef)
    mark_ready(order_line_id=menu_item_setup.id, actor=chef)

    # Serve: Should trigger consumption
    mark_served(order_line_id=menu_item_setup.id, actor=waiter)

    base_inventory_item.refresh_from_db()
    # 2 bowls * 200g = 400g = 0.4kg deduction from 10.000kg
    assert base_inventory_item.current_quantity == Decimal("9.600")

    # Ensure idempotent
    mark_served(order_line_id=menu_item_setup.id, actor=waiter)
    base_inventory_item.refresh_from_db()
    assert base_inventory_item.current_quantity == Decimal("9.600")

@pytest.mark.django_db
def test_insufficient_stock_rejection(menu_item_setup, base_inventory_item, chef, waiter):
    RecipeIngredient.objects.create(
        menu_item=menu_item_setup.menu_item,
        inventory_item=base_inventory_item,
        quantity=Decimal("6000"), # 6kg per bowl, order has 2 bowls = 12kg required. Only 10 available.
        unit="g"
    )
    mark_preparing(order_line_id=menu_item_setup.id, actor=chef)
    mark_ready(order_line_id=menu_item_setup.id, actor=chef)

    with pytest.raises(ValueError, match="Insufficient stock"):
        mark_served(order_line_id=menu_item_setup.id, actor=waiter)
