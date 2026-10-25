from decimal import Decimal
from io import BytesIO

import pytest
from django.contrib import admin
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, connection, transaction
from django.utils import timezone
from PIL import Image

from apps.accounts.models import User
from apps.menu.models import Category, MenuItem
from apps.restaurants.models import DiningTable, Restaurant

pytestmark = pytest.mark.django_db


@pytest.fixture
def restaurant():
    return Restaurant.objects.create(name="Test restaurant")


@pytest.fixture
def category(restaurant):
    return Category.objects.create(restaurant=restaurant, name="Momo")


@pytest.fixture
def menu_item(category):
    return MenuItem.objects.create(category=category, name="Vegetable momo", price="180.00")


@pytest.fixture
def table(restaurant):
    return DiningTable.objects.create(restaurant=restaurant, name="T01", capacity=4)


def logo_file(size=(30, 30), name="logo.png"):
    content = BytesIO()
    Image.new("RGB", size, "green").save(content, "PNG")
    return SimpleUploadedFile(name, content.getvalue(), content_type="image/png")


@pytest.mark.parametrize(
    "path", ["restaurant/", "restaurant/logo/", "tables/", "menu/categories/", "menu/items/"]
)
def test_workspace_requires_provisioned_ready_session(path, api_client, session_client, staff):
    url = "/api/v1/" + path
    assert api_client.get(url).status_code == 403
    staff.must_change_pin = True
    staff.save()
    client = session_client(staff)
    assert client.get(url).status_code == 403
    assert (
        client.post(
            url, {}, format="multipart" if path == "restaurant/logo/" else "json"
        ).status_code
        == 403
    )


@pytest.mark.parametrize("role", User.Role.values)
def test_workspace_role_matrix(role, session_client, restaurant, category, table):
    user = User.objects.create_user(username=f"role-{role}", role=role)
    client = session_client(user)
    manage = role in {"owner", "manager"}
    for path in ["restaurant/", "tables/", "menu/categories/", "menu/items/"]:
        response = client.get("/api/v1/" + path)
        assert response.status_code == 200
        assert "no-store" in response["Cache-Control"]
    for path, payload in [
        ("restaurant/", {"name": "Updated"}),
        (f"tables/{table.pk}/", {"status": "occupied"}),
        (f"menu/categories/{category.pk}/", {"name": "Updated category"}),
    ]:
        assert client.patch("/api/v1/" + path, payload, format="json").status_code == (
            200 if manage else 403
        )
    for path, payload in [
        ("tables/", {"name": "T02", "capacity": 2}),
        ("menu/categories/", {"name": "Drinks"}),
        ("menu/items/", {"name": "Steam momo", "category": category.pk, "price": "200.50"}),
    ]:
        assert client.post("/api/v1/" + path, payload, format="json").status_code == (
            201 if manage else 403
        )
    assert client.delete("/api/v1/restaurant/logo/").status_code == (204 if manage else 403)


def test_unassigned_superuser_cannot_access_workspace(session_client, restaurant):
    user = User.objects.create_user(username="legacy-admin", is_superuser=True, is_staff=True)
    assert session_client(user).get("/api/v1/restaurant/").status_code == 403


def test_csrf_is_enforced_for_all_workspace_mutations(owner, restaurant, category, table):
    from rest_framework.test import APIClient

    client = APIClient(enforce_csrf_checks=True)
    client.force_login(owner)
    for path in ["restaurant/", f"tables/{table.pk}/", f"menu/categories/{category.pk}/"]:
        assert client.patch("/api/v1/" + path, {}, format="json").status_code == 403
    assert client.post("/api/v1/menu/items/", {}, format="json").status_code == 403
    assert (
        client.post(
            "/api/v1/restaurant/logo/", {"logo": logo_file()}, format="multipart"
        ).status_code
        == 403
    )


