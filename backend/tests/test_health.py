from unittest.mock import patch

import pytest
from django.db import OperationalError
from django.urls import resolve, reverse


def test_liveness_is_public_versioned_and_database_independent(api_client, django_db_blocker):
    with django_db_blocker.block():
        response = api_client.get(reverse("v1:health"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "v1"}
    assert response["Content-Type"] == "application/json"
    assert resolve("/api/v1/health/").namespace == "v1"


@pytest.mark.django_db
def test_readiness_checks_real_postgresql(api_client):
    response = api_client.get(reverse("v1:readiness"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "v1"}


def test_readiness_failure_returns_generic_503(api_client, caplog):
    private_detail = "connection failure containing private deployment details"
    with patch("apps.core.views.connection.cursor", side_effect=OperationalError(private_detail)):
        response = api_client.get(reverse("v1:readiness"))

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
    assert private_detail not in response.content.decode()
    assert private_detail not in caplog.text


@pytest.mark.parametrize("path", ["/api/health/", "/api/v2/health/", "/api/v1/orders/"])
def test_only_declared_v1_routes_exist(api_client, path):
    assert api_client.get(path).status_code == 404


def test_health_does_not_accept_writes(api_client):
    assert api_client.post(reverse("v1:health"), {}, format="json").status_code == 405


def test_health_supports_head(api_client):
    response = api_client.head(reverse("v1:health"))
    assert response.status_code == 200
    assert response.content == b""


def test_admin_login_route_exists(api_client):
    assert api_client.get(reverse("admin:login")).status_code == 200
