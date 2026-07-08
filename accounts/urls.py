from django.urls import path

from .views import DeleteAccountView, MeView, VerifyFirebaseTokenView

urlpatterns = [
    path("me/", MeView.as_view(), name="me"),
    path("delete-account/", DeleteAccountView.as_view(), name="delete-account"),
    path("verify/", VerifyFirebaseTokenView.as_view(), name="verify-token"),
]
