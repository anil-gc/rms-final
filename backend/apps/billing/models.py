import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models


class Bill(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        FINALIZED = "finalized", "Finalized"
        PARTIALLY_PAID = "partially_paid", "Partially Paid"
        PAID = "paid", "Paid"
        VOIDED = "voided", "Voided"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    human_id = models.CharField(max_length=20, unique=True, editable=False)
    session = models.ForeignKey(
        "orders.DiningSession", on_delete=models.PROTECT, related_name="bills"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    taxable_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    service_charge = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="created_bills",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    finalized_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="finalized_bills",
    )
    finalized_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "id"]
        constraints = [
            models.CheckConstraint(
                condition=(models.Q(paid_amount__lte=models.F("grand_total"))),
                name="billing_paid_amount_lte_grand_total",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(subtotal__gte=0)
                    & models.Q(discount_amount__gte=0)
                    & models.Q(taxable_amount__gte=0)
                    & models.Q(tax_amount__gte=0)
                    & models.Q(service_charge__gte=0)
                    & models.Q(grand_total__gte=0)
                    & models.Q(paid_amount__gte=0)
                ),
                name="billing_amounts_non_negative",
            ),
        ]

    @property
    def outstanding_amount(self):
        return max(Decimal("0.00"), self.grand_total - self.paid_amount)


class BillLine(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bill = models.ForeignKey(Bill, on_delete=models.PROTECT, related_name="lines")
    order_line = models.OneToOneField(
        "orders.OrderLine", on_delete=models.PROTECT, related_name="bill_line"
    )
    item_name = models.CharField(max_length=150)
    quantity = models.PositiveSmallIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gte=1, quantity__lte=99), name="billing_quantity_range"
            ),
            models.CheckConstraint(
                condition=models.Q(unit_price__gt=0, unit_price__lte=Decimal("99999999.99")),
                name="billing_price_range",
            ),
            models.CheckConstraint(
                condition=models.Q(line_total=models.F("unit_price") * models.F("quantity")),
                name="billing_line_total_exact",
            ),
        ]


class Payment(models.Model):
    class Method(models.TextChoices):
        CASH = "cash", "Cash"
        CARD = "card", "Card terminal / POS"
        DIGITAL_WALLET = "digital_wallet", "QR or digital wallet"

    class Status(models.TextChoices):
        SUCCESS = "success", "Success"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bill = models.ForeignKey(Bill, on_delete=models.PROTECT, related_name="payments")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=20, choices=Method.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUCCESS)

    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    received_at = models.DateTimeField(auto_now_add=True)

    manual_reference = models.CharField(max_length=100, blank=True)
    idempotency_key = models.UUIDField(unique=True, editable=False)

    class Meta:
        ordering = ["received_at", "id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0), name="billing_payment_amount_positive"
            )
        ]


class PrintEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bill = models.ForeignKey(Bill, on_delete=models.PROTECT, related_name="print_events")
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["timestamp", "id"]
