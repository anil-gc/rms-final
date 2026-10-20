"""One restaurant and its physical tables. No orders or tenancy."""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.functions import Lower, Trim


class Restaurant(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, max_length=2000)
    address = models.CharField(max_length=500, blank=True)
    contact_phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    logo = models.ImageField(upload_to="restaurant-logos/", blank=True)
    currency = models.CharField(max_length=3, default="NPR", choices=[("NPR", "NPR")])
    opening_time = models.TimeField(null=True, blank=True)
    closing_time = models.TimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(id=1), name="restaurant_singleton"),
            models.CheckConstraint(condition=models.Q(currency="NPR"), name="restaurant_npr"),
            models.CheckConstraint(
                condition=models.Q(name__regex=r"\S"), name="restaurant_name_nonblank"
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(opening_time__isnull=True, closing_time__isnull=True)
                    | (
                        models.Q(opening_time__isnull=False, closing_time__isnull=False)
                        & ~models.Q(opening_time=models.F("closing_time"))
                    )
                ),
                name="restaurant_hours_pair",
            ),
        ]

    def __str__(self):
        return self.name


class DiningTable(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        OCCUPIED = "occupied", "Occupied"

    restaurant = models.ForeignKey(Restaurant, on_delete=models.PROTECT, related_name="tables")
    name = models.CharField(max_length=40)
    capacity = models.PositiveSmallIntegerField(
        default=2, validators=[MinValueValidator(1), MaxValueValidator(50)]
    )
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.AVAILABLE)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]
        constraints = [
            models.UniqueConstraint(Lower(Trim("name")), name="table_name_unique_ci"),
            models.CheckConstraint(
                condition=models.Q(name__regex=r"\S"), name="table_name_nonblank"
            ),
            models.CheckConstraint(
                condition=models.Q(capacity__gte=1, capacity__lte=50), name="table_capacity_range"
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=["available", "occupied"]), name="table_status_valid"
            ),
            models.CheckConstraint(
                condition=models.Q(is_active=True) | models.Q(status="available"),
                name="inactive_table_available",
            ),
        ]

    def __str__(self):
        return self.name
