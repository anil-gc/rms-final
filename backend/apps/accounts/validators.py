import re

from django.core.exceptions import ValidationError


def validate_pin(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{6}", value):
        raise ValidationError("Use exactly six ASCII digits, supplied as a string.")
    if len(set(value)) == 1 or value in {"123456", "654321", "012345", "987654"}:
        raise ValidationError("Choose a less predictable PIN.")
