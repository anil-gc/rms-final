import io
from unittest.mock import patch

import pytest
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.hashers import identify_hasher
from django.contrib.sessions.models import Session
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, transaction
from django.test import RequestFactory, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import STAFF_ROLES, User

pytestmark = pytest.mark.django_db
PREFIX = "/api/v1/accounts/"


def post(client, path, payload, **extra):
    response = client.post(PREFIX + path, payload, format="json", **extra)
    if response.status_code == 200 and "csrf_token" in response.json():
        client.credentials(HTTP_X_CSRFTOKEN=response.json()["csrf_token"])
    return response


def test_owner_password_login_rotates_session_and_csrf(owner, owner_password, session_client):
    client = session_client()
    client.session["prelogin"] = "value"
    session = client.session
    session["prelogin"] = "value"
    session.save()
    original_session = session.session_key
    original_csrf = client.cookies[settings.CSRF_COOKIE_NAME].value
    response = post(
        client, "login/owner/", {"username": owner.username, "password": owner_password}
    )
    assert response.status_code == 200
    assert response.json()["user"]["role"] == "owner"
    assert client.session.session_key != original_session
    assert client.cookies[settings.CSRF_COOKIE_NAME].value != original_csrf
    assert client.session.get_expiry_age() <= settings.ACCOUNTS_OWNER_SESSION_SECONDS
    assert "no-store" in response["Cache-Control"]
    assert client.cookies[settings.SESSION_COOKIE_NAME]["httponly"]
    assert client.cookies[settings.SESSION_COOKIE_NAME]["samesite"] == "Lax"
    assert client.get(PREFIX + "me/").status_code == 200


def test_staff_pin_login_and_logout_revoke_session(staff, session_client):
    client = session_client()
    response = post(client, "login/staff/", {"username": staff.username, "pin": "4827"})
    assert response.status_code == 200
    assert client.session.get_expiry_age() <= settings.ACCOUNTS_STAFF_SESSION_SECONDS
    key = client.session.session_key
    assert Session.objects.filter(session_key=key).exists()
    assert post(client, "logout/", {}).status_code == 204
    assert not Session.objects.filter(session_key=key).exists()
    assert client.get(PREFIX + "me/").status_code == 403
    replay = APIClient()
    replay.cookies[settings.SESSION_COOKIE_NAME] = key
    assert replay.get(PREFIX + "me/").status_code == 403


@pytest.mark.parametrize("endpoint", ["login/staff/", "login/owner/"])
def test_login_requires_csrf_even_for_anonymous_clients(endpoint):
    client = APIClient(enforce_csrf_checks=True)
    response = post(client, endpoint, {"username": "unknown", "password": "unknown"})
    assert response.status_code == 403
    assert response.json() == {"detail": "CSRF validation failed."}


def test_mutations_reject_missing_or_untrusted_csrf_origin(owner, owner_password, session_client):
    client = session_client(owner)
    payload = {
        "username": "new",
        "role": "waiter",
        "pin": "7392",
        "owner_password": owner_password,
    }
    assert (
        post(client, "staff/", payload, HTTP_ORIGIN="https://untrusted.example.test").status_code
        == 403
    )
    client.credentials()
    assert post(client, "staff/", payload).status_code == 403
    assert not User.objects.filter(username="new").exists()


@pytest.mark.parametrize("role", STAFF_ROLES)
def test_owner_creates_staff_with_hashed_temporary_pin(owner_client, owner_password, role):
    response = post(
        owner_client,
        "staff/",
        {
            "username": f"new-{role}",
            "role": role,
            "pin": "0427",
            "owner_password": owner_password,
        },
    )
    assert response.status_code == 201
    data = response.json()
    user = User.objects.get(pk=data["id"])
    assert user.role == role
    assert user.must_change_pin
    assert user.check_pin("0427")
    assert user.pin_hash != "0427"
    assert identify_hasher(user.pin_hash).algorithm == "argon2"
    assert not user.has_usable_password()
    assert not user.is_staff and not user.is_superuser
    assert set(data) == {
        "id",
        "username",
        "first_name",
        "last_name",
        "role",
        "is_active",
        "must_change_pin",
    }
    assert "0427" not in response.content.decode()


@pytest.mark.parametrize(
    "extra",
    [
        {"role": "owner"},
        {"is_staff": True},
        {"is_superuser": True},
        {"password": "injected"},
        {"restaurant_id": 1},
        {"auth_version": 1},
    ],
)
def test_staff_creation_rejects_role_and_privilege_injection(owner_client, owner_password, extra):
    payload = {
        "username": "injection",
        "role": "waiter",
        "pin": "7392",
        "owner_password": owner_password,
        **extra,
    }
    assert post(owner_client, "staff/", payload).status_code == 400
    assert not User.objects.filter(username="injection").exists()


