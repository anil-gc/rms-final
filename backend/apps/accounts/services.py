from django.conf import settings
from django.contrib.auth import authenticate, login, update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.views.decorators.debug import sensitive_variables
from rest_framework.exceptions import APIException, Throttled, ValidationError

from .models import STAFF_ROLES, User
from .rate_limits import (
    LoginRateLimited,
    consume_credential_attempt,
    refund_successful_account_attempt,
)


class InvalidCredentials(APIException):
    status_code = 401
    default_detail = "Invalid credentials."
    default_code = "invalid_credentials"


@sensitive_variables("credential")
def verify_credentials(request, username, credential, *, kind):
    raw_request = request._request
    # Pass PINs via `password`: Django redacts this key in user_login_failed signals.
    user = authenticate(raw_request, username=username, password=credential, credential_type=kind)
    if getattr(raw_request, "_rms_login_wait", None):
        raise Throttled(wait=raw_request._rms_login_wait)
    if user is None:
        raise InvalidCredentials()
    return user


def start_session(request, user):
    login(request._request, user, backend="apps.accounts.backends.AccountBackend")
    seconds = (
        settings.ACCOUNTS_OWNER_SESSION_SECONDS
        if user.role == User.Role.OWNER
        else settings.ACCOUNTS_STAFF_SESSION_SECONDS
    )
    request.session.set_expiry(seconds)


@sensitive_variables("password")
def confirm_owner(request, password):
    owner = verify_credentials(request, request.user.username, password, kind="password")
    if owner.pk != request.user.pk or owner.role != User.Role.OWNER:
        raise InvalidCredentials()
    return owner


@sensitive_variables("pin", "owner_password")
def create_staff(request, *, pin, owner_password, **attributes):
    confirm_owner(request, owner_password)
    user = User(**attributes, must_change_pin=True)
    user.set_unusable_password()
    user.set_pin(pin)
    try:
        with transaction.atomic():
            user.save()
    except IntegrityError as error:
        raise ValidationError({"username": "This username is unavailable."}) from error
    return user


def get_staff(pk, *, lock=False):
    queryset = User.objects.filter(role__in=STAFF_ROLES)
    if lock:
        queryset = queryset.select_for_update()
    return get_object_or_404(queryset, pk=pk)


@sensitive_variables("current_pin", "new_pin")
def change_pin(request, *, current_pin, new_pin):
    try:
        account_key = consume_credential_attempt(
            request.user.username, request.META.get("REMOTE_ADDR", "unknown"), scope="pin-change"
        )
    except LoginRateLimited as error:
        raise Throttled(wait=error.wait) from error
    with transaction.atomic():
        user = get_staff(request.user.pk, lock=True)
        if not user.check_pin(current_pin):
            raise InvalidCredentials()
        if user.check_pin(new_pin):
            raise ValidationError({"new_pin": "Choose a different PIN."})
        user.set_pin(new_pin)
        user.must_change_pin = False
        user.auth_version += 1
        user.save(update_fields=["pin_hash", "must_change_pin", "auth_version"])
    refund_successful_account_attempt(account_key)
    update_session_auth_hash(request._request, user)
    return user


@sensitive_variables("new_pin", "owner_password")
def reset_staff_pin(request, pk, *, new_pin, owner_password):
    confirm_owner(request, owner_password)
    with transaction.atomic():
        user = get_staff(pk, lock=True)
        if user.check_pin(new_pin):
            raise ValidationError({"new_pin": "Choose a different PIN."})
        user.set_pin(new_pin)
        user.must_change_pin = True
        user.auth_version += 1
        user.save(update_fields=["pin_hash", "must_change_pin", "auth_version"])
    return user


@sensitive_variables("owner_password")
def change_staff_state(request, pk, *, is_active, owner_password):
    confirm_owner(request, owner_password)
    with transaction.atomic():
        user = get_staff(pk, lock=True)
        user.is_active = is_active
        user.auth_version += 1
        user.save(update_fields=["is_active", "auth_version"])
    return user


@sensitive_variables("current_password", "new_password")
def change_owner_password(request, *, current_password, new_password):
    confirm_owner(request, current_password)
    with transaction.atomic():
        user = User.objects.select_for_update().get(pk=request.user.pk)
        # Recheck under the lock to serialize concurrent password changes.
        if not user.check_password(current_password):
            raise InvalidCredentials()
        if user.check_password(new_password):
            raise ValidationError({"new_password": "Choose a different password."})
        try:
            validate_password(new_password, user)
        except DjangoValidationError as error:
            raise ValidationError({"new_password": error.messages}) from error
        user.set_password(new_password)
        user.auth_version += 1
        user.save(update_fields=["password", "auth_version"])
    update_session_auth_hash(request._request, user)
    return user
