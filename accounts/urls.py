from django.urls import path

from .views import (
    ChangePasswordView,
    CustomTokenRefreshView,
    DeleteAccountView,
    ForgotPasswordView,
    LoginView,
    LogoutView,
    MeView,
    ProfileImageView,
    RegisterView,
    ResetPasswordView,
    SendVerificationEmailView,
    VerifyEmailView,
    VerifyResetTokenView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("token/refresh/", CustomTokenRefreshView.as_view(), name="token-refresh"),
    path("me/", MeView.as_view(), name="me"),
    path("profile-image/", ProfileImageView.as_view(), name="profile-image"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("delete-account/", DeleteAccountView.as_view(), name="delete-account"),
    path("forgot-password/", ForgotPasswordView.as_view(), name="forgot-password"),
    path(
        "verify-reset-token/",
        VerifyResetTokenView.as_view(),
        name="verify-reset-token",
    ),
    path("reset-password/", ResetPasswordView.as_view(), name="reset-password"),
    path(
        "send-verification-email/",
        SendVerificationEmailView.as_view(),
        name="send-verification-email",
    ),
    path("verify-email/", VerifyEmailView.as_view(), name="verify-email"),
]
