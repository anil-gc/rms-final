import pytest
from django.urls import reverse
from rest_framework.test import APIClient


@pytest.fixture
def client():
    return APIClient()


@pytest.mark.django_db
def test_kitchen_ticket_list(
    client, chef_user, waiter_user, setup_approved_order, setup_pending_order
):
    client.force_authenticate(user=chef_user)

    # Approved items should be returned (pending status implicitly)
    url = reverse("v1:kitchen-ticket-list")
    response = client.get(url + "?status=pending")
    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]["order_line_id"] == setup_approved_order.id

    # Waiter should also be able to read
    client.force_authenticate(user=waiter_user)
    response = client.get(url + "?status=pending")
    assert response.status_code == 200


@pytest.mark.django_db
def test_mark_preparing_api(client, chef_user, cashier_user, setup_approved_order):
    client.force_authenticate(user=cashier_user)
    url = reverse("v1:kitchen-mark-preparing", kwargs={"line_id": setup_approved_order.id})
    response = client.post(url)
    assert response.status_code == 403  # Cashier cannot mark preparing

    client.force_authenticate(user=chef_user)
    response = client.post(url)
    assert response.status_code == 200
    assert response.data["status"] == "preparing"


@pytest.mark.django_db
def test_cannot_prepare_pending_order(client, chef_user, setup_pending_order):
    client.force_authenticate(user=chef_user)
    url = reverse("v1:kitchen-mark-preparing", kwargs={"line_id": setup_pending_order.id})
    response = client.post(url)
    assert response.status_code == 400  # Validation error: Only approved items
