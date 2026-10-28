from rest_framework import serializers

from apps.accounts.serializers import UserSerializer
from apps.billing.models import Bill, BillLine, Payment, PrintEvent


class BillLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillLine
        fields = (
            "id",
            "item_name",
            "quantity",
            "unit_price",
            "line_total",
        )


class PaymentSerializer(serializers.ModelSerializer):
    received_by = UserSerializer(read_only=True)

    class Meta:
        model = Payment
        fields = (
            "id",
            "amount",
            "method",
            "status",
            "received_by",
            "received_at",
            "manual_reference",
            "idempotency_key",
        )


class BillSerializer(serializers.ModelSerializer):
    lines = BillLineSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)
    outstanding_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    created_by = UserSerializer(read_only=True)
    finalized_by = UserSerializer(read_only=True)

    class Meta:
        model = Bill
        fields = (
            "id",
            "human_id",
            "session",
            "status",
            "subtotal",
            "discount_amount",
            "taxable_amount",
            "tax_amount",
            "service_charge",
            "grand_total",
            "paid_amount",
            "outstanding_amount",
            "lines",
            "payments",
            "created_by",
            "created_at",
            "finalized_by",
            "finalized_at",
        )


class PaymentCreateSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    method = serializers.ChoiceField(choices=Payment.Method.choices)
    idempotency_key = serializers.UUIDField()
    manual_reference = serializers.CharField(max_length=100, allow_blank=True, required=False)


class PrintEventSerializer(serializers.ModelSerializer):
    requested_by = UserSerializer(read_only=True)

    class Meta:
        model = PrintEvent
        fields = ("id", "requested_by", "timestamp")
