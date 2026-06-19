from django.contrib.auth import authenticate
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from .models import User
from .serializers import (
    ChangePasswordSerializer,
    ForgotPasswordSerializer,
    LoginSerializer,
    LogoutSerializer,
    ProfileImageSerializer,
    RegisterSerializer,
    ResetPasswordSerializer,
    UserProfileUpdateSerializer,
    UserSerializer,
    VerifyEmailSerializer,
    VerifyResetTokenSerializer,
)
from .services import (
    consume_email_verification_token,
    consume_password_reset_token,
    error_response,
    get_valid_email_verification_token,
    get_valid_password_reset_token,
    issue_email_verification_token,
    issue_password_reset_token,
    send_password_reset_email,
    send_verification_email,
    success_response,
)
from .throttling import (
    ForgotPasswordAccountThrottle,
    ForgotPasswordIPThrottle,
    LoginAccountThrottle,
    LoginIPThrottle,
    RegisterAccountThrottle,
    RegisterIPThrottle,
    SendVerificationEmailUserThrottle,
    VerifyResetTokenIPThrottle,
)

TOO_MANY_ATTEMPTS = OpenApiResponse(description="Too many attempts (rate limited)")


def _tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [RegisterIPThrottle, RegisterAccountThrottle]

    @extend_schema(
        tags=["Accounts"],
        summary="Register a new account",
        description="Creates an account and immediately returns access/refresh tokens.",
        request=RegisterSerializer,
        responses={
            201: OpenApiResponse(description="Registration successful"),
            400: OpenApiResponse(description="Validation failed (e.g. duplicate email, weak password)"),
            429: TOO_MANY_ATTEMPTS,
        },
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                error_response("Validation failed.", serializer.errors),
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = serializer.save()
        tokens = _tokens_for_user(user)
        return Response(
            success_response(
                "Registration successful.",
                {"user": UserSerializer(user).data, **tokens},
            ),
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginIPThrottle, LoginAccountThrottle]

    @extend_schema(
        tags=["Accounts"],
        summary="Sign in",
        description="Authenticates with email + password and returns access/refresh tokens.",
        request=LoginSerializer,
        responses={
            200: OpenApiResponse(description="Login successful"),
            401: OpenApiResponse(description="Invalid email or password"),
            429: TOO_MANY_ATTEMPTS,
        },
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                error_response("Validation failed.", serializer.errors),
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = authenticate(
            request,
            username=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )
        if user is None:
            return Response(
                error_response("Invalid email or password."),
                status=status.HTTP_401_UNAUTHORIZED,
            )
        tokens = _tokens_for_user(user)
        return Response(
            success_response(
                "Login successful.",
                {"user": UserSerializer(user).data, **tokens},
            ),
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Accounts"],
        summary="Sign out",
        description="Blacklists the supplied refresh token. Requires authentication.",
        request=LogoutSerializer,
        responses={
            200: OpenApiResponse(description="Logged out successfully"),
            400: OpenApiResponse(description="Invalid or expired refresh token"),
            401: OpenApiResponse(description="Authentication required"),
        },
    )
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                error_response("Validation failed.", serializer.errors),
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(serializer.validated_data["refresh"])
            token.blacklist()
        except TokenError:
            return Response(
                error_response("Invalid or expired refresh token."),
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            success_response("Logged out successfully."), status=status.HTTP_200_OK
        )


class CustomTokenRefreshView(TokenRefreshView):
    @extend_schema(
        tags=["Accounts"],
        summary="Refresh access token",
        description="Exchanges a valid refresh token for a new access token.",
        responses={
            200: OpenApiResponse(description="Token refreshed"),
            401: OpenApiResponse(description="Refresh token invalid or expired"),
        },
    )
    def post(self, request, *args, **kwargs):
        try:
            response = super().post(request, *args, **kwargs)
        except InvalidToken:
            return Response(
                error_response("Refresh token invalid or expired."),
                status=status.HTTP_401_UNAUTHORIZED,
            )
        return Response(
            success_response("Token refreshed.", response.data),
            status=status.HTTP_200_OK,
        )


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Accounts"],
        summary="Get current user's profile",
        responses={200: UserSerializer},
    )
    def get(self, request):
        return Response(
            success_response(
                "Profile retrieved.", UserSerializer(request.user).data
            )
        )

    @extend_schema(
        tags=["Accounts"],
        summary="Update current user's profile",
        description="Updates editable profile fields only. Email and account-identifying fields are not editable here.",
        request=UserProfileUpdateSerializer,
        responses={
            200: UserSerializer,
            400: OpenApiResponse(description="Validation failed"),
        },
    )
    def patch(self, request):
        serializer = UserProfileUpdateSerializer(
            request.user, data=request.data, partial=True
        )
        if not serializer.is_valid():
            return Response(
                error_response("Validation failed.", serializer.errors),
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer.save()
        return Response(
            success_response(
                "Profile updated.", UserSerializer(request.user).data
            )
        )


class ProfileImageView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Accounts"],
        summary="Upload profile image",
        description="Accepts multipart/form-data. Allowed formats: JPG, JPEG, PNG, WEBP. Max size: 5 MB.",
        request=ProfileImageSerializer,
        responses={
            200: OpenApiResponse(description="Profile image updated"),
            400: OpenApiResponse(description="Unsupported format or file too large"),
        },
    )
    def post(self, request):
        serializer = ProfileImageSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                error_response("Validation failed.", serializer.errors),
                status=status.HTTP_400_BAD_REQUEST,
            )
        request.user.profile_image = serializer.validated_data["image"]
        request.user.save(update_fields=["profile_image"])
        return Response(
            success_response(
                "Profile image updated.",
                {"profile_image": request.user.profile_image.url},
            )
        )

    @extend_schema(
        tags=["Accounts"],
        summary="Remove profile image",
        responses={200: OpenApiResponse(description="Profile image removed")},
    )
    def delete(self, request):
        request.user.profile_image.delete(save=False)
        request.user.profile_image = None
        request.user.save(update_fields=["profile_image"])
        return Response(
            success_response("Profile image removed.", {"profile_image": None})
        )


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Accounts"],
        summary="Change password",
        request=ChangePasswordSerializer,
        responses={
            200: OpenApiResponse(description="Password changed successfully"),
            400: OpenApiResponse(description="Incorrect current password or weak new password"),
        },
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(
                error_response("Validation failed.", serializer.errors),
                status=status.HTTP_400_BAD_REQUEST,
            )
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])
        return Response(success_response("Password changed successfully."))


