from rest_framework import serializers

from apps.orders.models import OrderLine


class KitchenTicketSerializer(serializers.ModelSerializer):
    order_line_id = serializers.IntegerField(source="id", read_only=True)
    item_name = serializers.CharField(read_only=True)
    quantity = serializers.IntegerField(read_only=True)
    table_name = serializers.CharField(source="batch.order.session.table.name", read_only=True)
    order_id = serializers.UUIDField(source="batch.order.id", read_only=True)
    batch_id = serializers.UUIDField(source="batch.id", read_only=True)
    batch_sequence = serializers.IntegerField(source="batch.sequence", read_only=True)
    approved_at = serializers.DateTimeField(source="batch.reviewed_at", read_only=True)
    waiter_name = serializers.CharField(source="batch.submitted_by.username", read_only=True)

    status = serializers.SerializerMethodField()
    ticket_id = serializers.SerializerMethodField()

    class Meta:
        model = OrderLine
        fields = [
            "ticket_id",
            "order_line_id",
            "item_name",
            "quantity",
            "table_name",
            "order_id",
            "batch_id",
            "batch_sequence",
            "status",
            "created_at",
            "approved_at",
            "waiter_name",
        ]

    def get_status(self, obj):
        if hasattr(obj, "kitchen_ticket"):
            return obj.kitchen_ticket.status
        return "pending"

    def get_ticket_id(self, obj):
        if hasattr(obj, "kitchen_ticket"):
            return str(obj.kitchen_ticket.id)
        return None


class EmptyInputSerializer(serializers.Serializer):
    pass
