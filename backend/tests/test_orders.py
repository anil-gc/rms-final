from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
from uuid import uuid4

import pytest
from django.contrib import admin
from django.core.exceptions import ValidationError as ModelValidationError
from django.db import IntegrityError, close_old_connections, connections, transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.models import User
from apps.menu.models import Category, MenuItem
from apps.orders.models import DiningSession, Order, OrderBatch, OrderEvent, OrderLine
from apps.orders.services import (
    OrderConflict,
    approved_lines,
    open_session,
    review_batch,
    submit_batch,
)
from apps.restaurants.models import DiningTable, Restaurant

pytestmark = pytest.mark.django_db


@pytest.fixture
def domain(staff):
    restaurant = Restaurant.objects.create(name="Order tests")
    category = Category.objects.create(restaurant=restaurant, name="Meals")
    item = MenuItem.objects.create(category=category, name="Momo", price="200.05")
    table = DiningTable.objects.create(restaurant=restaurant, name="T5")
    cashier = User.objects.create_user(username="cashier-orders", role="cashier")
    return restaurant, category, item, table, staff, cashier


def opened(domain):
    return open_session(table_id=domain[3].pk, actor=domain[4])[0]


def submitted(domain, order=None, key=None, quantity=2):
    return submit_batch(
        order_id=(order or opened(domain)).pk,
        actor=domain[4],
        idempotency_key=key or uuid4(),
        lines=[{"menu_item": domain[2].pk, "quantity": quantity}],
    )[0]


def test_waiter_session_batches_history_and_snapshots(domain, session_client):
    restaurant, category, item, table, waiter, cashier = domain
    client = session_client(waiter)
    url = f"/api/v1/orders/tables/{table.pk}/"
    assert client.get(url + "active/").json() == {"order": None}
    response = client.post(url + "open/", {}, format="json")
    assert response.status_code == 201
    order_id = response.json()["id"]
    assert client.post(url + "open/", {}, format="json").json()["id"] == order_id
    table.refresh_from_db()
    assert table.status == "occupied"
    key = str(uuid4())
    payload = {"idempotency_key": key, "lines": [{"menu_item": item.pk, "quantity": 2}]}
    endpoint = f"/api/v1/orders/{order_id}/batches/"
    first = client.post(endpoint, payload, format="json")
    assert first.status_code == 201
    data = first.json()
    assert data["status"] == "pending" and data["sequence"] == 1
    assert data["total"] == "400.10"
    assert data["lines"][0]["unit_price"] == "200.05"
    assert not approved_lines().exists()
    reviewer = session_client(cashier)
    approval = reviewer.post(f"/api/v1/orders/batches/{data['id']}/approve/", {}, format="json")
    assert approval.status_code == 200
    assert approved_lines().count() == 1
    item.price, item.name, item.is_available = Decimal("250.25"), "New momo", False
    item.save()
    retry = client.post(endpoint, payload, format="json")
    assert retry.status_code == 200 and retry.json()["id"] == data["id"]
    assert retry.json()["status"] == "approved"
    assert retry.json()["lines"] == data["lines"]
    item.is_available = True
    item.save()
    payload["idempotency_key"] = str(uuid4())
    second = client.post(endpoint, payload, format="json")
    assert second.status_code == 201 and second.json()["sequence"] == 2
    assert second.json()["status"] == "pending" and second.json()["total"] == "500.50"
    history = client.get(f"/api/v1/orders/{order_id}/").json()
    assert history["batches"][0]["status"] == "approved"
    assert history["batches"][0]["lines"][0]["item_name"] == "Momo"
    assert history["totals"] == {"pending": "500.50", "approved": "400.10", "rejected": "0.00"}
    assert [event["kind"] for event in history["events"]] == [
        "session_opened",
        "order_created",
        "batch_submitted",
        "batch_approved",
        "batch_submitted",
    ]
    assert "no-store" in approval["Cache-Control"]
    assert "pin_hash" not in str(history) and "request_fingerprint" not in str(history)


