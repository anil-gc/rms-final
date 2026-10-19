from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q
from django.utils.crypto import salted_hmac

from .validators import validate_pin


class User(AbstractUser):
    """Single-location identities; blank legacy roles receive no API privileges."""

    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        MANAGER = "manager", "Manager"
        CASHIER = "cashier", "Cashier"
        WAITER = "waiter", "Waiter"
        CHEF = "chef", "Chef"

    role = models.CharField(max_length=10, choices=Role.choices, blank=True, default="")
    pin_hash = models.CharField(max_length=255, blank=True, editable=False)
    must_change_pin = models.BooleanField(default=False)
    auth_version = models.PositiveIntegerField(default=1, editable=False)

    class Meta(AbstractUser.Meta):
        abstract = False
        constraints = [
            models.CheckConstraint(
                condition=Q(role__in=["", "owner", "manager", "cashier", "waiter", "chef"]),
                name="accounts_valid_role",
            ),
            models.UniqueConstraint(
                fields=["role"], condition=Q(role="owner"), name="accounts_single_owner"
            ),
        ]

    @staticmethod
    def _peppered_pin(pin):
        return salted_hmac(
            "rms.accounts.pin", pin, secret=settings.PIN_PEPPER, algorithm="sha256"
        ).hexdigest()

    def set_pin(self, pin):
        validate_pin(pin)
        self.pin_hash = make_password(self._peppered_pin(pin))

    def check_pin(self, pin):
        return bool(self.pin_hash) and check_password(self._peppered_pin(pin), self.pin_hash)

    def _get_session_auth_hash(self, secret=None):
        # Django's normal session validation now also revokes sessions after a
        # PIN/role/state change. Django SECRET_KEY_FALLBACKS remain supported.
        value = ":".join(
            str(value)
            for value in (
                self.password,
                self.pin_hash,
                self.role,
                self.is_active,
                self.must_change_pin,
                self.auth_version,
            )
        )
        return salted_hmac(
            "rms.accounts.session", value, secret=secret, algorithm="sha256"
        ).hexdigest()


STAFF_ROLES = (User.Role.MANAGER, User.Role.CASHIER, User.Role.WAITER, User.Role.CHEF)


class LoginRateLimit(models.Model):
    """HMAC identifiers only; no raw usernames, IPs, PINs, or passwords."""

    key = models.CharField(max_length=64, primary_key=True)
    attempts = models.PositiveIntegerField(default=0)
    window_started = models.DateTimeField(db_index=True)