def test_restaurant_setup_is_non_overwriting_singleton(owner_client):
    assert owner_client.get("/api/v1/restaurant/").status_code == 404
    payload = {
        "name": "Himalaya kitchen",
        "currency": "NPR",
        "opening_time": "18:00",
        "closing_time": "02:00",
        "email": "team@example.test",
        "contact_phone": "+977 9801234567",
    }
    response = owner_client.post("/api/v1/restaurant/", payload, format="json")
    assert response.status_code == 201
    assert response.data["logo_url"] is None
    assert response.data["opening_time"] == "18:00:00"
    assert (
        owner_client.post("/api/v1/restaurant/", {"name": "Replace"}, format="json").status_code
        == 400
    )
    assert Restaurant.objects.get().name == payload["name"]
    with pytest.raises(IntegrityError), transaction.atomic():
        Restaurant.objects.create(id=2, name="Second")


@pytest.mark.parametrize(
    "payload",
    [
        {"name": " "},
        {"currency": "USD"},
        {"email": "not-email"},
        {"contact_phone": "abc1234"},
        {"contact_phone": "123"},
        {"opening_time": "09:00"},
        {"opening_time": "09:00", "closing_time": "09:00"},
        {"id": 2},
        {"restaurant": 2},
        {"logo": "https://example.test/remote.svg"},
        {"unknown": True},
    ],
)
def test_restaurant_invalid_updates_are_atomic(payload, owner_client, restaurant):
    assert owner_client.patch("/api/v1/restaurant/", payload, format="json").status_code == 400
    restaurant.refresh_from_db()
    assert restaurant.name == "Test restaurant" and restaurant.currency == "NPR"


def test_restaurant_partial_hours_merge_and_clear(owner_client, restaurant):
    restaurant.opening_time, restaurant.closing_time = "09:00", "22:00"
    restaurant.save()
    assert (
        owner_client.patch(
            "/api/v1/restaurant/", {"opening_time": "22:00"}, format="json"
        ).status_code
        == 400
    )
    assert (
        owner_client.patch("/api/v1/restaurant/", {"opening_time": None}, format="json").status_code
        == 400
    )
    assert (
        owner_client.patch(
            "/api/v1/restaurant/", {"opening_time": None, "closing_time": None}, format="json"
        ).status_code
        == 200
    )


@pytest.mark.parametrize(
    "path,payload", [("tables/", {"name": "T01"}), ("menu/categories/", {"name": "Drinks"})]
)
def test_profile_setup_required_before_related_creation(path, payload, owner_client):
    response = owner_client.post("/api/v1/" + path, payload, format="json")
    assert response.status_code == 400
    assert "profile first" in response.data["detail"]


def test_category_item_archive_and_availability(owner_client, session_client, staff, menu_item):
    category = menu_item.category
    client = session_client(staff)
    url = f"/api/v1/menu/items/{menu_item.pk}/"
    assert (
        owner_client.patch(
            url, {"price": "255.75", "is_available": False}, format="json"
        ).status_code
        == 200
    )
    menu_item.refresh_from_db()
    assert menu_item.price == Decimal("255.75")
    assert client.get(url).data["effective_available"] is False
    assert owner_client.patch(url, {"is_available": True}, format="json").status_code == 200
    assert client.get(url).data["effective_available"] is True
    assert (
        owner_client.patch(
            f"/api/v1/menu/categories/{category.pk}/", {"is_active": False}, format="json"
        ).status_code
        == 200
    )
    assert client.get("/api/v1/menu/categories/").data == []
    assert client.get("/api/v1/menu/items/").data == []
    assert client.get(url).status_code == 404
    assert owner_client.get(url).data["effective_available"] is False
    assert MenuItem.objects.filter(pk=menu_item.pk).exists()
    assert (
        owner_client.patch(
            f"/api/v1/menu/categories/{category.pk}/", {"is_active": True}, format="json"
        ).status_code
        == 200
    )
    assert client.get(url).status_code == 200
    assert owner_client.patch(url, {"is_active": False}, format="json").status_code == 200
    assert client.get(url).status_code == 404
    assert owner_client.get(url).status_code == 200