@pytest.mark.parametrize("role", ["owner", "manager", "cashier", "waiter", "chef", ""])
def test_order_role_matrix(domain, session_client, role):
    order = opened(domain)
    batch = submitted(domain, order)
    user = User.objects.create_user(username="role-orders", role=role, is_superuser=True)
    client = session_client(user)
    assert client.get("/api/v1/orders/").status_code == (
        200 if role in {"owner", "manager", "cashier", "waiter"} else 403
    )
    assert client.get(f"/api/v1/orders/{order.pk}/").status_code == (
        200 if role in {"owner", "manager", "cashier", "waiter"} else 403
    )
    assert client.post(
        f"/api/v1/orders/tables/{domain[3].pk}/open/", {}, format="json"
    ).status_code == (200 if role == "waiter" else 403)
    response = client.post(
        f"/api/v1/orders/{order.pk}/batches/",
        {"idempotency_key": str(uuid4()), "lines": [{"menu_item": domain[2].pk, "quantity": 1}]},
        format="json",
    )
    assert response.status_code == (201 if role == "waiter" else 403)
    response = client.post(f"/api/v1/orders/batches/{batch.pk}/approve/", {}, format="json")
    assert response.status_code == (200 if role == "cashier" else 403)


@pytest.mark.parametrize("identity", ["anonymous", "inactive", "temporary"])
def test_order_session_protections(domain, session_client, identity):
    waiter = domain[4]
    if identity == "inactive":
        waiter.is_active = False
    if identity == "temporary":
        waiter.must_change_pin = True
    waiter.save()
    client = session_client(None if identity == "anonymous" else waiter)
    for path in (
        "/api/v1/orders/",
        "/api/v1/orders/batches/",
        f"/api/v1/orders/tables/{domain[3].pk}/active/",
    ):
        assert client.get(path).status_code == 403
    assert (
        client.post(f"/api/v1/orders/tables/{domain[3].pk}/open/", {}, format="json").status_code
        == 403
    )


def test_all_order_writes_require_csrf(domain, session_client):
    order = opened(domain)
    batch = submitted(domain, order)
    from rest_framework.test import APIClient

    for actor, path, payload in [
        (domain[4], f"tables/{domain[3].pk}/open/", {}),
        (domain[4], f"{order.pk}/batches/", {"idempotency_key": str(uuid4()), "lines": []}),
        (domain[5], f"batches/{batch.pk}/approve/", {}),
        (domain[5], f"batches/{batch.pk}/reject/", {"reason": "Unavailable"}),
    ]:
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(actor)
        assert client.post("/api/v1/orders/" + path, payload, format="json").status_code == 403


@pytest.mark.parametrize("quantity", [0, -1, 1.5, "2", True, None, 100, 10**30])
def test_invalid_quantities_are_atomic(domain, quantity):
    order = opened(domain)
    with pytest.raises(ValidationError):
        submit_batch(
            order_id=order.pk,
            actor=domain[4],
            idempotency_key=uuid4(),
            lines=[{"menu_item": domain[2].pk, "quantity": quantity}],
        )
    assert not OrderBatch.objects.exists()
    assert OrderEvent.objects.count() == 2


@pytest.mark.parametrize(
    "lines",
    [
        [],
        None,
        {},
        [None],
        [{"menu_item": 1}],
        [{"menu_item": 1, "quantity": 1, "price": "0.01"}],
        [{"menu_item": 1, "quantity": 1}] * 51,
        [{"menu_item": 1, "quantity": 1}] * 2,
    ],
)
def test_invalid_line_payloads(domain, lines):
    with pytest.raises(ValidationError):
        submit_batch(
            order_id=opened(domain).pk, actor=domain[4], idempotency_key=uuid4(), lines=lines
        )


