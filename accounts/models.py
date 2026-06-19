import secrets
from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

from .managers import UserManager

PASSWORD_RESET_TOKEN_TTL = timedelta(hours=1)
EMAIL_VERIFICATION_TOKEN_TTL = timedelta(hours=24)


def _generate_token():
    return secrets.token_urlsafe(32)


class GenderChoices(models.TextChoices):
    MALE = "male", "Male"
    FEMALE = "female", "Female"
    OTHER = "other", "Other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say", "Prefer not to say"


class User(AbstractUser):
    email = models.EmailField(unique=True)
    username = models.CharField(
        max_length=150, unique=True, blank=True, null=True
    )
    full_name = models.CharField(max_length=150, blank=True)
    phone_number = models.CharField(max_length=32, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=20, choices=GenderChoices.choices, blank=True
    )
    profile_image = models.ImageField(
        upload_to="profile_images/", null=True, blank=True
    )
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email


class PasswordResetToken(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="password_reset_tokens"
    )
    token = models.CharField(max_length=64, unique=True, default=_generate_token)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + PASSWORD_RESET_TOKEN_TTL
        super().save(*args, **kwargs)

    def is_valid(self):
        return self.used_at is None and self.expires_at > timezone.now()


class EmailVerificationToken(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="email_verification_tokens"
    )
    token = models.CharField(max_length=64, unique=True, default=_generate_token)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + EMAIL_VERIFICATION_TOKEN_TTL
        super().save(*args, **kwargs)

    def is_valid(self):
        return self.used_at is None and self.expires_at > timezone.now()
