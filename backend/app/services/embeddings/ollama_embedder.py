import httpx

from backend.app.core.config import settings


async def embed_text(text: str) -> list[float]:
    async with httpx.AsyncClient(timeout=60.0) as client:
        result = await client.post(
            f"{settings.OLLAMA_BASE_URL}/api/embeddings",
            json={"model": settings.EMBEDDING_MODEL, "prompt": text},
        )
        result.raise_for_status()
        data = result.json()
        return data["embedding"]
