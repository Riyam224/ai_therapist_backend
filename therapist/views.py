from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .ai_model import generate_ai_response
from .models import MoodEntry
from .serializers import MoodEntrySerializer


class GenerateResponseAPIView(APIView):
    def post(self, request):
        emoji = request.data.get("emoji")
        thoughts = request.data.get("thoughts")

        if not emoji or not thoughts:
            return Response({"error": "emoji and thoughts required"}, status=400)

        ai_reply = generate_ai_response(emoji, thoughts)

        entry = MoodEntry.objects.create(
            emoji=emoji, thoughts=thoughts, ai_response=ai_reply
        )

        serializer = MoodEntrySerializer(entry)
        return Response(serializer.data, status=200)


class AllHistoryAPIView(APIView):
    def get(self, request):
        entries = MoodEntry.objects.all().order_by("-created_at")
        serializer = MoodEntrySerializer(entries, many=True)
        return Response(serializer.data)
