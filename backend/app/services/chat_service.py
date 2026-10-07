from collections.abc import AsyncIterator

from backend.app.core.config import settings
from backend.app.services.llm.factory import get_llm_provider
from backend.app.services.llm.model_router import is_reasoning_model


def _prepare(
    message: str, history: list[dict[str, str]] | None, model: str | None
) -> tuple[str, list[dict[str, str]], int | None]:
    history = list(history or [])
    if not settings.CHAT_SYSTEM_PROMPT:
        return message, history, None
    if is_reasoning_model(model):
        # DeepSeek-R1 style models answer badly (even gibberish, measured) with a system
        # prompt; their guidance is to put instructions into the user message instead.
        return f"{settings.CHAT_SYSTEM_PROMPT}\n\n{message}", history, settings.REASONING_MAX_TOKENS
    return message, [{"role": "system", "content": settings.CHAT_SYSTEM_PROMPT}, *history], None


async def get_chat_response(
    message: str,
    model: str | None = None,
    history: list[dict[str, str]] | None = None,
) -> str:
    message, history, max_tokens = _prepare(message, history, model)
    provider = get_llm_provider(model=model, max_tokens=max_tokens)
    return await provider.chat(message, history=history)


async def stream_chat_response(
    message: str,
    model: str | None = None,
    history: list[dict[str, str]] | None = None,
) -> AsyncIterator[str]:
    message, history, max_tokens = _prepare(message, history, model)
    provider = get_llm_provider(model=model, max_tokens=max_tokens)
    async for token in provider.chat_stream(message, history=history):
        yield token
