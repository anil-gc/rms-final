from rest_framework.permissions import BasePermission

from .models import User


class IsProvisionedUser(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and user.is_authenticated and user.is_active and user.role in User.Role.values
        )


class IsAuthenticatedAndPinReady(IsProvisionedUser):
    message = "An active account with a completed PIN change is required."

    def has_permission(self, request, view):
        return super().has_permission(request, view) and not request.user.must_change_pin


class HasRole(IsAuthenticatedAndPinReady):
    allowed_roles = ()

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role in self.allowed_roles


class IsOwner(HasRole):
    allowed_roles = (User.Role.OWNER,)


class IsOwnerOrManager(HasRole):
    allowed_roles = (User.Role.OWNER, User.Role.MANAGER)


class IsCashier(HasRole):
    allowed_roles = (User.Role.CASHIER,)


class IsWaiter(HasRole):
    allowed_roles = (User.Role.WAITER,)


class IsChef(HasRole):
    allowed_roles = (User.Role.CHEF,)
