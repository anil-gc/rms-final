import uuid

from django.conf import settings
from django.db import models


class KitchenTicket(models.Model):
    class Status(models.TextChoices):
        PREPARING = "preparing", "Preparing"
        READY = "ready", "Ready"
        SERVED = "served", "Served"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_line = models.OneToOneField(
        "orders.OrderLine", on_delete=models.PROTECT, related_name="kitchen_ticket"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PREPARING)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at", "id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=["preparing", "ready", "served"]),
                name="kitchen_ticket_status_valid",
            ),
        ]


class KitchenEvent(models.Model):
    class Kind(models.TextChoices):
        MARKED_PREPARING = "marked_preparing", "Marked Preparing"
        MARKED_READY = "marked_ready", "Marked Ready"
        MARKED_SERVED = "marked_served", "Marked Served"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.ForeignKey(KitchenTicket, on_delete=models.PROTECT, related_name="events")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    kind = models.CharField(max_length=20, choices=Kind.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        constraints = [
            models.UniqueConstraint(fields=["ticket", "kind"], name="kitchen_unique_ticket_event")
        ]
