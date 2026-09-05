from pydantic import BaseModel


class IngestRequest(BaseModel):
    text: str


class IngestResponse(BaseModel):
    chunks_ingested: int


class RagQueryRequest(BaseModel):
    query: str
    top_k: int = 3


class RagQueryResponse(BaseModel):
    query: str
    context: list[str]
