# therapist/admin.py
from django.contrib import admin
from .models import MoodEntry


@admin.register(MoodEntry)
class MoodEntryAdmin(admin.ModelAdmin):
    list_display = ("emoji", "thoughts", "ai_response", "created_at")
    search_fields = ("thoughts", "ai_response")
