from fastapi import APIRouter, HTTPException

from backend.app.agents.base import AgentInput, AgentResult
from backend.app.agents.manager import AgentExecutionError, AgentManager, AgentNotFoundError
from backend.app.agents.orchestrator import MultiAgentOrchestrator
from backend.app.schemas.agent import AgentRunRequest
from backend.app.schemas.chat import ChatHistoryResponse, ChatRequest, ChatResponse
from backend.app.schemas.execution import ExecuteCodeRequest, ExecuteCodeResponse
from backend.app.schemas.orchestration import OrchestrateRequest, OrchestrateResponse
from backend.app.schemas.rag import IngestRequest, IngestResponse, RagQueryRequest, RagQueryResponse
from backend.app.services.chat_service import get_chat_response
from backend.app.services.execution.sandbox import run_python_code
from backend.app.services.memory.conversation_memory import ConversationMemory
from backend.app.services.rag.rag_service import ingest_document, retrieve_context

router = APIRouter()
agent_manager = AgentManager()
orchestrator = MultiAgentOrchestrator(agent_manager)
conversation_memory = ConversationMemory()


@router.post("/api/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    history = conversation_memory.get_history(request.session_id) if request.session_id else None
    reply = await get_chat_response(request.message, history=history)
    if request.session_id:
        conversation_memory.add_exchange(request.session_id, request.message, reply)
    return ChatResponse(response=reply)


@router.get("/api/v1/chat/{session_id}/history", response_model=ChatHistoryResponse)
def get_chat_history(session_id: str) -> ChatHistoryResponse:
    return ChatHistoryResponse(session_id=session_id, history=conversation_memory.get_history(session_id))


@router.delete("/api/v1/chat/{session_id}/history")
def clear_chat_history(session_id: str) -> dict:
    conversation_memory.clear(session_id)
    return {"status": "cleared", "session_id": session_id}


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


@router.post("/api/v1/documents/ingest", response_model=IngestResponse)
async def ingest(request: IngestRequest) -> IngestResponse:
    chunks_ingested = await ingest_document(request.text)
    return IngestResponse(chunks_ingested=chunks_ingested)


@router.post("/api/v1/rag/query", response_model=RagQueryResponse)
async def rag_query(request: RagQueryRequest) -> RagQueryResponse:
    context = await retrieve_context(request.query, top_k=request.top_k)
    return RagQueryResponse(query=request.query, context=context)


@router.post("/api/v1/execute", response_model=ExecuteCodeResponse)
async def execute_code(request: ExecuteCodeRequest) -> ExecuteCodeResponse:
    result = await run_python_code(request.code, timeout=request.timeout)
    return ExecuteCodeResponse(
        stdout=result.stdout,
        stderr=result.stderr,
        exit_code=result.exit_code,
        timed_out=result.timed_out,
    )
