from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
from django.db import close_old_connections, connections

from apps.accounts.models import LoginRateLimit, User
from apps.accounts.rate_limits import LoginRateLimited, consume_credential_attempt
from apps.accounts.validators import validate_pin

pytestmark = pytest.mark.django_db
PREFIX = "/api/v1/accounts/"
LEGACY_PIN = "482759"  # Synthetic historical credential, never a preview account PIN.


@pytest.fixture
def legacy_staff(staff):
    staff.pin_hash = make_password(User._peppered_pin(LEGACY_PIN))
    staff.save(update_fields=["pin_hash"])
    return staff


def test_new_pin_setter_rejects_six_digits_without_modifying_hash(staff):
    original = staff.pin_hash
    with pytest.raises(ValidationError):
        staff.set_pin(LEGACY_PIN)
    assert staff.pin_hash == original
    staff.refresh_from_db()
    assert staff.pin_hash == original


@pytest.mark.parametrize("pin", ["0427", "4827", "7392"])
def test_four_digit_pin_preserves_strings_and_leading_zero(staff, pin, session_client):
    validate_pin(pin)
    staff.set_pin(pin)
    staff.save(update_fields=["pin_hash"])
    assert staff.check_pin(pin)
    client = session_client()
    response = client.post(
        PREFIX + "login/staff/", {"username": staff.username, "pin": pin}, format="json"
    )
    assert response.status_code == 200 and response.json()["user"]["id"] == staff.pk
    if pin.startswith("0"):
        assert not staff.check_pin(pin[1:])


def test_legacy_login_keeps_hash_sessions_and_original_length(legacy_staff, session_client):
    user = legacy_staff
    original = (user.pin_hash, user.auth_version, user.must_change_pin, user.pk)
    existing = session_client(user)
    client = session_client()
    short = client.post(
        PREFIX + "login/staff/", {"username": user.username, "pin": LEGACY_PIN[:4]}, format="json"
    )
    assert short.status_code == 401
    response = client.post(
        PREFIX + "login/staff/", {"username": user.username, "pin": LEGACY_PIN}, format="json"
    )
    assert response.status_code == 200
    user.refresh_from_db()
    assert (user.pin_hash, user.auth_version, user.must_change_pin, user.pk) == original
    assert existing.get(PREFIX + "me/").status_code == 200


@pytest.mark.parametrize("temporary", [False, True])
def test_legacy_self_transition_retains_current_session_and_revokes_others(
    legacy_staff, session_client, temporary
):
    user = legacy_staff
    user.must_change_pin = temporary
    user.save(update_fields=["must_change_pin"])
    client = session_client(user)
    other = session_client(user)
    version = user.auth_version
    response = client.post(
        PREFIX + "pin/change/", {"current_pin": LEGACY_PIN, "new_pin": "0427"}, format="json"
    )
    assert response.status_code == 200 and not response.json()["must_change_pin"]
    assert client.get(PREFIX + "me/").status_code == 200
    assert other.get(PREFIX + "me/").status_code == 403
    user.refresh_from_db()
    assert user.auth_version == version + 1
    assert user.check_pin("0427") and not user.check_pin(LEGACY_PIN)


def test_owner_can_reset_legacy_to_four_digit_temporary_pin(
    legacy_staff, owner_client, owner_password, session_client
):
    user = legacy_staff
    other = session_client(user)
    result = owner_client.post(
        PREFIX + f"staff/{user.pk}/pin/reset/",
        {
            "new_pin": "0427",
            "owner_password": owner_password,
        },
        format="json",
    )
    assert result.status_code == 200 and result.json()["must_change_pin"]
    assert other.get(PREFIX + "me/").status_code == 403
    user.refresh_from_db()
    assert user.check_pin("0427") and not user.check_pin(LEGACY_PIN)


@pytest.mark.parametrize("pin", ["482759", "0000", "1111", "1234", "4321", 427])
def test_reset_and_change_reject_invalid_new_pin_atomically(
    staff, owner_client, owner_password, session_client, pin
):
    original = (staff.pin_hash, staff.auth_version, staff.must_change_pin)
    response = owner_client.post(
        PREFIX + f"staff/{staff.pk}/pin/reset/",
        {
            "new_pin": pin,
            "owner_password": owner_password,
        },
        format="json",
    )
    assert response.status_code == 400
    client = session_client(staff)
    assert (
        client.post(
            PREFIX + "pin/change/", {"current_pin": "4827", "new_pin": pin}, format="json"
        ).status_code
        == 400
    )
    staff.refresh_from_db()
    assert (staff.pin_hash, staff.auth_version, staff.must_change_pin) == original


def test_pin_and_password_budgets_share_identity_without_weakening_caps():
    assert settings.ACCOUNTS_PIN_ACCOUNT_LIMIT == 3
    assert settings.ACCOUNTS_LOGIN_ACCOUNT_LIMIT == 5
    for _ in range(3):
        consume_credential_attempt("shared-pin", "192.0.2.1", pin=True)
    with pytest.raises(LoginRateLimited):
        consume_credential_attempt("shared-pin", "192.0.2.2", pin=True)
    # Password checking keeps its five-attempt cap; it never verifies staff PINs.
    consume_credential_attempt("shared-pin", "192.0.2.2")
    consume_credential_attempt("shared-pin", "192.0.2.3")
    with pytest.raises(LoginRateLimited):
        consume_credential_attempt("shared-pin", "192.0.2.4")
    with pytest.raises(LoginRateLimited):
        consume_credential_attempt("shared-pin", "192.0.2.5", pin=True)


@pytest.mark.django_db(transaction=True)
def test_concurrent_pin_attempts_cannot_exceed_stricter_cap():
    barrier = Barrier(6)

    def attempt(index):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            try:
                consume_credential_attempt("pin-race", f"192.0.2.{index}", pin=True)
                return "admitted"
            except LoginRateLimited:
                return "limited"
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=6) as pool:
        outcomes = list(pool.map(attempt, range(6)))
    assert outcomes.count("admitted") == outcomes.count("limited") == 3
    assert all(len(row.key) == 64 for row in LoginRateLimit.objects.all())
