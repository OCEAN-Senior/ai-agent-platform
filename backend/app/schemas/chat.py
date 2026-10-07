from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    user_name: str | None = None
    # Search this session's uploaded documents and give relevant excerpts to the model.
    use_documents: bool = False


class ChatResponse(BaseModel):
    response: str
    # Which model answered (routing between chat and reasoning models).
    model: str | None = None


class ChatHistoryResponse(BaseModel):
    session_id: str
    history: list[dict[str, str]]
