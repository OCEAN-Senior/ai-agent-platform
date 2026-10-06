from collections.abc import AsyncIterator

from backend.app.core.config import settings
from backend.app.services.llm.factory import get_llm_provider


def _with_system_prompt(history: list[dict[str, str]] | None) -> list[dict[str, str]]:
    if not settings.CHAT_SYSTEM_PROMPT:
        return list(history or [])
    return [{"role": "system", "content": settings.CHAT_SYSTEM_PROMPT}, *(history or [])]


async def get_chat_response(
    message: str,
    model: str | None = None,
    history: list[dict[str, str]] | None = None,
) -> str:
    provider = get_llm_provider(model=model)
    return await provider.chat(message, history=_with_system_prompt(history))


async def stream_chat_response(
    message: str,
    model: str | None = None,
    history: list[dict[str, str]] | None = None,
) -> AsyncIterator[str]:
    provider = get_llm_provider(model=model)
    async for token in provider.chat_stream(message, history=_with_system_prompt(history)):
        yield token
