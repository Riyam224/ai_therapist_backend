# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework import status
# from .ai_model import generate_ai_response
# from .models import MoodEntry
# from .serializers import MoodEntrySerializer
# from drf_spectacular.utils import (
#     extend_schema,
#     OpenApiExample,
#     OpenApiResponse,
# )


# class GenerateResponseAPIView(APIView):
#     def post(self, request):
#         emoji = request.data.get("emoji")
#         thoughts = request.data.get("thoughts")

#         if not emoji or not thoughts:
#             return Response({"error": "emoji and thoughts required"}, status=400)

#         ai_reply = generate_ai_response(emoji, thoughts)

#         entry = MoodEntry.objects.create(
#             emoji=emoji, thoughts=thoughts, ai_response=ai_reply
#         )

#         serializer = MoodEntrySerializer(entry)
#         return Response(serializer.data, status=200)


# class AllHistoryAPIView(APIView):
#     def get(self, request):
#         entries = MoodEntry.objects.all().order_by("-created_at")
#         serializer = MoodEntrySerializer(entries, many=True)
#         return Response(serializer.data)


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import (
    extend_schema,
    OpenApiExample,
    OpenApiResponse,
)
from .ai_model import generate_ai_response
from .models import MoodEntry
from .serializers import MoodEntrySerializer


class GenerateResponseAPIView(APIView):

    @extend_schema(
        tags=["Therapist"],
        summary="Generate AI response",
        description="""
Send an emoji and your thoughts to Luna (AI Therapist).
Luna will respond with an empathetic, supportive message.

The entry is automatically saved to your journal history.
        """,
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "emoji": {"type": "string", "example": "😔"},
                    "thoughts": {
                        "type": "string",
                        "example": "I feel overwhelmed lately",
                    },
                },
                "required": ["emoji", "thoughts"],
            }
        },
        responses={
            200: MoodEntrySerializer,
            400: OpenApiResponse(description="Missing emoji or thoughts"),
        },
        examples=[
            OpenApiExample(
                "Overwhelmed example",
                value={
                    "emoji": "😔",
                    "thoughts": "I feel very overwhelmed with everything lately",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Happy example",
                value={
                    "emoji": "😊",
                    "thoughts": "I feel happy and grateful today!",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Anxious example",
                value={
                    "emoji": "😰",
                    "thoughts": "I am anxious about my future career",
                },
                request_only=True,
            ),
        ],
    )
    def post(self, request):
        emoji = request.data.get("emoji")
        thoughts = request.data.get("thoughts")

        if not emoji or not thoughts:
            return Response(
                {"error": "emoji and thoughts are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ai_reply = generate_ai_response(emoji, thoughts)

        entry = MoodEntry.objects.create(
            emoji=emoji,
            thoughts=thoughts,
            ai_response=ai_reply,
        )

        return Response(MoodEntrySerializer(entry).data, status=status.HTTP_200_OK)


class AllHistoryAPIView(APIView):

    @extend_schema(
        tags=["Therapist"],
        summary="Get mood history",
        description="""
Returns all saved mood journal entries, ordered by most recent first.

Each entry contains:
- **emoji** — the mood emoji selected by the user
- **thoughts** — what the user shared
- **ai_response** — Luna's empathetic response
- **created_at** — timestamp of the entry
        """,
        responses={200: MoodEntrySerializer(many=True)},
        examples=[
            OpenApiExample(
                "History response",
                value=[
                    {
                        "id": 1,
                        "emoji": "😔",
                        "thoughts": "I feel overwhelmed",
                        "ai_response": "It sounds like you are carrying a lot right now...",
                        "created_at": "2026-03-27T12:00:00Z",
                    },
                    {
                        "id": 2,
                        "emoji": "😊",
                        "thoughts": "Feeling grateful today",
                        "ai_response": "That is beautiful! Gratitude is a powerful...",
                        "created_at": "2026-03-26T09:30:00Z",
                    },
                ],
                response_only=True,
            ),
        ],
    )
    def get(self, request):
        entries = MoodEntry.objects.all().order_by("-created_at")
        return Response(MoodEntrySerializer(entries, many=True).data)