class DeleteAccountView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Accounts"],
        summary="Permanently delete account",
        description="Deletes the authenticated user's account. Owner-only; no request body.",
        responses={200: OpenApiResponse(description="Account deleted permanently")},
    )
    def delete(self, request):
        request.user.delete()
        return Response(success_response("Account deleted permanently."))


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ForgotPasswordIPThrottle, ForgotPasswordAccountThrottle]

    @extend_schema(
        tags=["Accounts"],
        summary="Request password reset",
        description="Always returns success regardless of whether the email is registered (no account-existence disclosure).",
        request=ForgotPasswordSerializer,
        responses={
            200: OpenApiResponse(description="Reset email sent (or silently no-op)"),
            429: TOO_MANY_ATTEMPTS,
        },
    )
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                error_response("Validation failed.", serializer.errors),
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = User.objects.filter(
            email__iexact=serializer.validated_data["email"]
        ).first()
        if user is not None:
            token = issue_password_reset_token(user)
            send_password_reset_email(user, token.token)
        return Response(
            success_response(
                "If an account exists for this email, a reset link has been sent."
            )
        )


class VerifyResetTokenView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [VerifyResetTokenIPThrottle]

    @extend_schema(
        tags=["Accounts"],
        summary="Verify a password-reset token",
        request=VerifyResetTokenSerializer,
        responses={
            200: OpenApiResponse(description="Token is valid"),
            400: OpenApiResponse(description="Invalid or expired token"),
            429: TOO_MANY_ATTEMPTS,
        },
    )
    def post(self, request):
        serializer = VerifyResetTokenSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                error_response("Validation failed.", serializer.errors),
                status=status.HTTP_400_BAD_REQUEST,
            )
        token = get_valid_password_reset_token(serializer.validated_data["token"])
        if token is None:
            return Response(
                error_response("Invalid or expired token."),
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(success_response("Token is valid.", {"valid": True}))


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Accounts"],
        summary="Reset password with a valid token",
        request=ResetPasswordSerializer,
        responses={
            200: OpenApiResponse(description="Password reset successfully"),
            400: OpenApiResponse(description="Invalid/expired token or weak new password"),
        },
    )
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                error_response("Validation failed.", serializer.errors),
                status=status.HTTP_400_BAD_REQUEST,
            )
        token = get_valid_password_reset_token(serializer.validated_data["token"])
        if token is None:
            return Response(
                error_response("Invalid or expired token."),
                status=status.HTTP_400_BAD_REQUEST,
            )
        token.user.set_password(serializer.validated_data["new_password"])
        token.user.save(update_fields=["password"])
        consume_password_reset_token(token)
        return Response(success_response("Password reset successfully."))


class SendVerificationEmailView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [SendVerificationEmailUserThrottle]

    @extend_schema(
        tags=["Accounts"],
        summary="Send email verification message",
        description="Issues a verification token for the authenticated user. No-ops gracefully if already verified.",
        request=None,
        responses={
            200: OpenApiResponse(description="Verification email sent (or already verified)"),
            429: TOO_MANY_ATTEMPTS,
        },
    )
    def post(self, request):
        if request.user.is_verified:
            return Response(success_response("Account is already verified."))
        token = issue_email_verification_token(request.user)
        send_verification_email(request.user, token.token)
        return Response(success_response("Verification email sent."))


class VerifyEmailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Accounts"],
        summary="Verify email with token",
        request=VerifyEmailSerializer,
        responses={
            200: OpenApiResponse(description="Email verified successfully"),
            400: OpenApiResponse(description="Invalid or expired verification token"),
        },
    )
    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                error_response("Validation failed.", serializer.errors),
                status=status.HTTP_400_BAD_REQUEST,
            )
        token = get_valid_email_verification_token(
            serializer.validated_data["token"]
        )
        if token is None or token.user_id != request.user.id:
            return Response(
                error_response("Invalid or expired verification token."),
                status=status.HTTP_400_BAD_REQUEST,
            )
        consume_email_verification_token(token)
        return Response(success_response("Email verified successfully."))
