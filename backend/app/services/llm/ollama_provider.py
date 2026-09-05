from typing import Any

import httpx

from backend.app.core.config import settings
from backend.app.services.llm.base import LLMProvider


class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str | None = None, model: str | None = None):
        self.base_url = base_url or settings.OLLAMA_BASE_URL
        self.model = model or settings.OLLAMA_MODEL

    async def chat(self, message: str, history: list[dict[str, str]] | None = None) -> str:
        messages = [*(history or []), {"role": "user", "content": message}]
        message_response = await self._chat_request(messages)
        return message_response["content"]

    async def chat_with_tools(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> dict[str, Any]:
        return await self._chat_request(messages, tools=tools)

    async def _chat_request(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        if tools:
            payload["tools"] = tools

        async with httpx.AsyncClient(timeout=60.0) as client:
            result = await client.post(f"{self.base_url}/api/chat", json=payload)
            result.raise_for_status()
            data = result.json()
            return data["message"]