@pytest.mark.parametrize(
    "unavailable", ["item", "archived_item", "category", "restaurant", "missing"]
)
def test_unavailable_menu_rejected(domain, unavailable):
    restaurant, category, item, table, waiter, cashier = domain
    order = opened(domain)
    target, field = {
        "item": (item, "is_available"),
        "archived_item": (item, "is_active"),
        "category": (category, "is_active"),
        "restaurant": (restaurant, "is_active"),
        "missing": (item, "is_available"),
    }[unavailable]
    setattr(target, field, False)
    target.save()
    with pytest.raises(ValidationError):
        submit_batch(
            order_id=order.pk,
            actor=waiter,
            idempotency_key=uuid4(),
            lines=[{"menu_item": 999999 if unavailable == "missing" else item.pk, "quantity": 1}],
        )
    assert not OrderBatch.objects.exists()


def test_idempotency_conflict_and_scope(domain):
    order = opened(domain)
    key = uuid4()
    batch = submitted(domain, order, key)
    assert submitted(domain, order, key).pk == batch.pk
    with pytest.raises(OrderConflict):
        submitted(domain, order, key, quantity=3)
    other = User.objects.create_user(username="another-waiter", role="waiter")
    different, created = submit_batch(
        order_id=order.pk,
        actor=other,
        idempotency_key=key,
        lines=[{"menu_item": domain[2].pk, "quantity": 2}],
    )
    assert created and different.pk != batch.pk and different.sequence == 2


def test_rejection_and_terminal_review_conflicts(domain, session_client):
    batch = submitted(domain)
    client = session_client(domain[5])
    path = f"/api/v1/orders/batches/{batch.pk}/"
    for body in ({}, {"reason": "   "}, {"reason": "x" * 501}, {"reason": "No", "price": "1"}):
        assert client.post(path + "reject/", body, format="json").status_code == 400
    assert client.post(path + "approve/", {"quantity": 9}, format="json").status_code == 400
    assert (
        client.post(path + "reject/", {"reason": "  Sold out  "}, format="json").status_code == 200
    )
    assert client.post(path + "approve/", {}, format="json").status_code == 409
    assert client.post(path + "reject/", {"reason": "Again"}, format="json").status_code == 409
    batch.refresh_from_db()
    assert batch.status == "rejected" and batch.rejection_reason == "Sold out"
    assert batch.reviewed_by == domain[5] and batch.reviewed_at
    assert batch.events.count() == 2
    assert not approved_lines().exists()
    domain[3].refresh_from_db()
    assert domain[3].status == "occupied"


def test_session_table_guards_and_legacy_occupancy(domain, owner_client):
    table = domain[3]
    table.status = "occupied"
    table.save()
    with pytest.raises(OrderConflict):
        opened(domain)
    table.status = "available"
    table.save()
    opened(domain)
    endpoint = f"/api/v1/tables/{table.pk}/"
    for body in (
        {"status": "available"},
        {"is_active": False},
        {"status": "available", "is_active": False},
    ):
        assert owner_client.patch(endpoint, body, format="json").status_code == 400
    assert owner_client.patch(endpoint, {"capacity": 4}, format="json").status_code == 200
    assert owner_client.get(endpoint).json()["has_active_session"] is True


@pytest.mark.parametrize("mode", ["inactive", "restaurant", "invalid"])
def test_invalid_open_table(domain, mode):
    if mode == "invalid":
        from django.http import Http404

        with pytest.raises(Http404):
            open_session(table_id=999999, actor=domain[4])
    else:
        target = domain[3] if mode == "inactive" else domain[0]
        target.is_active = False
        target.save()
        with pytest.raises(ValidationError):
            opened(domain)
    assert not DiningSession.objects.exists()


def test_no_mutable_line_event_or_admin_paths(domain, session_client, owner):
    batch = submitted(domain)
    line = batch.lines.get()
    with pytest.raises(ModelValidationError):
        line.save()
    with pytest.raises(ModelValidationError):
        OrderLine.objects.filter(pk=line.pk).update(quantity=9)
    with pytest.raises(ModelValidationError):
        line.delete()
    with pytest.raises(ModelValidationError):
        OrderEvent.objects.all().delete()
    from django.test import RequestFactory

    request = RequestFactory().get("/admin/")
    request.user = owner
    for model in (DiningSession, Order, OrderBatch, OrderLine, OrderEvent):
        operator = admin.site._registry[model]
        assert operator.has_view_permission(request)
        assert not operator.has_add_permission(request)
        assert not operator.has_change_permission(request)
        assert not operator.has_delete_permission(request)
    client = session_client(domain[5])
    for method in (client.patch, client.put, client.delete):
        assert method(f"/api/v1/orders/batches/{batch.pk}/", {}, format="json").status_code == 405


