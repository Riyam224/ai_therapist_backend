import io
import tempfile
from unittest.mock import patch

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient

from .models import EmailVerificationToken, PasswordResetToken, User


VALID_PASSWORD = "StrongPass1"


def _png_upload(name="photo.png", size=(10, 10)):
    buffer = io.BytesIO()
    Image.new("RGB", size, color="red").save(buffer, format="PNG")
    buffer.seek(0)
    return SimpleUploadedFile(name, buffer.read(), content_type="image/png")


def _register(client, email="alice@example.com", password=VALID_PASSWORD, **extra):
    payload = {
        "email": email,
        "password": password,
        "password_confirm": password,
    }
    payload.update(extra)
    return client.post("/api/accounts/register/", payload, format="json")


class RegisterTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def test_register_success(self):
        response = _register(self.client)
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["success"])
        self.assertIn("access", response.data["data"])
        self.assertIn("refresh", response.data["data"])
        self.assertEqual(response.data["data"]["user"]["email"], "alice@example.com")

    def test_register_duplicate_email_rejected(self):
        _register(self.client)
        response = _register(self.client)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data["success"])
        self.assertIn("email", response.data["errors"])

    def test_register_rejects_weak_password(self):
        response = _register(
            self.client, email="bob@example.com", password="weak", password_confirm="weak"
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data["success"])
        self.assertIn("password", response.data["errors"])


class LoginTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        _register(self.client, email="alice@example.com")

    def test_login_success(self):
        response = self.client.post(
            "/api/accounts/login/",
            {"email": "alice@example.com", "password": VALID_PASSWORD},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertIn("access", response.data["data"])
        self.assertIn("refresh", response.data["data"])

    def test_login_invalid_password_rejected(self):
        response = self.client.post(
            "/api/accounts/login/",
            {"email": "alice@example.com", "password": "WrongPass1"},
            format="json",
        )
        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.data["success"])


class LogoutTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        reg = _register(self.client, email="alice@example.com")
        self.access = reg.data["data"]["access"]
        self.refresh = reg.data["data"]["refresh"]

    def test_logout_blacklists_refresh_token(self):
        response = self.client.post(
            "/api/accounts/logout/",
            {"refresh": self.refresh},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {self.access}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])

        refresh_response = self.client.post(
            "/api/accounts/token/refresh/",
            {"refresh": self.refresh},
            format="json",
        )
        self.assertEqual(refresh_response.status_code, 401)


class TokenRefreshTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        reg = _register(self.client, email="alice@example.com")
        self.refresh = reg.data["data"]["refresh"]

    def test_token_refresh_returns_new_access_token(self):
        response = self.client.post(
            "/api/accounts/token/refresh/",
            {"refresh": self.refresh},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertIn("access", response.data["data"])


class ThrottlingTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def test_login_throttled_after_five_attempts(self):
        statuses = []
        for _ in range(6):
            response = self.client.post(
                "/api/accounts/login/",
                {"email": "nobody@example.com", "password": "wrong"},
                format="json",
            )
            statuses.append(response.status_code)
        self.assertEqual(statuses[:5].count(429), 0)
        self.assertEqual(statuses[5], 429)


class ProfileTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        reg = _register(self.client, email="alice@example.com")
        self.access = reg.data["data"]["access"]
        self.auth_header = {"HTTP_AUTHORIZATION": f"Bearer {self.access}"}

    def test_get_profile_returns_full_details_excluding_password(self):
        response = self.client.get("/api/accounts/me/", **self.auth_header)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["email"], "alice@example.com")
        self.assertNotIn("password", response.data["data"])

    def test_patch_profile_updates_editable_fields(self):
        response = self.client.patch(
            "/api/accounts/me/",
            {"full_name": "Alice Doe", "phone_number": "+1234567890", "bio": "Hi there"},
            format="json",
            **self.auth_header,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["full_name"], "Alice Doe")
        self.assertEqual(response.data["data"]["bio"], "Hi there")

    def test_patch_profile_ignores_email_and_protected_fields(self):
        response = self.client.patch(
            "/api/accounts/me/",
            {"email": "hacked@example.com", "is_staff": True},
            format="json",
            **self.auth_header,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["email"], "alice@example.com")

    def test_other_user_cannot_view_or_edit_my_profile(self):
        reg2 = _register(self.client, email="bob@example.com")
        bob_access = reg2.data["data"]["access"]
        response = self.client.get(
            "/api/accounts/me/", HTTP_AUTHORIZATION=f"Bearer {bob_access}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["email"], "bob@example.com")
        self.assertNotEqual(response.data["data"]["email"], "alice@example.com")


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class ProfileImageTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        reg = _register(self.client, email="alice@example.com")
        self.access = reg.data["data"]["access"]
        self.auth_header = {"HTTP_AUTHORIZATION": f"Bearer {self.access}"}

    def test_upload_valid_image_succeeds(self):
        response = self.client.post(
            "/api/accounts/profile-image/",
            {"image": _png_upload()},
            format="multipart",
            **self.auth_header,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertIsNotNone(response.data["data"]["profile_image"])

    def test_upload_unsupported_format_rejected(self):
        bad_file = SimpleUploadedFile(
            "doc.txt", b"not an image", content_type="text/plain"
        )
        response = self.client.post(
            "/api/accounts/profile-image/",
            {"image": bad_file},
            format="multipart",
            **self.auth_header,
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data["success"])

    def test_remove_profile_image_clears_photo(self):
        self.client.post(
            "/api/accounts/profile-image/",
            {"image": _png_upload()},
            format="multipart",
            **self.auth_header,
        )
        response = self.client.delete("/api/accounts/profile-image/", **self.auth_header)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["data"]["profile_image"])


class ChangePasswordTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        reg = _register(self.client, email="alice@example.com")
        self.access = reg.data["data"]["access"]
        self.auth_header = {"HTTP_AUTHORIZATION": f"Bearer {self.access}"}

    def test_change_password_success(self):
        response = self.client.post(
            "/api/accounts/change-password/",
            {
                "old_password": VALID_PASSWORD,
                "new_password": "EvenStr0nger1",
                "new_password_confirm": "EvenStr0nger1",
            },
            format="json",
            **self.auth_header,
        )
        self.assertEqual(response.status_code, 200)

        old_login = self.client.post(
            "/api/accounts/login/",
            {"email": "alice@example.com", "password": VALID_PASSWORD},
            format="json",
        )
        self.assertEqual(old_login.status_code, 401)

        new_login = self.client.post(
            "/api/accounts/login/",
            {"email": "alice@example.com", "password": "EvenStr0nger1"},
            format="json",
        )
        self.assertEqual(new_login.status_code, 200)

    def test_change_password_wrong_old_password_rejected(self):
        response = self.client.post(
            "/api/accounts/change-password/",
            {
                "old_password": "WrongOld1",
                "new_password": "EvenStr0nger1",
                "new_password_confirm": "EvenStr0nger1",
            },
            format="json",
            **self.auth_header,
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data["success"])


class PasswordResetTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        _register(self.client, email="alice@example.com")
        self.user = User.objects.get(email="alice@example.com")

    @patch("accounts.views.send_password_reset_email")
    def test_forgot_password_always_returns_success(self, mock_send):
        response = self.client.post(
            "/api/accounts/forgot-password/",
            {"email": "alice@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertTrue(mock_send.called)

        response_unknown = self.client.post(
            "/api/accounts/forgot-password/",
            {"email": "nobody@example.com"},
            format="json",
        )
        self.assertEqual(response_unknown.status_code, 200)
        self.assertTrue(response_unknown.data["success"])

    @patch("accounts.views.send_password_reset_email")
    def test_reset_password_flow(self, mock_send):
        self.client.post(
            "/api/accounts/forgot-password/",
            {"email": "alice@example.com"},
            format="json",
        )
        token = PasswordResetToken.objects.filter(user=self.user).latest("created_at")

        verify_response = self.client.post(
            "/api/accounts/verify-reset-token/",
            {"token": token.token},
            format="json",
        )
        self.assertEqual(verify_response.status_code, 200)
        self.assertTrue(verify_response.data["data"]["valid"])

        reset_response = self.client.post(
            "/api/accounts/reset-password/",
            {
                "token": token.token,
                "new_password": "ResetPass1",
                "new_password_confirm": "ResetPass1",
            },
            format="json",
        )
        self.assertEqual(reset_response.status_code, 200)

        reuse_response = self.client.post(
            "/api/accounts/reset-password/",
            {
                "token": token.token,
                "new_password": "AnotherPass1",
                "new_password_confirm": "AnotherPass1",
            },
            format="json",
        )
        self.assertEqual(reuse_response.status_code, 400)

    def test_reset_password_invalid_token_rejected(self):
        response = self.client.post(
            "/api/accounts/reset-password/",
            {
                "token": "not-a-real-token",
                "new_password": "ResetPass1",
                "new_password_confirm": "ResetPass1",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data["success"])

    @patch("accounts.views.send_password_reset_email")
    def test_forgot_password_throttled_after_three_attempts(self, mock_send):
        statuses = []
        for _ in range(4):
            response = self.client.post(
                "/api/accounts/forgot-password/",
                {"email": "alice@example.com"},
                format="json",
            )
            statuses.append(response.status_code)
        self.assertEqual(statuses[:3].count(429), 0)
        self.assertEqual(statuses[3], 429)

    @patch("accounts.views.send_password_reset_email")
    def test_verify_reset_token_throttled_after_five_attempts(self, mock_send):
        statuses = []
        for _ in range(6):
            response = self.client.post(
                "/api/accounts/verify-reset-token/",
                {"token": "irrelevant"},
                format="json",
            )
            statuses.append(response.status_code)
        self.assertEqual(statuses[:5].count(429), 0)
        self.assertEqual(statuses[5], 429)


class DeleteAccountTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        reg = _register(self.client, email="alice@example.com")
        self.access = reg.data["data"]["access"]
        self.auth_header = {"HTTP_AUTHORIZATION": f"Bearer {self.access}"}

    def test_authenticated_deletion_removes_account(self):
        response = self.client.delete("/api/accounts/delete-account/", **self.auth_header)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email="alice@example.com").exists())

        login_response = self.client.post(
            "/api/accounts/login/",
            {"email": "alice@example.com", "password": VALID_PASSWORD},
            format="json",
        )
        self.assertEqual(login_response.status_code, 401)

    def test_unauthenticated_deletion_rejected(self):
        response = self.client.delete("/api/accounts/delete-account/")
        self.assertEqual(response.status_code, 401)
        self.assertTrue(User.objects.filter(email="alice@example.com").exists())


class EmailVerificationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        reg = _register(self.client, email="alice@example.com")
        self.access = reg.data["data"]["access"]
        self.auth_header = {"HTTP_AUTHORIZATION": f"Bearer {self.access}"}
        self.user = User.objects.get(email="alice@example.com")

    @patch("accounts.views.send_verification_email")
    def test_send_verification_email_issues_token(self, mock_send):
        response = self.client.post(
            "/api/accounts/send-verification-email/", **self.auth_header
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertTrue(
            EmailVerificationToken.objects.filter(user=self.user).exists()
        )
        self.assertTrue(mock_send.called)

    @patch("accounts.views.send_verification_email")
    def test_send_verification_email_already_verified_graceful(self, mock_send):
        self.user.is_verified = True
        self.user.save(update_fields=["is_verified"])
        response = self.client.post(
            "/api/accounts/send-verification-email/", **self.auth_header
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])

    @patch("accounts.views.send_verification_email")
    def test_send_verification_email_throttled_after_three_attempts(self, mock_send):
        statuses = []
        for _ in range(4):
            response = self.client.post(
                "/api/accounts/send-verification-email/", **self.auth_header
            )
            statuses.append(response.status_code)
        self.assertEqual(statuses[:3].count(429), 0)
        self.assertEqual(statuses[3], 429)

    @patch("accounts.views.send_verification_email")
    def test_verify_email_with_valid_token_marks_verified(self, mock_send):
        self.client.post("/api/accounts/send-verification-email/", **self.auth_header)
        token = EmailVerificationToken.objects.filter(user=self.user).latest(
            "created_at"
        )
        response = self.client.post(
            "/api/accounts/verify-email/",
            {"token": token.token},
            format="json",
            **self.auth_header,
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_verified)

    def test_verify_email_with_invalid_token_rejected(self):
        response = self.client.post(
            "/api/accounts/verify-email/",
            {"token": "not-a-real-token"},
            format="json",
            **self.auth_header,
        )
        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_verified)
