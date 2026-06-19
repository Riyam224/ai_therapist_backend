import re

from django.core.exceptions import ValidationError

PHONE_REGEX = re.compile(r"^\+?[0-9\s\-()]{7,20}$")

ALLOWED_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


def validate_password_strength(password):
    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters long.")
    if not re.search(r"[A-Z]", password):
        raise ValidationError(
            "Password must contain at least one uppercase letter."
        )
    if not re.search(r"[a-z]", password):
        raise ValidationError(
            "Password must contain at least one lowercase letter."
        )
    if not re.search(r"[0-9]", password):
        raise ValidationError("Password must contain at least one number.")


def validate_phone_number(value):
    if value and not PHONE_REGEX.match(value):
        raise ValidationError("Enter a valid phone number.")


def validate_profile_image(image):
    content_type = getattr(image, "content_type", None)
    if content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
        raise ValidationError(
            "Unsupported image type. Allowed formats: JPG, JPEG, PNG, WEBP."
        )
    if image.size > MAX_IMAGE_SIZE_BYTES:
        raise ValidationError("Image file too large. Maximum size is 5 MB.")
