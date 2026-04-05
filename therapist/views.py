from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import (
    extend_schema,
    OpenApiExample,
    OpenApiResponse,
)
from .ai_model import generate_ai_response
from .serializers import MoodEntrySerializer
from datetime import datetime, timedelta
from django.conf import settings


from drf_spectacular.utils import extend_schema, OpenApiResponse
from django.utils import timezone
from .models import MoodEntry
import requests as http_requests


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


# class WeeklyLetterAPIView(APIView):

#     @extend_schema(
#         tags=["Therapist"],
#         summary="Get Luna's weekly letter",
#         description="Generates a personal weekly letter from Luna based on recent entries.",
#         responses={200: OpenApiResponse(description="Weekly letter")},
#     )
#     def post(self, request):
#         week_start = datetime.now() - timedelta(days=7)
#         week_end = datetime.now()

#         # get last 7 days entries
#         entries = MoodEntry.objects.filter(
#             created_at__gte=week_start,
#         ).order_by("created_at")

#         # need at least 2 entries
#         if entries.count() < 2:
#             return Response(
#                 {"letter": None, "reason": "not_enough_entries"},
#                 status=status.HTTP_200_OK,
#             )

#         # format for AI
#         formatted_entries = "\n".join(
#             [
#                 f"- {e.created_at.strftime('%A')}: "
#                 f"felt {e.emoji}, wrote: '{e.thoughts[:100]}'"
#                 for e in entries
#             ]
#         )

#         # dominant emoji this week
#         emoji_list = [e.emoji for e in entries]
#         dominant_emoji = max(set(emoji_list), key=emoji_list.count)

#         # call GROQ
#         import requests as http_requests

#         groq_api_key = getattr(settings, "GROQ_API_KEY", None)
#         headers = {
#             "Authorization": f"Bearer {groq_api_key}",
#             "Content-Type": "application/json",
#         }
#         payload = {
#             "model": "llama-3.1-8b-instant",
#             "messages": [
#                 {
#                     "role": "system",
#                     "content": (
#                         "You are Luna, a warm and empathetic AI journal "
#                         "companion in the MindEase app. Write a short "
#                         "personal weekly letter summarizing the emotional "
#                         "week. Your letter must:\n"
#                         '- Start with "Dear friend,"\n'
#                         "- Be 3-4 short paragraphs\n"
#                         "- Reference specific moods from the entries\n"
#                         "- Be warm, encouraging, never clinical\n"
#                         '- End with "— Luna 🌿"\n'
#                         "- Be under 200 words"
#                     ),
#                 },
#                 {
#                     "role": "user",
#                     "content": (
#                         f"Write a weekly letter based on these entries:\n\n"
#                         f"{formatted_entries}\n\n"
#                         f"Entry count: {entries.count()}\n"
#                         f"Dominant mood: {dominant_emoji}"
#                     ),
#                 },
#             ],
#         }
#         groq_response = http_requests.post(
#             "https://api.groq.com/openai/v1/chat/completions",
#             json=payload,
#             headers=headers,
#         )
#         response = groq_response.json()

#         return Response(
#             {
#                 "letter": response["choices"][0]["message"]["content"],
#                 "stats": {
#                     "entry_count": entries.count(),
#                     "dominant_emoji": dominant_emoji,
#                     "streak": entries.count(),
#                     "week_start": week_start.strftime("%Y-%m-%d"),
#                     "week_end": week_end.strftime("%Y-%m-%d"),
#                 },
#             },
#             status=status.HTTP_200_OK,
#         )


# from rest_framework.views import APIView
# from rest_framework.response import Response
# from drf_spectacular.utils import extend_schema, OpenApiResponse
# from datetime import datetime, timedelta
# from django.conf import settings
# from .models import MoodEntry
# import requests as http_requests


# class WeeklyLetterAPIView(APIView):

#     @extend_schema(
#         tags=["Therapist"],
#         summary="Get Luna's weekly letter",
#         description="Generates a personal weekly letter from Luna based on recent entries.",
#         responses={200: OpenApiResponse(description="Weekly letter")},
#     )
#     def get(self, request):
#         week_start = datetime.now() - timedelta(days=7)
#         week_end = datetime.now()

#         # get last 7 days entries
#         entries = MoodEntry.objects.filter(
#             created_at__gte=week_start,
#         ).order_by("created_at")

#         # need at least 2 entries
#         if entries.count() < 2:
#             return Response(
#                 {"letter": None, "reason": "not_enough_entries"},
#                 status=200,
#             )

#         # format for AI
#         formatted_entries = "\n".join(
#             [
#                 f"- {e.created_at.strftime('%A')}: "
#                 f"felt {e.emoji}, wrote: '{e.thoughts[:100]}'"
#                 for e in entries
#             ]
#         )

