from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    response: str


class ChatHistoryResponse(BaseModel):
    session_id: str
    history: list[dict[str, str]]
