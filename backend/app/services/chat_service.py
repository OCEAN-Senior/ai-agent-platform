from collections.abc import AsyncIterator

from backend.app.services.llm.factory import get_llm_provider


async def get_chat_response(
    message: str,
    model: str | None = None,
    history: list[dict[str, str]] | None = None,
) -> str:
    provider = get_llm_provider(model=model)
    return await provider.chat(message, history=history)


async def stream_chat_response(
    message: str,
    model: str | None = None,
    history: list[dict[str, str]] | None = None,
) -> AsyncIterator[str]:
    provider = get_llm_provider(model=model)
    async for token in provider.chat_stream(message, history=history):
        yield token
