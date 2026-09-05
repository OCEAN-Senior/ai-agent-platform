from fastapi import APIRouter, HTTPException

from backend.app.agents.base import AgentInput, AgentResult
from backend.app.agents.manager import AgentExecutionError, AgentManager, AgentNotFoundError
from backend.app.agents.orchestrator import MultiAgentOrchestrator
from backend.app.schemas.agent import AgentRunRequest
from backend.app.schemas.chat import ChatRequest, ChatResponse
from backend.app.schemas.orchestration import OrchestrateRequest, OrchestrateResponse
from backend.app.services.chat_service import get_chat_response

router = APIRouter()
agent_manager = AgentManager()
orchestrator = MultiAgentOrchestrator(agent_manager)


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
    reply = await get_chat_response(request.message)
    return ChatResponse(response=reply)


@router.post("/api/v1/agent/run", response_model=AgentResult)
async def run_agent(request: AgentRunRequest) -> AgentResult:
    try:
        return await agent_manager.run(
            request.agent,
            AgentInput(task=request.task, context=request.context),
        )
    except AgentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AgentExecutionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/api/v1/agent/orchestrate", response_model=OrchestrateResponse)
async def orchestrate(request: OrchestrateRequest) -> OrchestrateResponse:
    try:
        return await orchestrator.run(request.task)
    except AgentExecutionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
