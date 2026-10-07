"""Pick the local model for a chat message: reasoning model for numbers/logic, chat model otherwise.

Rule-based on purpose (no extra model call, instant, testable). Measured on our questions:
the Uzbek-tuned chat model got 0/3 calculation/table/logic questions right, DeepSeek-R1 8B 2/3,
while the Uzbek model writes somewhat better Uzbek prose.
"""
import re

from backend.app.core.config import settings

_APOS = "'’ʻʼ`‘"
_A = f"[{_APOS}]?"

# Arithmetic written out: "47*89", "120 + 85", "4500/3", "15%".
_EXPRESSION = re.compile(r"\d\s*[-+*/×÷^]\s*\d|\d\s*%")
# Words that ask for a calculation, count, comparison or aggregate (Uzbek Latin/Cyrillic + English).
_CALC_WORDS = re.compile(
    rf"\b(hisobla\w*|hisob-kitob\w*|nechta|necha|qancha|jami|umumiy|foiz\w*|o{_A}rtacha\w*|"
    rf"ko{_A}paytir\w*|qo{_A}sh\w*|ayir\w*|bo{_A}l(?:ing|ib|sak)\w*|taqqosla\w*|solishtir\w*|"
    rf"farq\w*|ulush\w*|nisbat\w*|tenglama\w*|masala\w*|eng\s+(?:ko{_A}p|kam|katta|kichik)\w*|"
    rf"ҳисобла\w*|нечта|неча|қанча|жами|фоиз\w*|ўртача\w*|"
    rf"calculate|compute|how\s+many|how\s+much|total|average|percent\w*|sum)\b",
    re.IGNORECASE,
)
# Logic / reasoning puzzles.
_LOGIC = re.compile(
    rf"\b(mantiq\w*|isbotla\w*|xulosa\s+chiqar\w*|kim\s+(?:katta|kichik)|eng\s+kichig\w*|eng\s+katta\w*|"
    rf"мантиқ\w*|logic\w*|puzzle|prove)\b",
    re.IGNORECASE,
)
_DIGIT = re.compile(r"\d")
_SPREADSHEET_MARK = "[Yuklangan jadval:"


def needs_reasoning(message: str, history: list[dict[str, str]] | None = None) -> bool:
    if _EXPRESSION.search(message) or _LOGIC.search(message):
        return True
    if _CALC_WORDS.search(message):
        recent = history[-6:] if history else []
        table_in_context = any(_SPREADSHEET_MARK in (m.get("content") or "") for m in recent)
        return bool(_DIGIT.search(message)) or table_in_context
    return False


def choose_model(message: str, history: list[dict[str, str]] | None = None) -> str | None:
    """Model override for this message, or None for the default chat model."""
    if settings.REASONING_MODEL and needs_reasoning(message, history):
        return settings.REASONING_MODEL
    return None


def is_reasoning_model(model: str | None) -> bool:
    return bool(model) and model == settings.REASONING_MODEL
