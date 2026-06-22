import logging

import firebase_admin
from django.conf import settings
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from firebase_admin import auth, credentials
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from accounts.models import User

logger = logging.getLogger(__name__)

if not firebase_admin._apps and settings.FIREBASE_CREDENTIALS_PATH:
    firebase_admin.initialize_app(
        credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
    )


class FirebaseAuthentication(BaseAuthentication):
    """Resolves request.user from a verified Firebase ID token.

    Identity comes exclusively from the verified token's `uid` claim —
    never from the request body or query parameters.
    """

    keyword = "Bearer"

    def authenticate(self, request):
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if not header.startswith(f"{self.keyword} "):
            return None
        token = header[len(self.keyword) + 1 :].strip()
        if not token:
            return None

        try:
            decoded = auth.verify_id_token(token)
        except Exception as exc:
            logger.warning("Firebase token verification failed: %s", exc)
            raise AuthenticationFailed("Invalid or expired token.")

        uid = decoded["uid"]
        # Firebase users without an email (phone/anonymous sign-in) would
        # otherwise collide on User.email's unique constraint once a second
        # such user is created with email="".
        email = decoded.get("email") or f"{uid}@firebase.local"

        user, _ = User.objects.get_or_create(
            firebase_uid=uid,
            defaults={"email": email, "username": uid},
        )
        return (user, None)

    def authenticate_header(self, request):
        return self.keyword


class FirebaseAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "core.firebase_auth.FirebaseAuthentication"
    name = "FirebaseAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "Firebase ID token",
        }
