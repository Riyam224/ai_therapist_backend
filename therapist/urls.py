from django.urls import path
from .views import GenerateResponseAPIView, AllHistoryAPIView, WeeklyLetterAPIView

urlpatterns = [
    path("generate/", GenerateResponseAPIView.as_view()),
    path("history/", AllHistoryAPIView.as_view()),
    path("weekly-letter/", WeeklyLetterAPIView.as_view()),
]
