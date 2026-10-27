from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import STAFF_ROLES, User
from .validators import validate_pin


class StrictSerializer(serializers.Serializer):
    """Reject unexpected fields so role/privilege escalation is never silently ignored."""

    def to_internal_value(self, data):
        if isinstance(data, dict):
            unknown = set(data) - set(self.fields)
            if unknown:
                raise serializers.ValidationError(
                    {key: "Unknown field." for key in sorted(unknown)}
                )
        return super().to_internal_value(data)


class PINField(serializers.CharField):
    def __init__(self, **kwargs):
        super().__init__(trim_whitespace=False, write_only=True, **kwargs)

    def to_internal_value(self, data):
        if not isinstance(data, str):
            raise serializers.ValidationError("Supply the PIN as a string.")
        return super().to_internal_value(data)


class NewPINField(PINField):
    def __init__(self, **kwargs):
        super().__init__(max_length=4, min_length=4, **kwargs)

    def run_validation(self, data=serializers.empty):
        value = super().run_validation(data)
        try:
            validate_pin(value)
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.messages) from error
        return value


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "role",
            "is_active",
            "must_change_pin",
        ]
        read_only_fields = fields


class OwnerLoginSerializer(StrictSerializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=1024)


class StaffLoginSerializer(StrictSerializer):
    username = serializers.CharField(max_length=150)
    pin = PINField(max_length=128)


class OwnerConfirmationSerializer(StrictSerializer):
    owner_password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=1024)


class StaffCreateSerializer(OwnerConfirmationSerializer):
    username = serializers.CharField(max_length=150, validators=[UnicodeUsernameValidator()])
    first_name = serializers.CharField(max_length=150, required=False, default="", allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, default="", allow_blank=True)
    role = serializers.ChoiceField(choices=STAFF_ROLES)
    pin = NewPINField()


class PINChangeSerializer(StrictSerializer):
    current_pin = PINField(max_length=128)
    new_pin = NewPINField()


class PINResetSerializer(OwnerConfirmationSerializer):
    new_pin = NewPINField()


class StaffStateSerializer(OwnerConfirmationSerializer):
    is_active = serializers.BooleanField()


class OwnerPasswordChangeSerializer(StrictSerializer):
    current_password = serializers.CharField(
        write_only=True, trim_whitespace=False, max_length=1024
    )
    new_password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=1024)
