from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.hashers import make_password
from django.views.decorators.debug import sensitive_variables

from .models import STAFF_ROLES, User
from .rate_limits import (
    LoginRateLimited,
    consume_credential_attempt,
    refund_successful_account_attempt,
)


class AccountBackend(ModelBackend):
    """One rate-limited backend for API PIN/password and standard admin login."""

    @sensitive_variables("password")
    def authenticate(
        self, request, username=None, password=None, credential_type="password", **kwargs
    ):
        if username is None or password is None:
            return None
        if request is not None:
            request._rms_login_wait = None
        address = request.META.get("REMOTE_ADDR", "unknown") if request is not None else "internal"
        try:
            account_key = consume_credential_attempt(username, address)
        except LoginRateLimited as error:
            if request is not None:
                request._rms_login_wait = error.wait
            return None

        user = User.objects.filter(username=username).first()
        valid = False
        if user and user.is_active:
            if credential_type == "pin" and user.role in STAFF_ROLES and user.pin_hash:
                valid = user.check_pin(password)
            elif (
                credential_type == "password"
                and (user.role == User.Role.OWNER or user.is_superuser)
                and user.has_usable_password()
            ):
                valid = user.check_password(password)
            else:
                make_password(password)
        else:
            # Unknown and disabled identities still perform an expensive hash.
            make_password(password)
        if valid:
            refund_successful_account_attempt(account_key)
            return user
        return None
