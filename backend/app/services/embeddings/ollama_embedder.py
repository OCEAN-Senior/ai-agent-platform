from typing import Literal

import httpx

from backend.app.core.config import settings


async def embed_text(text: str, kind: Literal["document", "query"] = "document") -> list[float]:
    # nomic-embed-text is trained with task prefixes; without them document/query
    # similarities are noticeably less discriminative.
    if settings.EMBEDDING_MODEL.startswith("nomic-embed-text"):
        text = f"search_{kind}: {text}"
    async with httpx.AsyncClient(timeout=60.0) as client:
        result = await client.post(
            f"{settings.OLLAMA_BASE_URL}/api/embeddings",
            json={"model": settings.EMBEDDING_MODEL, "prompt": text},
        )
        result.raise_for_status()
        data = result.json()
        return data["embedding"]
