from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from unittest.mock import patch

import pytest
from django.conf import settings
from django.db import close_old_connections, connections
from django.test import override_settings
from django.utils import timezone

from apps.accounts.models import LoginRateLimit
from apps.accounts.rate_limits import (
    LoginRateLimited,
    consume_credential_attempt,
    refund_successful_account_attempt,
)

PREFIX = "/api/v1/accounts/"


@pytest.mark.django_db
def test_account_failed_login_budget_is_shared_across_client_ips(staff, session_client):
    client = session_client()
    for attempt in range(
        min(settings.ACCOUNTS_LOGIN_ACCOUNT_LIMIT, settings.ACCOUNTS_PIN_ACCOUNT_LIMIT)
    ):
        response = client.post(
            PREFIX + "login/staff/",
            {
                "username": staff.username,
                "pin": "incorrect",
            },
            format="json",
            REMOTE_ADDR=f"192.0.2.{attempt + 1}",
        )
        assert response.status_code == 401
    blocked = client.post(
        PREFIX + "login/staff/",
        {
            "username": staff.username,
            "pin": "4827",
        },
        format="json",
        REMOTE_ADDR="198.51.100.1",
    )
    assert blocked.status_code == 429
    assert 1 <= int(blocked["Retry-After"]) <= settings.ACCOUNTS_LOGIN_ACCOUNT_WINDOW_SECONDS
    assert not client.session.get("_auth_user_id")
    assert all(len(bucket.key) == 64 for bucket in LoginRateLimit.objects.all())
    assert not LoginRateLimit.objects.filter(key__contains=staff.username).exists()


@pytest.mark.django_db
@override_settings(ACCOUNTS_LOGIN_IP_LIMIT=2)
def test_ip_budget_ignores_spoofed_forwarded_headers(session_client):
    client = session_client()
    for index, expected in enumerate([401, 401, 429]):
        response = client.post(
            PREFIX + "login/staff/",
            {
                "username": f"unknown-{index}",
                "pin": "4827",
            },
            format="json",
            REMOTE_ADDR="192.0.2.50",
            HTTP_X_FORWARDED_FOR=f"198.51.100.{index}",
        )
        assert response.status_code == expected


@pytest.mark.django_db
@override_settings(ACCOUNTS_LOGIN_ACCOUNT_LIMIT=1, ACCOUNTS_LOGIN_IP_LIMIT=3)
def test_success_refunds_only_the_account_attempt(staff, session_client):
    for _ in range(3):
        client = session_client()
        assert (
            client.post(
                PREFIX + "login/staff/",
                {
                    "username": staff.username,
                    "pin": "4827",
                },
                format="json",
            ).status_code
            == 200
        )
    client = session_client()
    assert (
        client.post(
            PREFIX + "login/staff/",
            {
                "username": staff.username,
                "pin": "4827",
            },
            format="json",
        ).status_code
        == 429
    )


@pytest.mark.django_db
def test_expired_failure_window_allows_login_again(staff, session_client):
    for _ in range(min(settings.ACCOUNTS_LOGIN_ACCOUNT_LIMIT, settings.ACCOUNTS_PIN_ACCOUNT_LIMIT)):
        consume_credential_attempt(staff.username, "192.0.2.1")
    LoginRateLimit.objects.update(window_started=timezone.now() - timedelta(hours=1))
    client = session_client()
    assert (
        client.post(
            PREFIX + "login/staff/",
            {
                "username": staff.username,
                "pin": "4827",
            },
            format="json",
        ).status_code
        == 200
    )


@pytest.mark.django_db
def test_success_does_not_refund_an_attempt_in_a_new_window():
    old = consume_credential_attempt("window-test", "192.0.2.1")
    later = old[1] + timedelta(seconds=settings.ACCOUNTS_LOGIN_ACCOUNT_WINDOW_SECONDS + 1)
    with patch("apps.accounts.rate_limits.timezone.now", return_value=later):
        new = consume_credential_attempt("window-test", "192.0.2.1")
    refund_successful_account_attempt(old)
    assert LoginRateLimit.objects.get(pk=new[0]).attempts == 1


