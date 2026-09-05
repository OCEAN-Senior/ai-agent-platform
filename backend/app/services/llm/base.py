from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    async def chat(self, message: str, history: list[dict[str, str]] | None = None) -> str:
        """Send a message (with optional prior turns) to the LLM and return its text response."""
