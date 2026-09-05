from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from backend.app.core.config import settings

_NOMIC_EMBED_TEXT_SIZE = 768

_client = AsyncQdrantClient(url=settings.QDRANT_URL)


async def _ensure_collection() -> None:
    collections = (await _client.get_collections()).collections
    if not any(c.name == settings.QDRANT_COLLECTION for c in collections):
        await _client.create_collection(
            collection_name=settings.QDRANT_COLLECTION,
            vectors_config=VectorParams(size=_NOMIC_EMBED_TEXT_SIZE, distance=Distance.COSINE),
        )


async def upsert_chunk(chunk_id: str, vector: list[float], text: str) -> None:
    await _ensure_collection()
    await _client.upsert(
        collection_name=settings.QDRANT_COLLECTION,
        points=[PointStruct(id=chunk_id, vector=vector, payload={"text": text})],
    )


async def search(vector: list[float], top_k: int = 3) -> list[str]:
    await _ensure_collection()
    response = await _client.query_points(
        collection_name=settings.QDRANT_COLLECTION,
        query=vector,
        limit=top_k,
    )
    return [point.payload["text"] for point in response.points if point.payload]
