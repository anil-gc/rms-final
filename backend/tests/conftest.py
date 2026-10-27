import secrets

import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def owner_password():
    return secrets.token_urlsafe(24)


@pytest.fixture
def owner(db, owner_password):
    from apps.accounts.models import User

    return User.objects.create_user(
        username="owner-test", password=owner_password, role=User.Role.OWNER, is_staff=True
    )


@pytest.fixture
def staff(db):
    from apps.accounts.models import User

    user = User.objects.create_user(username="waiter-test", role=User.Role.WAITER)
    user.set_pin("4827")
    user.save(update_fields=["pin_hash"])
    return user


@pytest.fixture
def session_client():
    """Exercise real Django session validation and CSRF, not force_authenticate."""

    def make_client(user=None):
        client = APIClient(enforce_csrf_checks=True)
        if user is not None:
            client.force_login(user)
        token = client.get("/api/v1/accounts/csrf/").json()["csrf_token"]
        client.credentials(HTTP_X_CSRFTOKEN=token)
        return client

    return make_client


@pytest.fixture
def owner_client(owner, session_client):
    return session_client(owner)