#         # dominant emoji this week
#         emoji_list = [e.emoji for e in entries]
#         dominant_emoji = max(set(emoji_list), key=emoji_list.count)

#         # call GROQ AI
#         groq_api_key = getattr(settings, "GROQ_API_KEY", None)
#         headers = {
#             "Authorization": f"Bearer {groq_api_key}",
#             "Content-Type": "application/json",
#         }
#         payload = {
#             "model": "llama-3.1-8b-instant",
#             "messages": [
#                 {
#                     "role": "system",
#                     "content": (
#                         "You are Luna, a warm and empathetic AI journal "
#                         "companion in the MindEase app. Write a short "
#                         "personal weekly letter summarizing the emotional "
#                         "week. Your letter must:\n"
#                         '- Start with "Dear friend,"\n'
#                         "- Be 3-4 short paragraphs\n"
#                         "- Reference specific moods from the entries\n"
#                         "- Be warm, encouraging, never clinical\n"
#                         '- End with "— Luna 🌿"\n'
#                         "- Be under 200 words"
#                     ),
#                 },
#                 {
#                     "role": "user",
#                     "content": (
#                         f"Write a weekly letter based on these entries:\n\n"
#                         f"{formatted_entries}\n\n"
#                         f"Entry count: {entries.count()}\n"
#                         f"Dominant mood: {dominant_emoji}"
#                     ),
#                 },
#             ],
#         }
#         groq_response = http_requests.post(
#             "https://api/groq.com/openai/v1/chat/completions",
#             json=payload,
#             headers=headers,
#         )
#         response = groq_response.json()

#         return Response(
#             {
#                 "letter": response["choices"][0]["message"]["content"],
#                 "stats": {
#                     "entry_count": entries.count(),
#                     "dominant_emoji": dominant_emoji,
#                     "streak": entries.count(),
#                     "week_start": week_start.strftime("%Y-%m-%d"),
#                     "week_end": week_end.strftime("%Y-%m-%d"),
#                 },
#             },
#             status=200,
#         )
class WeeklyLetterAPIView(APIView):

    @extend_schema(
        tags=["Therapist"],
        summary="Get Luna's weekly letter",
        description="Generates a personal weekly letter from Luna based on recent entries.",
        responses={200: OpenApiResponse(description="Weekly letter")},
    )
    def get(self, request):
        """
        GET endpoint to fetch a weekly letter from Luna.
        - Timezone-aware datetime used to fetch entries correctly.
        - Requires at least 2 entries in the last 7 days.
        """
        # Use timezone-aware datetime
        week_start = timezone.now() - timedelta(days=7)
        week_end = timezone.now()

        # Fetch last 7 days entries
        entries = MoodEntry.objects.filter(created_at__gte=week_start).order_by(
            "created_at"
        )

        # Minimum 2 entries required
        if entries.count() < 2:
            return Response(
                {"letter": None, "reason": "not_enough_entries"},
                status=200,
            )

        # Format entries for AI
        formatted_entries = "\n".join(
            [
                f"- {e.created_at.strftime('%A')}: "
                f"felt {e.emoji}, wrote: '{e.thoughts[:100]}'"
                for e in entries
            ]
        )

        # Dominant emoji
        emoji_list = [e.emoji for e in entries]
        dominant_emoji = max(set(emoji_list), key=emoji_list.count)

        # Call GROQ AI
        groq_api_key = getattr(settings, "GROQ_API_KEY", None)
        headers = {
            "Authorization": f"Bearer {groq_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are Luna, a warm and empathetic AI journal "
                        "companion in the MindEase app. Write a short "
                        "personal weekly letter summarizing the emotional "
                        "week. Your letter must:\n"
                        '- Start with "Dear friend,"\n'
                        "- Be 3-4 short paragraphs\n"
                        "- Reference specific moods from the entries\n"
                        "- Be warm, encouraging, never clinical\n"
                        '- End with "— Luna 🌿"\n'
                        "- Be under 200 words"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Write a weekly letter based on these entries:\n\n"
                        f"{formatted_entries}\n\n"
                        f"Entry count: {entries.count()}\n"
                        f"Dominant mood: {dominant_emoji}"
                    ),
                },
            ],
        }

        groq_response = http_requests.post(
            "https://api/groq.com/openai/v1/chat/completions",
            json=payload,
            headers=headers,
        )
        response = groq_response.json()

        # Return letter + stats
        return Response(
            {
                "letter": response["choices"][0]["message"]["content"],
                "stats": {
                    "entry_count": entries.count(),
                    "dominant_emoji": dominant_emoji,
                    "streak": entries.count(),
                    "week_start": week_start.strftime("%Y-%m-%d"),
                    "week_end": week_end.strftime("%Y-%m-%d"),
                },
            },
            status=200,
        )