@pytest.mark.django_db
def test_pin_change_current_credential_is_rate_limited(staff, session_client):
    client = session_client(staff)
    for _ in range(min(settings.ACCOUNTS_LOGIN_ACCOUNT_LIMIT, settings.ACCOUNTS_PIN_ACCOUNT_LIMIT)):
        assert (
            client.post(
                PREFIX + "pin/change/",
                {
                    "current_pin": "incorrect",
                    "new_pin": "7392",
                },
                format="json",
            ).status_code
            == 401
        )
    assert (
        client.post(
            PREFIX + "pin/change/",
            {
                "current_pin": "4827",
                "new_pin": "7392",
            },
            format="json",
        ).status_code
        == 429
    )


@pytest.mark.django_db
@override_settings(ACCOUNTS_LOGIN_ACCOUNT_LIMIT=1)
def test_admin_and_api_password_login_share_failed_attempt_budget(
    owner, owner_password, session_client
):
    # The first invalid admin password consumes the same Owner identity budget.
    from django.test import Client

    admin_client = Client()
    response = admin_client.post(
        "/admin/login/", {"username": owner.username, "password": "incorrect"}
    )
    assert response.status_code == 200
    client = session_client()
    assert (
        client.post(
            PREFIX + "login/owner/",
            {
                "username": owner.username,
                "password": owner_password,
            },
            format="json",
        ).status_code
        == 429
    )


@pytest.mark.django_db(transaction=True)
@override_settings(ACCOUNTS_LOGIN_ACCOUNT_LIMIT=3)
def test_concurrent_workers_cannot_exceed_postgresql_account_budget():
    barrier = Barrier(6)

    def attempt(number):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            try:
                consume_credential_attempt("concurrent-account", f"192.0.2.{number}")
                return "admitted"
            except LoginRateLimited:
                return "limited"
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=6) as executor:
        outcomes = list(executor.map(attempt, range(6)))
    assert outcomes.count("admitted") == 3
    assert outcomes.count("limited") == 3


@pytest.mark.django_db
def test_old_rate_limit_buckets_can_be_purged():
    from django.core.management import call_command

    consume_credential_attempt("stale", "192.0.2.1")
    LoginRateLimit.objects.update(window_started=timezone.now() - timedelta(days=2))
    consume_credential_attempt("recent", "198.51.100.1")
    call_command("purge_login_limits")
    assert LoginRateLimit.objects.count() == 2


@pytest.mark.django_db
@override_settings(ACCOUNTS_LOGIN_ACCOUNT_LIMIT=1)
def test_admin_password_change_cannot_bypass_account_budget(owner, owner_password, session_client):
    client = session_client(owner)
    response = client.post(
        "/admin/password_change/",
        {
            "old_password": "incorrect",
            "new_password1": "new-test-only-owner-password!",
            "new_password2": "new-test-only-owner-password!",
        },
    )
    assert response.status_code == 200
    blocked = client.post(
        "/admin/password_change/",
        {
            "old_password": owner_password,
            "new_password1": "new-test-only-owner-password!",
            "new_password2": "new-test-only-owner-password!",
        },
    )
    assert blocked.status_code == 429 and "Retry-After" in blocked
    owner.refresh_from_db()
    assert owner.check_password(owner_password)


@pytest.mark.django_db
@override_settings(ACCOUNTS_LOGIN_ACCOUNT_LIMIT=1)
def test_successful_admin_password_change_refunds_account_budget(
    owner, owner_password, session_client
):
    client = session_client(owner)
    response = client.post(
        "/admin/password_change/",
        {
            "old_password": owner_password,
            "new_password1": "new-test-only-owner-password!",
            "new_password2": "new-test-only-owner-password!",
        },
    )
    assert response.status_code == 302
    owner.refresh_from_db()
    assert owner.check_password("new-test-only-owner-password!")
    assert sorted(LoginRateLimit.objects.values_list("attempts", flat=True)) == [0, 1]
