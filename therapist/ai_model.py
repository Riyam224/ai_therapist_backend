import os
import requests

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

def generate_ai_response(emoji, thoughts):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a warm, supportive AI therapist. "
                    "Write a short, empathetic, modern response with kindness. "
                    "Use simple emotional language and avoid long paragraphs."
                ),
            },
            {"role": "user", "content": f"Emoji: {emoji}\nThoughts: {thoughts}"},
        ],
    }
    response = requests.post(url, json=payload, headers=headers)
    data = response.json()
    return data["choices"][0]["message"]["content"]