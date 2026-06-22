import logging

from drf_spectacular.utils import OpenApiResponse, extend_schema
from firebase_admin import auth as firebase_auth_admin
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import UserProfileUpdateSerializer, UserSerializer
from .services import error_response, success_response

logger = logging.getLogger(__name__)


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
        description="Updates editable profile fields only. Identity-bearing fields are not editable here.",
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


class DeleteAccountView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Accounts"],
        summary="Permanently delete account",
        description="Deletes the authenticated user's Firebase identity and local account. Owner-only; no request body.",
        responses={
            200: OpenApiResponse(description="Account deleted permanently"),
            502: OpenApiResponse(description="Firebase identity deletion failed"),
        },
    )
    def delete(self, request):
        user = request.user
        if user.firebase_uid:
            try:
                firebase_auth_admin.delete_user(user.firebase_uid)
            except Exception as exc:
                logger.error(
                    "Firebase delete_user failed for uid=%s: %s",
                    user.firebase_uid,
                    exc,
                )
                return Response(
                    error_response(
                        "Failed to delete Firebase identity. Account not deleted."
                    ),
                    status=status.HTTP_502_BAD_GATEWAY,
                )
        user.delete()
        return Response(success_response("Account deleted permanently."))
