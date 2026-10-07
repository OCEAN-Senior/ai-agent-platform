import uuid

from backend.app.core.config import settings
from backend.app.services.embeddings.ollama_embedder import embed_text
from backend.app.services.rag.vector_store import delete_source, search, upsert_chunk

_CHUNK_SIZE_WORDS = 500


def _chunk_text(text: str, chunk_size: int = _CHUNK_SIZE_WORDS) -> list[str]:
    words = text.split()
    if not words:
        return []
    return [" ".join(words[i : i + chunk_size]) for i in range(0, len(words), chunk_size)]


async def ingest_document(text: str, owner: str | None = None, source: str | None = None) -> int:
    chunks = _chunk_text(text)
    if source:
        await delete_source(owner, source)
    for chunk in chunks:
        vector = await embed_text(chunk, kind="document")
        await upsert_chunk(str(uuid.uuid4()), vector, chunk, owner=owner, source=source)
    return len(chunks)


async def retrieve_context(
    query: str, top_k: int = 3, owner: str | None = None, min_score: float | None = None
) -> list[str]:
    vector = await embed_text(query, kind="query")
    return await search(vector, top_k=top_k, owner=owner, min_score=min_score)


async def augment_with_documents(message: str, owner: str) -> str:
    """Prepend the owner's relevant document excerpts to the message (unchanged if none)."""
    chunks = await retrieve_context(
        message, top_k=settings.RAG_TOP_K, owner=owner, min_score=settings.RAG_MIN_SCORE
    )
    if not chunks:
        return message
    context = "\n\n---\n\n".join(chunks)
    return (
        "The excerpts below come from documents this user uploaded and were picked by an "
        "automatic search, so they are often unrelated to the message. Use them ONLY if they "
        "directly answer it (then say the answer is based on their documents). If they don't, "
        "answer normally and do not mention the excerpts or documents at all.\n\n"
        f"--- Document excerpts ---\n{context}\n--- End of excerpts ---\n\n"
        f"User's message: {message}"
    )
