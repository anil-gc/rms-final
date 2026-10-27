"""Table visits, immutable submissions and attributable cashier decisions."""

import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q


class DiningSession(models.Model):
    class State(models.TextChoices):
        OPEN = "open", "Open"
        CLOSED = "closed", "Closed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    table = models.ForeignKey(
        "restaurants.DiningTable", on_delete=models.PROTECT, related_name="dining_sessions"
    )
    state = models.CharField(max_length=8, choices=State.choices, default=State.OPEN)
    opened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="opened_dining_sessions"
    )
    opened_at = models.DateTimeField(auto_now_add=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="closed_dining_sessions",
    )
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-opened_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["table"],
                condition=Q(state="open"),
                name="orders_one_open_session_per_table",
            ),
            models.CheckConstraint(
                condition=(
                    Q(state="open", closed_by__isnull=True, closed_at__isnull=True)
                    | Q(state="closed", closed_by__isnull=False, closed_at__isnull=False)
                ),
                name="orders_session_state_consistent",
            ),
        ]


class Order(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.OneToOneField(DiningSession, on_delete=models.PROTECT, related_name="order")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "id"]


class OrderBatch(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="batches")
    sequence = models.PositiveIntegerField()
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="submitted_order_batches"
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reviewed_order_batches",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.CharField(max_length=500, blank=True)
    idempotency_key = models.UUIDField(editable=False)
    request_fingerprint = models.CharField(max_length=64, editable=False)

    class Meta:
        ordering = ["sequence", "id"]
        indexes = [models.Index(fields=["status", "submitted_at"], name="orders_pending_queue")]
        constraints = [
            models.UniqueConstraint(fields=["order", "sequence"], name="orders_batch_sequence"),
            models.UniqueConstraint(
                fields=["order", "submitted_by", "idempotency_key"],
                name="orders_submission_idempotency",
            ),
            models.CheckConstraint(condition=Q(sequence__gte=1), name="orders_sequence_positive"),
            models.CheckConstraint(
                condition=(
                    Q(
                        status="pending",
                        reviewed_by__isnull=True,
                        reviewed_at__isnull=True,
                        rejection_reason="",
                    )
                    | Q(
                        status="approved",
                        reviewed_by__isnull=False,
                        reviewed_at__isnull=False,
                        rejection_reason="",
                    )
                    | (
                        Q(status="rejected", reviewed_by__isnull=False, reviewed_at__isnull=False)
                        & Q(rejection_reason__regex=r"\S")
                    )
                ),
                name="orders_review_consistent",
            ),
        ]

    @property
    def total(self):
        return sum((line.line_total for line in self.lines.all()), Decimal("0.00"))


class AppendOnlyQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError("Submitted lines and audit events are append-only.")

    def delete(self):
        raise ValidationError("Submitted lines and audit events cannot be deleted.")

    def bulk_update(self, objs, fields, batch_size=None):
        raise ValidationError("Submitted lines and audit events are append-only.")


class AppendOnlyModel(models.Model):
    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Submitted lines and audit events are append-only.")
        kwargs["force_insert"] = True
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Submitted lines and audit events cannot be deleted.")


class OrderLine(AppendOnlyModel):
    batch = models.ForeignKey(OrderBatch, on_delete=models.PROTECT, related_name="lines")
    menu_item = models.ForeignKey("menu.MenuItem", on_delete=models.PROTECT)
    item_name = models.CharField(max_length=150)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveSmallIntegerField()
    line_total = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["batch", "menu_item"], name="orders_distinct_line"),
            models.CheckConstraint(
                condition=Q(quantity__gte=1, quantity__lte=99), name="orders_quantity_range"
            ),
            models.CheckConstraint(
                condition=Q(unit_price__gt=0, unit_price__lte=Decimal("99999999.99")),
                name="orders_price_range",
            ),
            models.CheckConstraint(
                condition=Q(line_total=F("unit_price") * F("quantity")),
                name="orders_line_total_exact",
            ),
            models.CheckConstraint(
                condition=Q(item_name__regex=r"\S"), name="orders_snapshot_name_nonblank"
            ),
        ]


class OrderEvent(AppendOnlyModel):
    class Kind(models.TextChoices):
        SESSION_OPENED = "session_opened", "Dining session opened"
        ORDER_CREATED = "order_created", "Order created"
        BATCH_SUBMITTED = "batch_submitted", "Batch submitted"
        BATCH_APPROVED = "batch_approved", "Batch approved"
        BATCH_REJECTED = "batch_rejected", "Batch rejected"

    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="events")
    batch = models.ForeignKey(
        OrderBatch, on_delete=models.PROTECT, null=True, blank=True, related_name="events"
    )
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    kind = models.CharField(max_length=24, choices=Kind.choices)
    reason = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(kind__in=["session_opened", "order_created"], batch__isnull=True, reason="")
                    | Q(
                        kind__in=["batch_submitted", "batch_approved"],
                        batch__isnull=False,
                        reason="",
                    )
                    | (Q(kind="batch_rejected", batch__isnull=False) & Q(reason__regex=r"\S"))
                ),
                name="orders_event_shape",
            ),
            models.UniqueConstraint(
                fields=["batch", "kind"],
                condition=Q(batch__isnull=False),
                name="orders_unique_batch_event",
            ),
            models.UniqueConstraint(
                fields=["order", "kind"],
                condition=Q(batch__isnull=True),
                name="orders_unique_opening_event",
            ),
        ]
