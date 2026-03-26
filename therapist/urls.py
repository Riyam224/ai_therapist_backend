from django.urls import path
from .views import ai_therapist


urlpatterns = [
    path("", ai_therapist, name="ai_therapist"),
    # ← هكذا "" لتكون /api/therapist/ صحيحة
    path("generate/", ai_therapist, name="ai-generate"),
]
