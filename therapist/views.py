from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .ai_model import generate_support_message
from .models import MoodEntry
from .serializers import MoodEntrySerializer


@api_view(["POST", "GET"])
def ai_therapist(request):
    if request.method == "GET":
        entries = MoodEntry.objects.all().order_by("-created_at")
        serializer = MoodEntrySerializer(entries, many=True)
        return Response(serializer.data)

    # POST
    emoji = request.data.get("emoji")
    thoughts = request.data.get("thoughts")
    if not emoji or not thoughts:
        return Response(
            {"error": "emoji and thoughts are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        message = generate_support_message(emoji, thoughts)
        entry = MoodEntry.objects.create(
            emoji=emoji, thoughts=thoughts, ai_response=message
        )
        serializer = MoodEntrySerializer(entry)
    except Exception as e:
        return Response(
            {"error": "model generation failed", "details": str(e)}, status=500
        )

    return Response(serializer.data)
