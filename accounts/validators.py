import re

from django.core.exceptions import ValidationError

PHONE_REGEX = re.compile(r"^\+?[0-9\s\-()]{7,20}$")


def validate_phone_number(value):
    if value and not PHONE_REGEX.match(value):
        raise ValidationError("Enter a valid phone number.")