def test_restaurant_inactive_makes_menu_unavailable(owner_client, menu_item):
    assert (
        owner_client.patch("/api/v1/restaurant/", {"is_active": False}, format="json").status_code
        == 200
    )
    response = owner_client.get(f"/api/v1/menu/items/{menu_item.pk}/")
    assert response.data["is_available"] is True and response.data["effective_available"] is False
    assert (
        owner_client.patch("/api/v1/restaurant/", {"is_active": True}, format="json").status_code
        == 200
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"price": "0"},
        {"price": "-1"},
        {"price": "1.005"},
        {"price": "NaN"},
        {"price": "100000000"},
        {"category": 999999},
        {"name": " "},
        {"restaurant": 1},
        {"effective_available": True},
    ],
)
def test_invalid_menu_item_changes(payload, owner_client, menu_item):
    assert (
        owner_client.patch(
            f"/api/v1/menu/items/{menu_item.pk}/", payload, format="json"
        ).status_code
        == 400
    )
    menu_item.refresh_from_db()
    assert menu_item.price == Decimal("180.00")


def test_case_insensitive_names_and_item_category_scope(
    owner_client, restaurant, category, menu_item, table
):
    assert (
        owner_client.post(
            "/api/v1/menu/categories/", {"name": "  MOMO  "}, format="json"
        ).status_code
        == 400
    )
    assert owner_client.post("/api/v1/tables/", {"name": "t01"}, format="json").status_code == 400
    data = {"name": " VEGETABLE MOMO ", "category": category.pk, "price": "100"}
    assert owner_client.post("/api/v1/menu/items/", data, format="json").status_code == 400
    other = Category.objects.create(restaurant=restaurant, name="Other")
    data["category"] = other.pk
    assert owner_client.post("/api/v1/menu/items/", data, format="json").status_code == 201
    with pytest.raises(IntegrityError), transaction.atomic():
        Category.objects.create(restaurant=restaurant, name=" MOMO ")
    with pytest.raises(IntegrityError), transaction.atomic():
        DiningTable.objects.create(restaurant=restaurant, name="t01")


@pytest.mark.parametrize(
    "payload",
    [
        {"capacity": 0},
        {"capacity": 51},
        {"capacity": "1.5"},
        {"status": "reserved"},
        {"restaurant": 1},
        {"name": " "},
    ],
)
def test_invalid_table_changes(payload, owner_client, table):
    assert (
        owner_client.patch(f"/api/v1/tables/{table.pk}/", payload, format="json").status_code == 400
    )
    table.refresh_from_db()
    assert table.capacity == 4 and table.status == "available"


def test_table_occupancy_and_archive(owner_client, session_client, staff, table):
    url = f"/api/v1/tables/{table.pk}/"
    assert owner_client.patch(url, {"status": "occupied"}, format="json").status_code == 200
    assert owner_client.patch(url, {"is_active": False}, format="json").status_code == 400
    assert (
        owner_client.patch(
            url, {"status": "available", "is_active": False}, format="json"
        ).status_code
        == 200
    )
    assert session_client(staff).get(url).status_code == 404
    assert owner_client.patch(url, {"status": "occupied"}, format="json").status_code == 400
    assert owner_client.patch(url, {"is_active": True}, format="json").status_code == 200
    assert session_client(staff).get(url).status_code == 200


@pytest.mark.parametrize(
    "path", ["restaurant/", "tables/1/", "menu/categories/1/", "menu/items/1/"]
)
def test_no_hard_delete_or_put(path, owner_client, restaurant, category, menu_item, table):
    assert owner_client.delete("/api/v1/" + path).status_code == 405
    assert owner_client.put("/api/v1/" + path, {}, format="json").status_code == 405