@pytest.mark.parametrize(
    "bad",
    [
        {"quantity": 0},
        {"quantity": 100},
        {"unit_price": "0"},
        {"unit_price": "-1"},
        {"line_total": "1"},
        {"item_name": " "},
    ],
)
def test_line_database_constraints(domain, bad):
    order = opened(domain)
    batch = OrderBatch.objects.create(
        order=order,
        sequence=1,
        submitted_by=domain[4],
        idempotency_key=uuid4(),
        request_fingerprint="a" * 64,
    )
    values = dict(
        batch=batch,
        menu_item=domain[2],
        item_name="Momo",
        unit_price="200.05",
        quantity=2,
        line_total="400.10",
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        OrderLine.objects.create(**(values | bad))


def test_session_and_review_database_constraints(domain):
    order = opened(domain)
    with pytest.raises(IntegrityError), transaction.atomic():
        DiningSession.objects.create(table=domain[3], opened_by=domain[4])
    batch = submitted(domain, order)
    with pytest.raises(IntegrityError), transaction.atomic():
        OrderBatch.objects.filter(pk=batch.pk).update(status="approved")


def test_pagination_detail_and_read_permissions(domain, session_client):
    batch = submitted(domain)
    client = session_client(domain[5])
    queue = client.get("/api/v1/orders/batches/").json()
    assert queue["count"] == 1 and queue["results"][0]["id"] == str(batch.pk)
    assert client.get(f"/api/v1/orders/batches/{batch.pk}/").status_code == 200
    assert client.get("/api/v1/orders/batches/?status=unknown").status_code == 400
    assert client.get("/api/v1/orders/batches/?page=99").status_code == 404
    assert client.get("/api/v1/orders/batches/?status=approved").json()["count"] == 0


def concurrent(operations):
    barrier = Barrier(len(operations))

    def worker(operation):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            try:
                return operation()
            except OrderConflict:
                return "conflict"
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=len(operations)) as pool:
        return list(pool.map(worker, operations))


@pytest.mark.django_db(transaction=True)
def test_concurrent_open_uses_one_session(domain):
    results = concurrent(
        [lambda: open_session(table_id=domain[3].pk, actor=domain[4]) for _ in range(2)]
    )
    assert sum(created for order, created in results) == 1
    assert len({order.pk for order, created in results}) == 1
    assert DiningSession.objects.count() == Order.objects.count() == 1
    assert OrderEvent.objects.count() == 2


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("conflicting", [False, True])
def test_concurrent_submission_idempotency(domain, conflicting):
    order = opened(domain)
    key = uuid4()
    results = concurrent(
        [
            lambda: submitted(domain, order, key, 2),
            lambda: submitted(domain, order, key, 3 if conflicting else 2),
        ]
    )
    assert OrderBatch.objects.count() == 1
    assert OrderEvent.objects.filter(kind="batch_submitted").count() == 1
    if conflicting:
        assert results.count("conflict") == 1
    else:
        assert results[0].pk == results[1].pk


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("second", ["approved", "rejected"])
def test_concurrent_cashier_decisions(domain, second):
    batch = submitted(domain)
    other = User.objects.create_user(username="second-cashier", role="cashier")
    results = concurrent(
        [
            lambda: review_batch(batch_id=batch.pk, actor=domain[5], decision="approved"),
            lambda: review_batch(
                batch_id=batch.pk,
                actor=other,
                decision=second,
                reason="Sold out" if second == "rejected" else "",
            ),
        ]
    )
    assert results.count("conflict") == 1
    batch.refresh_from_db()
    assert batch.status in {"approved", "rejected"}
    assert batch.events.filter(kind__in=["batch_approved", "batch_rejected"]).count() == 1


