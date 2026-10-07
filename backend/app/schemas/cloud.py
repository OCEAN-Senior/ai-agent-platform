from pydantic import BaseModel


class CloudPreviewRequest(BaseModel):
    session_id: str


class CloudPreviewResponse(BaseModel):
    request_id: int
    enabled: bool
    masked_question: str
    context_messages: int
    hidden: dict[str, int]


class CloudActionRequest(BaseModel):
    request_id: int
    session_id: str


class CloudSendResponse(BaseModel):
    response: str
