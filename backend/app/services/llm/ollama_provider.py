import httpx

from backend.app.core.config import settings
from backend.app.services.llm.base import LLMProvider


class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str | None = None, model: str | None = None):
        self.base_url = base_url or settings.OLLAMA_BASE_URL
        self.model = model or settings.OLLAMA_MODEL

    async def chat(self, message: str) -> str:
        async with httpx.AsyncClient(timeout=60.0) as client:
            result = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": message}],
                    "stream": False,
                },
            )
            result.raise_for_status()
            data = result.json()
            return data["message"]["content"]