def test_services_check_roles_without_http(domain):
    with pytest.raises(PermissionDenied):
        open_session(table_id=domain[3].pk, actor=domain[5])
    batch = submitted(domain)
    with pytest.raises(PermissionDenied):
        review_batch(batch_id=batch.pk, actor=domain[4], decision="approved")


@pytest.mark.parametrize("operation", ["open", "submit", "review"])
def test_business_event_failure_rolls_back_entire_operation(domain, monkeypatch, operation):
    order = opened(domain) if operation != "open" else None
    batch = submitted(domain, order) if operation == "review" else None
    event_count = OrderEvent.objects.count()

    def fail(*args, **kwargs):
        raise RuntimeError("Simulated audit storage failure")

    monkeypatch.setattr("apps.orders.services._event", fail)
    with pytest.raises(RuntimeError):
        if operation == "open":
            opened(domain)
        elif operation == "submit":
            submitted(domain, order)
        else:
            review_batch(batch_id=batch.pk, actor=domain[5], decision="approved")
    assert OrderEvent.objects.count() == event_count
    if operation == "open":
        assert not DiningSession.objects.exists() and not Order.objects.exists()
        domain[3].refresh_from_db()
        assert domain[3].status == "available"
    elif operation == "submit":
        assert not OrderBatch.objects.exists() and not OrderLine.objects.exists()
    else:
        batch.refresh_from_db()
        assert batch.status == "pending" and batch.reviewed_by is None


def test_canonical_payload_retry_and_missing_key(domain, session_client):
    order = opened(domain)
    other = MenuItem.objects.create(category=domain[1], name="Tea", price="60.50")
    lines = [{"menu_item": domain[2].pk, "quantity": 1}, {"menu_item": other.pk, "quantity": 3}]
    key = uuid4()
    first, created = submit_batch(
        order_id=order.pk, actor=domain[4], idempotency_key=key, lines=lines
    )
    retry, created = submit_batch(
        order_id=order.pk, actor=domain[4], idempotency_key=key, lines=lines[::-1]
    )
    assert retry.pk == first.pk and not created
    client = session_client(domain[4])
    for payload in (
        {"lines": lines},
        {"lines": lines, "idempotency_key": "invalid"},
        {"lines": lines, "idempotency_key": str(uuid4()), "unit_price": "1"},
    ):
        assert (
            client.post(f"/api/v1/orders/{order.pk}/batches/", payload, format="json").status_code
            == 400
        )


@pytest.mark.django_db(transaction=True)
def test_concurrent_distinct_submissions_get_unique_sequences(domain):
    order = opened(domain)
    results = concurrent([lambda: submitted(domain, order), lambda: submitted(domain, order)])
    assert {batch.sequence for batch in results} == {1, 2}
    assert OrderBatch.objects.count() == 2


@pytest.mark.django_db(transaction=True)
def test_orders_migration_preserves_existing_domain_records(domain):
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor

    executor = MigrationExecutor(connection)
    latest = executor.loader.graph.leaf_nodes()
    identity = (domain[4].pk, domain[4].username, domain[4].pin_hash)
    existing = (domain[0].pk, domain[1].pk, domain[2].pk, domain[3].pk)
    try:
        executor.migrate([("orders", None)])
        MigrationExecutor(connection).migrate(latest)
        waiter = User.objects.get(pk=identity[0])
        assert (waiter.pk, waiter.username, waiter.pin_hash) == identity
        assert (
            Restaurant.objects.get().pk,
            Category.objects.get().pk,
            MenuItem.objects.get().pk,
            DiningTable.objects.get().pk,
        ) == existing
        assert MenuItem.objects.get().price == Decimal("200.05")
        assert DiningTable.objects.get().status == "available"
    finally:
        MigrationExecutor(connection).migrate(latest)
