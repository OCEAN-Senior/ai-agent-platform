from collections.abc import Awaitable, Callable
from typing import TypeVar

import httpx
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.exceptions import ResponseHandlingException
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    FilterSelector,
    IsEmptyCondition,
    MatchValue,
    PayloadField,
    PointStruct,
    VectorParams,
)

from backend.app.core.config import settings

_NOMIC_EMBED_TEXT_SIZE = 768

_client = AsyncQdrantClient(url=settings.QDRANT_URL)

T = TypeVar("T")


async def _retry_once(call: Callable[[], Awaitable[T]]) -> T:
    """Qdrant closes idle keep-alive connections after ~5s; the first request on such a
    stale pooled connection fails with 'Server disconnected', so retry it once."""
    try:
        return await call()
    except (ResponseHandlingException, httpx.TransportError):
        return await call()


async def _ensure_collection() -> None:
    collections = (await _retry_once(_client.get_collections)).collections
    if not any(c.name == settings.QDRANT_COLLECTION for c in collections):
        await _client.create_collection(
            collection_name=settings.QDRANT_COLLECTION,
            vectors_config=VectorParams(size=_NOMIC_EMBED_TEXT_SIZE, distance=Distance.COSINE),
        )


def _owner_filter(owner: str | None) -> Filter:
    """Private documents carry an `owner` (e.g. "tg:<user id>") and are only visible to
    that owner; shared documents have no owner and are what owner-less searches see."""
    if owner:
        return Filter(must=[FieldCondition(key="owner", match=MatchValue(value=owner))])
    return Filter(must=[IsEmptyCondition(is_empty=PayloadField(key="owner"))])


async def upsert_chunk(
    chunk_id: str,
    vector: list[float],
    text: str,
    owner: str | None = None,
    source: str | None = None,
) -> None:
    await _ensure_collection()
    payload = {"text": text}
    if owner:
        payload["owner"] = owner
    if source:
        payload["source"] = source
    await _retry_once(
        lambda: _client.upsert(
            collection_name=settings.QDRANT_COLLECTION,
            points=[PointStruct(id=chunk_id, vector=vector, payload=payload)],
        )
    )


async def delete_source(owner: str | None, source: str) -> None:
    """Remove a document's old chunks so re-uploading it replaces instead of duplicating."""
    await _ensure_collection()
    flt = _owner_filter(owner)
    flt.must.append(FieldCondition(key="source", match=MatchValue(value=source)))
    await _retry_once(
        lambda: _client.delete(
            collection_name=settings.QDRANT_COLLECTION, points_selector=FilterSelector(filter=flt)
        )
    )


async def search(
    vector: list[float],
    top_k: int = 3,
    owner: str | None = None,
    min_score: float | None = None,
) -> list[str]:
    await _ensure_collection()
    response = await _retry_once(
        lambda: _client.query_points(
            collection_name=settings.QDRANT_COLLECTION,
            query=vector,
            query_filter=_owner_filter(owner),
            limit=top_k,
            score_threshold=min_score,
        )
    )
    return [point.payload["text"] for point in response.points if point.payload]