@pytest.mark.parametrize(
    "pin",
    [
        "123456",
        "111111",
        "654321",
        "12345",
        "1234567",
        "१२३४५६",
        4827,
        " 4827",
        "0000",
        "1111",
        "1234",
        "4321",
        "0123",
        "9876",
        "7890",
        "2109",
        "१२३४",
        "427",
        "04270",
        "0427 ",
        "04a7",
        "04.7",
        False,
        None,
    ],
)
def test_staff_creation_rejects_invalid_or_weak_pins(owner_client, owner_password, pin):
    response = post(
        owner_client,
        "staff/",
        {
            "username": "invalid-pin",
            "role": "waiter",
            "pin": pin,
            "owner_password": owner_password,
        },
    )
    assert response.status_code == 400
    assert not User.objects.filter(username="invalid-pin").exists()


def test_owner_must_reauthenticate_for_staff_writes(owner_client, staff):
    response = post(
        owner_client,
        f"staff/{staff.pk}/pin/reset/",
        {
            "new_pin": "7392",
            "owner_password": "incorrect",
        },
    )
    assert response.status_code == 401
    staff.refresh_from_db()
    assert staff.check_pin("4827")


@pytest.mark.parametrize("role", STAFF_ROLES)
def test_non_owners_cannot_list_create_reset_or_disable_staff(staff, session_client, role):
    staff.role = role
    staff.save(update_fields=["role"])
    client = session_client(staff)
    assert client.get(PREFIX + "staff/").status_code == 403
    assert post(client, "staff/", {}).status_code == 403
    assert post(client, f"staff/{staff.pk}/pin/reset/", {}).status_code == 403
    assert client.patch(PREFIX + f"staff/{staff.pk}/", {}, format="json").status_code == 403
    assert post(client, "password/change/", {}).status_code == 403


def test_unknown_and_inactive_accounts_have_generic_login_failure(staff, session_client):
    client = session_client()
    staff.is_active = False
    staff.save(update_fields=["is_active"])
    for username in [staff.username, "does-not-exist"]:
        response = post(client, "login/staff/", {"username": username, "pin": "4827"})
        assert response.status_code == 401
        assert response.json() == {"detail": "Invalid credentials."}


def test_owner_pin_and_staff_password_login_are_not_allowed(
    owner, owner_password, staff, session_client
):
    owner.set_pin("4827")
    owner.save(update_fields=["pin_hash"])
    client = session_client()
    assert (
        post(client, "login/staff/", {"username": owner.username, "pin": "4827"}).status_code == 401
    )
    assert (
        post(
            client, "login/owner/", {"username": staff.username, "password": owner_password}
        ).status_code
        == 401
    )


def test_temporary_pin_must_change_and_change_revokes_other_sessions(staff, session_client):
    staff.must_change_pin = True
    staff.save(update_fields=["must_change_pin"])
    current = session_client(staff)
    other = session_client(staff)
    assert current.get(PREFIX + "me/").json()["must_change_pin"] is True
    response = post(current, "pin/change/", {"current_pin": "4827", "new_pin": "7392"})
    assert response.status_code == 200
    assert response.json()["must_change_pin"] is False
    assert current.get(PREFIX + "me/").status_code == 200
    assert other.get(PREFIX + "me/").status_code == 403
    staff.refresh_from_db()
    assert staff.check_pin("7392") and not staff.check_pin("4827")


@pytest.mark.parametrize(
    "current,new,status",
    [
        ("wrong", "7392", 401),
        ("4827", "4827", 400),
        ("4827", "111111", 400),
    ],
)
def test_pin_change_rejects_invalid_credentials_and_reuse(
    staff, session_client, current, new, status
):
    client = session_client(staff)
    assert (
        post(client, "pin/change/", {"current_pin": current, "new_pin": new}).status_code == status
    )
    staff.refresh_from_db()
    assert staff.check_pin("4827")


def test_owner_reset_revokes_sessions_and_requires_new_pin_change(
    owner_client, owner_password, staff, session_client
):
    existing = session_client(staff)
    response = post(
        owner_client,
        f"staff/{staff.pk}/pin/reset/",
        {
            "new_pin": "7392",
            "owner_password": owner_password,
        },
    )
    assert response.status_code == 200
    assert existing.get(PREFIX + "me/").status_code == 403
    client = session_client()
    assert (
        post(client, "login/staff/", {"username": staff.username, "pin": "4827"}).status_code == 401
    )
    result = post(client, "login/staff/", {"username": staff.username, "pin": "7392"})
    assert result.status_code == 200 and result.json()["user"]["must_change_pin"] is True


def test_deactivation_then_reactivation_does_not_restore_old_session(
    owner_client, owner_password, staff, session_client
):
    old = session_client(staff)
    for active in [False, True]:
        result = owner_client.patch(
            PREFIX + f"staff/{staff.pk}/",
            {
                "is_active": active,
                "owner_password": owner_password,
            },
            format="json",
        )
        assert result.status_code == 200
    assert old.get(PREFIX + "me/").status_code == 403


