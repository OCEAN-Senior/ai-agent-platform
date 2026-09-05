from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any


class LLMProvider(ABC):
    @abstractmethod
    async def chat(self, message: str, history: list[dict[str, str]] | None = None) -> str:
        """Send a message (with optional prior turns) to the LLM and return its text response."""

    async def chat_with_tools(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Send a raw message list plus tool schemas; return the raw assistant message.

        Not every provider supports tool calling, so this has a default that raises
        rather than being abstract.
        """
        raise NotImplementedError(f"{type(self).__name__} does not support tool calling yet.")

    async def chat_stream(
        self, message: str, history: list[dict[str, str]] | None = None
    ) -> AsyncIterator[str]:
        """Yield response text incrementally instead of returning it all at once.

        Not every provider supports streaming, so this has a default that raises
        rather than being abstract.
        """
        raise NotImplementedError(f"{type(self).__name__} does not support streaming yet.")
        yield ""  # pragma: no cover -- makes this an async generator for the type checker
