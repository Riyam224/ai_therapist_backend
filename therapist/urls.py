from django.urls import path
from .views import GenerateResponseAPIView, AllHistoryAPIView

urlpatterns = [
    path("generate/", GenerateResponseAPIView.as_view()),
    path("history/", AllHistoryAPIView.as_view()),
]
