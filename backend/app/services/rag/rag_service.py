import uuid

from backend.app.services.embeddings.ollama_embedder import embed_text
from backend.app.services.rag.vector_store import search, upsert_chunk

_CHUNK_SIZE_WORDS = 500


def _chunk_text(text: str, chunk_size: int = _CHUNK_SIZE_WORDS) -> list[str]:
    words = text.split()
    if not words:
        return []
    return [" ".join(words[i : i + chunk_size]) for i in range(0, len(words), chunk_size)]


async def ingest_document(text: str) -> int:
    chunks = _chunk_text(text)
    for chunk in chunks:
        vector = await embed_text(chunk)
        await upsert_chunk(str(uuid.uuid4()), vector, chunk)
    return len(chunks)


async def retrieve_context(query: str, top_k: int = 3) -> list[str]:
    vector = await embed_text(query)
    return await search(vector, top_k=top_k)
