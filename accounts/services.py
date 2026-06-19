import logging

from django.utils import timezone

from .models import EmailVerificationToken, PasswordResetToken

logger = logging.getLogger(__name__)


def success_response(message, data=None):
    return {"success": True, "message": message, "data": data or {}}


def error_response(message, errors=None):
    return {"success": False, "message": message, "errors": errors or {}}


def send_password_reset_email(user, token):
    """Stub: actual email delivery is out of scope for this feature (see spec.md Assumptions).

    Mocked in tests; swap for a real provider call later without changing call sites.
    """
    logger.info("Password reset token issued for %s: %s", user.email, token)


def send_verification_email(user, token):
    """Stub: actual email delivery is out of scope for this feature (see spec.md Assumptions).

    Mocked in tests; swap for a real provider call later without changing call sites.
    """
    logger.info("Email verification token issued for %s: %s", user.email, token)


def issue_password_reset_token(user):
    return PasswordResetToken.objects.create(user=user)


def get_valid_password_reset_token(token):
    try:
        reset_token = PasswordResetToken.objects.get(token=token)
    except PasswordResetToken.DoesNotExist:
        return None
    return reset_token if reset_token.is_valid() else None


def consume_password_reset_token(reset_token):
    reset_token.used_at = timezone.now()
    reset_token.save(update_fields=["used_at"])


def issue_email_verification_token(user):
    return EmailVerificationToken.objects.create(user=user)


def get_valid_email_verification_token(token):
    try:
        verification_token = EmailVerificationToken.objects.get(token=token)
    except EmailVerificationToken.DoesNotExist:
        return None
    return verification_token if verification_token.is_valid() else None


def consume_email_verification_token(verification_token):
    verification_token.used_at = timezone.now()
    verification_token.save(update_fields=["used_at"])
    verification_token.user.is_verified = True
    verification_token.user.save(update_fields=["is_verified"])
