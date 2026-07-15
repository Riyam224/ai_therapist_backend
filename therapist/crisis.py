import re

CRISIS_KEYWORDS = [
    "kill myself", "suicide", "end my life", "want to die",
    "hurt myself", "self harm", "self-harm", "no reason to live",
    "better off dead", "can't go on", "ending it all",
]
_CRISIS_PATTERN = re.compile(r"|".join(re.escape(k) for k in CRISIS_KEYWORDS), re.IGNORECASE)

CRISIS_RESPONSE = (
    "It sounds like you're carrying something really heavy right now, and I "
    "don't want you to carry it alone. I'm not able to give crisis support "
    "myself, but real people can help right away:\n\n"
    "• US: call or text 988 (Suicide & Crisis Lifeline)\n"
    "• Outside the US: https://findahelpline.com\n\n"
    "If you're in immediate danger, please contact local emergency services. "
    "I'll be right here whenever you want to talk more."
)


def contains_crisis_language(text: str) -> bool:
    return bool(text) and bool(_CRISIS_PATTERN.search(text))
