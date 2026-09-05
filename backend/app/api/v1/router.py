from fastapi import APIRouter

from backend.app.schemas.chat import ChatRequest, ChatResponse
from backend.app.services.ollama_service import generate_chat_response

router = APIRouter()


@router.get("/")
def root():
    return {
        "message": "AI Agent Platform API"
    }


@router.get("/health")
def health():
    return {
        "status": "ok"
    }


@router.post("/api/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    reply = await generate_chat_response(request.message)
    return ChatResponse(response=reply)