@pytest.mark.django_db(transaction=True)
def test_logo_reencoding_protected_delivery_replace_remove(
    owner_client,
    session_client,
    staff,
    restaurant,
    settings,
    tmp_path,
    django_capture_on_commit_callbacks,
):
    settings.MEDIA_ROOT = tmp_path
    url = "/api/v1/restaurant/logo/"
    with django_capture_on_commit_callbacks(execute=True):
        response = owner_client.post(
            url, {"logo": logo_file(name="unsafe-name.html.png")}, format="multipart"
        )
    assert response.status_code == 200
    assert response.data["logo_url"].startswith(url)
    restaurant.refresh_from_db()
    old_path = restaurant.logo.path
    assert restaurant.logo.name.endswith(".png") and "unsafe-name" not in restaurant.logo.name
    with Image.open(old_path) as normalized:
        assert normalized.format == "PNG" and not normalized.info
    response = session_client(staff).get(url)
    assert response.status_code == 200 and response["Content-Type"] == "image/png"
    assert "no-store" in response["Cache-Control"]
    assert b"".join(response.streaming_content).startswith(b"\x89PNG")
    response.close()
    with django_capture_on_commit_callbacks(execute=True):
        assert owner_client.post(url, {"logo": logo_file()}, format="multipart").status_code == 200
    from pathlib import Path

    assert not Path(old_path).exists()
    with django_capture_on_commit_callbacks(execute=True):
        assert owner_client.delete(url).status_code == 204
    assert owner_client.get(url).status_code == 404


@pytest.mark.parametrize("kind", ["svg", "invalid", "large", "dimensions", "unknown"])
def test_invalid_logos_do_not_replace_existing(kind, owner_client, restaurant, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    if kind == "dimensions":
        upload = logo_file(size=(2049, 1))
    elif kind == "large":
        upload = SimpleUploadedFile("big.png", b"x" * (2 * 1024 * 1024 + 1))
    else:
        upload = SimpleUploadedFile(
            "file.svg", b"<svg><script>alert(1)</script></svg>", content_type="image/svg+xml"
        )
    payload = {"logo": upload} if kind != "unknown" else {"logo": logo_file(), "is_active": "false"}
    assert (
        owner_client.post("/api/v1/restaurant/logo/", payload, format="multipart").status_code
        == 400
    )
    restaurant.refresh_from_db()
    assert not restaurant.logo


def test_logo_is_unavailable_to_anonymous_or_temporary_sessions(
    owner_client, restaurant, settings, tmp_path, api_client, session_client, staff
):
    settings.MEDIA_ROOT = tmp_path
    assert (
        owner_client.post(
            "/api/v1/restaurant/logo/", {"logo": logo_file()}, format="multipart"
        ).status_code
        == 200
    )
    assert api_client.get("/api/v1/restaurant/logo/").status_code == 403
    staff.must_change_pin = True
    staff.save()
    assert session_client(staff).get("/api/v1/restaurant/logo/").status_code == 403


def test_admin_is_read_only_for_workspace_records(owner, restaurant, category, menu_item, table):
    from django.test import RequestFactory

    request = RequestFactory().get("/admin/")
    request.user = owner
    for model in [Restaurant, Category, MenuItem, DiningTable]:
        model_admin = admin.site._registry[model]
        assert model_admin.has_view_permission(request)
        assert not model_admin.has_add_permission(request)
        assert not model_admin.has_change_permission(request)
        assert not model_admin.has_delete_permission(request)


@pytest.mark.parametrize("price", ["0", "-0.01", "NaN"])
def test_price_constraints_protect_direct_database_writes(category, price):
    with pytest.raises(IntegrityError), transaction.atomic():
        # Bypass DecimalField conversion (which already rejects NaN) to exercise
        # the PostgreSQL constraint itself for all three invalid values.
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO menu_menuitem "
                "(name, description, price, category_id, is_available, is_active, updated_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                ["Invalid direct item", "", price, category.pk, True, True, timezone.now()],
            )


@pytest.mark.parametrize(
    "values",
    [
        {"capacity": 0},
        {"capacity": 51},
        {"status": "reserved"},
        {"status": "occupied", "is_active": False},
    ],
)
def test_table_constraints_protect_direct_database_writes(restaurant, values):
    with pytest.raises(IntegrityError), transaction.atomic():
        DiningTable.objects.create(restaurant=restaurant, name="Invalid direct table", **values)


def test_related_records_are_protected_from_direct_hard_delete(
    restaurant, category, menu_item, table
):
    from django.db.models.deletion import ProtectedError

    with pytest.raises(ProtectedError):
        category.delete()
    with pytest.raises(ProtectedError):
        restaurant.delete()
