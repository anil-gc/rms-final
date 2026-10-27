from decimal import Decimal

from rest_framework import serializers

from apps.core.api import StrictModelSerializer

from .models import Order, OrderBatch, OrderEvent, OrderLine
from .services import validate_lines


class StrictInputSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if not isinstance(data, dict) or set(data) - set(self.fields):
            raise serializers.ValidationError(
                {"detail": "Unknown fields or invalid request object."}
            )
        return super().to_internal_value(data)


class EmptyInputSerializer(StrictInputSerializer):
    pass


class SubmissionSerializer(StrictInputSerializer):
    idempotency_key = serializers.UUIDField()
    lines = serializers.JSONField()

    def validate_lines(self, value):
        return validate_lines(value)


class RejectionSerializer(StrictInputSerializer):
    reason = serializers.CharField(max_length=500, allow_blank=False, trim_whitespace=True)


class LineSerializer(StrictModelSerializer):
    class Meta:
        model = OrderLine
        fields = [
            "id",
            "menu_item",
            "item_name",
            "unit_price",
            "quantity",
            "line_total",
            "created_at",
        ]
        read_only_fields = fields


class BatchSerializer(StrictModelSerializer):
    lines = LineSerializer(many=True, read_only=True)
    total = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    submitted_by_name = serializers.CharField(source="submitted_by.username", read_only=True)
    reviewed_by_name = serializers.CharField(
        source="reviewed_by.username", read_only=True, allow_null=True
    )
    table_name = serializers.CharField(source="order.session.table.name", read_only=True)

    class Meta:
        model = OrderBatch
        fields = [
            "id",
            "order",
            "sequence",
            "status",
            "submitted_by",
            "submitted_by_name",
            "submitted_at",
            "reviewed_by",
            "reviewed_by_name",
            "reviewed_at",
            "rejection_reason",
            "table_name",
            "lines",
            "total",
        ]
        read_only_fields = fields


class EventSerializer(StrictModelSerializer):
    actor_name = serializers.CharField(source="actor.username", read_only=True)

    class Meta:
        model = OrderEvent
        fields = ["id", "batch", "actor", "actor_name", "kind", "reason", "created_at"]
        read_only_fields = fields


class OrderSummarySerializer(StrictModelSerializer):
    table = serializers.IntegerField(source="session.table_id", read_only=True)
    table_name = serializers.CharField(source="session.table.name", read_only=True)
    state = serializers.CharField(source="session.state", read_only=True)
    opened_at = serializers.DateTimeField(source="session.opened_at", read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "session",
            "table",
            "table_name",
            "state",
            "opened_at",
            "created_by",
            "created_at",
        ]
        read_only_fields = fields


class OrderDetailSerializer(OrderSummarySerializer):
    batches = BatchSerializer(many=True, read_only=True)
    events = EventSerializer(many=True, read_only=True)
    totals = serializers.SerializerMethodField()

    class Meta(OrderSummarySerializer.Meta):
        fields = [*OrderSummarySerializer.Meta.fields, "batches", "events", "totals"]
        read_only_fields = fields

    def get_totals(self, obj):
        totals = {status: Decimal("0.00") for status in OrderBatch.Status.values}
        for batch in obj.batches.all():
            totals[batch.status] += batch.total
        return {key: format(value, ".2f") for key, value in totals.items()}
