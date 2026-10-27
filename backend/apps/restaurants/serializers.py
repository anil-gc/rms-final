import re

from rest_framework import serializers

from apps.core.api import StrictModelSerializer

from .models import DiningTable, Restaurant


class RestaurantSerializer(StrictModelSerializer):
    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = Restaurant
        fields = [
            "id",
            "name",
            "description",
            "address",
            "contact_phone",
            "email",
            "logo_url",
            "currency",
            "opening_time",
            "closing_time",
            "is_active",
            "updated_at",
        ]
        read_only_fields = ["id", "updated_at"]

    def get_logo_url(self, obj):
        if not obj.logo:
            return None
        return f"/api/v1/restaurant/logo/?v={obj.updated_at.timestamp()}"

    def validate_contact_phone(self, value):
        if value and (
            not re.fullmatch(r"\+?[0-9 ()-]+", value)
            or not 7 <= len(re.sub(r"\D", "", value)) <= 15
        ):
            raise serializers.ValidationError(
                "Use 7–15 digits, optionally with +, spaces, brackets or hyphens."
            )
        return value

    def validate(self, attrs):
        opening = attrs.get("opening_time", getattr(self.instance, "opening_time", None))
        closing = attrs.get("closing_time", getattr(self.instance, "closing_time", None))
        if (opening is None) != (closing is None) or (opening is not None and opening == closing):
            raise serializers.ValidationError(
                {
                    "closing_time": "Set two different times or clear both. "
                    "Overnight hours are allowed."
                }
            )
        return attrs


class DiningTableSerializer(StrictModelSerializer):
    has_active_session = serializers.BooleanField(read_only=True, default=False)

    class Meta:
        model = DiningTable
        fields = [
            "id",
            "name",
            "capacity",
            "status",
            "is_active",
            "updated_at",
            "has_active_session",
        ]
        read_only_fields = ["id", "updated_at", "has_active_session"]

    def validate_name(self, value):
        query = DiningTable.objects.filter(name__iexact=value)
        if self.instance:
            query = query.exclude(pk=self.instance.pk)
        if query.exists():
            raise serializers.ValidationError(
                "A table with this name already exists, including archived tables."
            )
        return value

    def validate(self, attrs):
        active = attrs.get("is_active", getattr(self.instance, "is_active", True))
        status = attrs.get("status", getattr(self.instance, "status", DiningTable.Status.AVAILABLE))
        if self.instance and (not active or status != DiningTable.Status.OCCUPIED):
            from apps.orders.models import DiningSession

            if DiningSession.objects.filter(table=self.instance, state="open").exists():
                raise serializers.ValidationError(
                    {
                        "status": "An active dining session keeps this table occupied "
                        "until billing closes it."
                    }
                )
        if not active and status != DiningTable.Status.AVAILABLE:
            raise serializers.ValidationError(
                {
                    "status": "Mark the table available before archiving. "
                    "Archived tables cannot be occupied."
                }
            )
        return attrs
