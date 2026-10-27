import math
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.utils.crypto import salted_hmac

from .models import LoginRateLimit


@dataclass
class LoginRateLimited(Exception):
    wait: int


def consume_credential_attempt(username, address, *, scope="login", pin=False):
    """Reserve an attempt before hashing; PostgreSQL locks prevent lost updates."""
    now = timezone.now()
    budgets = [
        (
            f"{scope}:account:{username.casefold()}",
            min(settings.ACCOUNTS_LOGIN_ACCOUNT_LIMIT, settings.ACCOUNTS_PIN_ACCOUNT_LIMIT)
            if pin or scope == "pin-change"
            else settings.ACCOUNTS_LOGIN_ACCOUNT_LIMIT,
            settings.ACCOUNTS_LOGIN_ACCOUNT_WINDOW_SECONDS,
        ),
        (
            f"{scope}:ip:{address}",
            settings.ACCOUNTS_LOGIN_IP_LIMIT,
            settings.ACCOUNTS_LOGIN_IP_WINDOW_SECONDS,
        ),
    ]
    budgets = sorted(
        (
            salted_hmac("rms.accounts.login-limit", key, algorithm="sha256").hexdigest(),
            limit,
            window,
        )
        for key, limit, window in budgets
    )
    account_key = salted_hmac(
        "rms.accounts.login-limit", f"{scope}:account:{username.casefold()}", algorithm="sha256"
    ).hexdigest()
    with transaction.atomic():
        for key, limit, window in budgets:
            bucket, _ = LoginRateLimit.objects.select_for_update().get_or_create(
                key=key, defaults={"window_started": now}
            )
            expires = bucket.window_started + timedelta(seconds=window)
            if expires <= now:
                bucket.attempts = 0
                bucket.window_started = now
            elif bucket.attempts >= limit:
                raise LoginRateLimited(max(1, math.ceil((expires - now).total_seconds())))
            bucket.attempts += 1
            bucket.save(update_fields=["attempts", "window_started"])
            if key == account_key:
                account_window = bucket.window_started
    return account_key, account_window


def refund_successful_account_attempt(reservation):
    # Only the admitted successful attempt is refunded. Prior failures remain;
    # IP budgets continue to count every attempt, including successful ones.
    key, window = reservation
    LoginRateLimit.objects.filter(key=key, window_started=window, attempts__gt=0).update(
        attempts=F("attempts") - 1
    )