def test_owner_cannot_be_targeted_by_staff_management(owner_client, owner, owner_password):
    response = post(
        owner_client,
        f"staff/{owner.pk}/pin/reset/",
        {
            "new_pin": "7392",
            "owner_password": owner_password,
        },
    )
    assert response.status_code == 404
    assert post(owner_client, "pin/change/", {}).status_code == 403


def test_owner_password_change_enforces_policy_and_revokes_other_sessions(
    owner_client, owner, owner_password, session_client
):
    other = session_client(owner)
    assert (
        post(
            owner_client,
            "password/change/",
            {
                "current_password": owner_password,
                "new_password": "short",
            },
        ).status_code
        == 400
    )
    assert (
        post(
            owner_client,
            "password/change/",
            {
                "current_password": "incorrect",
                "new_password": "new-owner-password-example!",
            },
        ).status_code
        == 401
    )
    response = post(
        owner_client,
        "password/change/",
        {
            "current_password": owner_password,
            "new_password": "new-owner-password-example!",
        },
    )
    assert response.status_code == 200
    assert owner_client.get(PREFIX + "me/").status_code == 200
    assert other.get(PREFIX + "me/").status_code == 403


def test_server_enforces_session_expiry(staff, session_client):
    client = session_client(staff)
    Session.objects.filter(session_key=client.session.session_key).update(
        expire_date=timezone.now()
    )
    assert client.get(PREFIX + "me/").status_code == 403


def test_unassigned_superuser_gets_no_implicit_business_role(session_client):
    user = User.objects.create_superuser(
        username="recovery-admin", password="recovery-only-example-password"
    )
    client = session_client(user)
    assert client.get(PREFIX + "me/").status_code == 403
    assert client.get(PREFIX + "staff/").status_code == 403
    assert post(client, "staff/", {}).status_code == 403


def test_pin_hashes_are_salted_and_pepper_dependent(staff):
    other = User(username="other")
    other.set_pin("4827")
    assert staff.pin_hash != other.pin_hash
    with override_settings(PIN_PEPPER="different-test-only-pepper-value"):
        assert not staff.check_pin("4827")


def test_only_one_owner_is_allowed_by_database(owner, owner_password):
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.create_user(username="second-owner", role="owner", password=owner_password)


def test_database_rejects_unknown_roles():
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.create_user(username="invalid-role", role="admin")


@override_settings(SESSION_COOKIE_SECURE=True, CSRF_COOKIE_SECURE=True)
def test_secure_session_cookie_flags(owner, owner_password, session_client):
    client = session_client()
    response = post(
        client,
        "login/owner/",
        {
            "username": owner.username,
            "password": owner_password,
        },
    )
    assert response.status_code == 200
    for cookie_name in [settings.SESSION_COOKIE_NAME, settings.CSRF_COOKIE_NAME]:
        assert client.cookies[cookie_name]["secure"]
        assert client.cookies[cookie_name]["httponly"]


def test_duplicate_staff_username_preserves_existing_account(owner_client, owner_password, staff):
    response = post(
        owner_client,
        "staff/",
        {
            "username": staff.username,
            "role": "chef",
            "pin": "7392",
            "owner_password": owner_password,
        },
    )
    assert response.status_code == 400
    staff.refresh_from_db()
    assert staff.role == "waiter" and staff.check_pin("4827")


def test_account_admin_is_read_only_and_hides_hashes(owner):
    model_admin = admin.site._registry[User]
    request = RequestFactory().get("/")
    request.user = owner
    assert model_admin.has_view_permission(request)
    assert model_admin.has_module_permission(request)
    assert not model_admin.has_add_permission(request)
    assert not model_admin.has_change_permission(request, owner)
    assert not model_admin.has_delete_permission(request, owner)
    assert "password" not in model_admin.fields and "pin_hash" not in model_admin.fields


def test_bootstrap_owner_creates_validated_owner_without_printing_password(owner_password):
    output = io.StringIO()
    with patch(
        "apps.accounts.management.commands.bootstrap_owner.getpass",
        side_effect=[owner_password] * 2,
    ):
        call_command("bootstrap_owner", username="initial-owner", stdout=output)
    user = User.objects.get(username="initial-owner")
    assert user.role == "owner" and user.is_staff and not user.is_superuser
    assert user.check_password(owner_password)
    assert owner_password not in output.getvalue()
    with pytest.raises(CommandError):
        call_command("bootstrap_owner", username="another-owner")


@pytest.mark.parametrize(
    "passwords", [["short", "short"], ["first-long-password", "different-long-password"]]
)
def test_bootstrap_rejects_weak_and_mismatched_passwords(passwords):
    with patch("apps.accounts.management.commands.bootstrap_owner.getpass", side_effect=passwords):
        with pytest.raises(CommandError):
            call_command("bootstrap_owner", username="initial-owner")
    assert not User.objects.filter(role="owner").exists()
