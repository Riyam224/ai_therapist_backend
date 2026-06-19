from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import User
from .validators import (
    validate_password_strength,
    validate_phone_number,
    validate_profile_image,
)


def _validate_password(value):
    try:
        validate_password_strength(value)
    except DjangoValidationError as exc:
        raise serializers.ValidationError(exc.messages)
    return value


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "username",
            "full_name",
            "phone_number",
            "bio",
            "date_of_birth",
            "gender",
            "profile_image",
            "is_verified",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    username = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "An account with this email already exists."
            )
        return value

    def validate_username(self, value):
        if value and User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("This username is already taken.")
        return value

    def validate_password(self, value):
        return _validate_password(value)

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        username = validated_data.pop("username", None) or None
        return User.objects.create_user(username=username, **validated_data)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("full_name", "phone_number", "bio", "date_of_birth", "gender")

    def validate_phone_number(self, value):
        try:
            validate_phone_number(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages)
        return value


class ProfileImageSerializer(serializers.Serializer):
    image = serializers.ImageField()

    def validate_image(self, value):
        try:
            validate_profile_image(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages)
        return value


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    new_password_confirm = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Incorrect current password.")
        return value

    def validate_new_password(self, value):
        return _validate_password(value)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "Passwords do not match."}
            )
        return attrs


class VerifyEmailSerializer(serializers.Serializer):
    token = serializers.CharField()


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class VerifyResetTokenSerializer(serializers.Serializer):
    token = serializers.CharField()


class ResetPasswordSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)
    new_password_confirm = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        return _validate_password(value)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "Passwords do not match."}
            )
        return attrs
