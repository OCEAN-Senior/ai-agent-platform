import httpx

from backend.app.core.config import settings


async def generate_chat_response(message: str) -> str:
    async with httpx.AsyncClient(timeout=60.0) as client:
        result = await client.post(
            f"{settings.OLLAMA_BASE_URL}/api/chat",
            json={
                "model": settings.OLLAMA_MODEL,
                "messages": [{"role": "user", "content": message}],
                "stream": False,
            },
        )
        result.raise_for_status()
        data = result.json()
        return data["message"]["content"]
