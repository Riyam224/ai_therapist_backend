from rest_framework import serializers
from .models import MoodEntry


class MoodEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = MoodEntry
        fields = ["id", "emoji", "thoughts", "ai_response", "created_at"]
