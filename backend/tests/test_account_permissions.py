from types import SimpleNamespace

import pytest
from django.contrib.auth.models import AnonymousUser

from apps.accounts.models import User
from apps.accounts.permissions import (
    IsAuthenticatedAndPinReady,
    IsCashier,
    IsChef,
    IsOwner,
    IsOwnerOrManager,
    IsWaiter,
)


@pytest.mark.parametrize(
    "permission,allowed",
    [
        (IsOwner, {"owner"}),
        (IsOwnerOrManager, {"owner", "manager"}),
        (IsCashier, {"cashier"}),
        (IsWaiter, {"waiter"}),
        (IsChef, {"chef"}),
    ],
)
@pytest.mark.parametrize("role", ["owner", "manager", "cashier", "waiter", "chef", ""])
def test_role_permission_matrix_has_no_owner_or_superuser_bypass(permission, allowed, role):
    user = User(username="permission-test", role=role, is_superuser=True)
    assert permission().has_permission(SimpleNamespace(user=user), None) == (role in allowed)


def test_default_permission_rejects_temporary_pin_and_inactive_users():
    user = User(role="waiter", must_change_pin=True)
    permission = IsAuthenticatedAndPinReady()
    assert not permission.has_permission(SimpleNamespace(user=user), None)
    user.must_change_pin = False
    assert permission.has_permission(SimpleNamespace(user=user), None)
    user.is_active = False
    assert not permission.has_permission(SimpleNamespace(user=user), None)
    assert not permission.has_permission(SimpleNamespace(user=AnonymousUser()), None)


def test_default_api_permission_blocks_pending_pin_change():
    from rest_framework.response import Response
    from rest_framework.test import APIRequestFactory, force_authenticate
    from rest_framework.views import APIView

    class ProtectedView(APIView):
        def get(self, request):
            return Response({"ok": True})

    user = User(role="waiter", must_change_pin=True)
    request = APIRequestFactory().get("/test-only/")
    force_authenticate(request, user=user)
    assert ProtectedView.as_view()(request).status_code == 403
    user.must_change_pin = False
    request = APIRequestFactory().get("/test-only/")
    force_authenticate(request, user=user)
    assert ProtectedView.as_view()(request).status_code == 200
