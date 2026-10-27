import re

from django.core.exceptions import ValidationError


def validate_pin(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}", value):
        raise ValidationError("Use exactly four ASCII digits, supplied as a string.")
    ascending = "0123456789012"
    descending = "9876543210987"
    if len(set(value)) == 1 or value in ascending or value in descending:
        raise ValidationError("Choose a less predictable PIN.")
