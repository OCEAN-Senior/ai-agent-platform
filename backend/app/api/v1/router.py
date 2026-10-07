import asyncio
import base64
import binascii
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from backend.app.agents.base import AgentInput, AgentResult
from backend.app.agents.manager import AgentExecutionError, AgentManager, AgentNotFoundError
from backend.app.agents.orchestrator import MultiAgentOrchestrator
from backend.app.schemas.agent import AgentRunRequest
from backend.app.schemas.chat import ChatHistoryResponse, ChatRequest, ChatResponse
from backend.app.schemas.cloud import (
    CloudActionRequest,
    CloudPreviewRequest,
    CloudPreviewResponse,
    CloudSendResponse,
)
from backend.app.schemas.execution import ExecuteCodeRequest, ExecuteCodeResponse
from backend.app.schemas.files import FileIngestRequest, FileIngestResponse
from backend.app.schemas.orchestration import OrchestrateRequest, OrchestrateResponse
from backend.app.schemas.rag import IngestRequest, IngestResponse, RagQueryRequest, RagQueryResponse
from backend.app.services.chat_service import get_chat_response, stream_chat_response
from backend.app.services.cloud.cloud_service import CloudRequestError, CloudService
from backend.app.services.execution.sandbox import run_python_code
from backend.app.services.files.extract import (
    DOCUMENT_TYPES,
    SPREADSHEET_TYPES,
    extract_document_text,
    summarize_spreadsheet,
)
from backend.app.services.memory.conversation_memory import ConversationMemory
from backend.app.services.rag.rag_service import (
    augment_with_documents,
    ingest_document,
    retrieve_context,
)

router = APIRouter()
agent_manager = AgentManager()
orchestrator = MultiAgentOrchestrator(agent_manager)
conversation_memory = ConversationMemory()
cloud_service = CloudService(conversation_memory)


async def _prompt_for(request: ChatRequest) -> str:
    # Only the model sees document excerpts; memory stores what the user actually wrote.
    if request.use_documents and request.session_id:
        return await augment_with_documents(request.message, owner=request.session_id)
    return request.message


@router.post("/api/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    history = conversation_memory.get_history(request.session_id) if request.session_id else None
    reply = await get_chat_response(await _prompt_for(request), history=history)
    if request.session_id:
        conversation_memory.add_exchange(
            request.session_id, request.message, reply, user_name=request.user_name
        )
    return ChatResponse(response=reply)


@router.post("/api/v1/chat/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    history = conversation_memory.get_history(request.session_id) if request.session_id else None
    prompt = await _prompt_for(request)

    async def event_generator():
        full_response = ""
        async for token in stream_chat_response(prompt, history=history):
            full_response += token
            yield f"data: {json.dumps({'token': token})}\n\n"
        if request.session_id:
            conversation_memory.add_exchange(
                request.session_id, request.message, full_response, user_name=request.user_name
            )
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


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


@router.post("/api/v1/files/ingest", response_model=FileIngestResponse)
async def ingest_file(request: FileIngestRequest) -> FileIngestResponse:
    """Documents -> the session's private search index; spreadsheets -> a summary in its chat."""
    filename = Path(request.filename).name
    suffix = Path(filename).suffix.lower()
    try:
        data = base64.b64decode(request.content_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=400, detail="content_base64 is not valid base64") from exc

    if suffix in DOCUMENT_TYPES:
        try:
            text = await asyncio.to_thread(extract_document_text, filename, data)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Could not read the document: {exc}") from exc
        if not text.strip():
            raise HTTPException(status_code=422, detail="No text found in the document (scanned PDF?)")
        chunks = await ingest_document(text, owner=request.session_id, source=filename)
        conversation_memory.add_exchange(
            request.session_id,
            f"[Hujjat yuklandi: {filename}]",
            f"Hujjat o'qildi va indekslandi ({chunks} bo'lak).",
            user_name=request.user_name,
        )
        return FileIngestResponse(kind="document", filename=filename, chunks=chunks)

    if suffix in SPREADSHEET_TYPES:
        try:
            summary = await asyncio.to_thread(summarize_spreadsheet, filename, data)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Could not read the spreadsheet: {exc}") from exc
        conversation_memory.add_exchange(
            request.session_id,
            f"[Yuklangan jadval: {filename}]\n{summary}",
            "Jadvalni ko'rib chiqdim, savollaringizga tayyorman.",
            user_name=request.user_name,
        )
        return FileIngestResponse(kind="spreadsheet", filename=filename, chunks=0)

    raise HTTPException(status_code=415, detail=f"Unsupported file type: {suffix or '(none)'}")


@router.post("/api/v1/cloud/preview", response_model=CloudPreviewResponse)
def cloud_preview(request: CloudPreviewRequest) -> CloudPreviewResponse:
    """Mask the session's latest question (+ context) and park it until the user confirms."""
    try:
        return CloudPreviewResponse(**cloud_service.preview(request.session_id))
    except CloudRequestError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/api/v1/cloud/send", response_model=CloudSendResponse)
async def cloud_send(request: CloudActionRequest) -> CloudSendResponse:
    try:
        return CloudSendResponse(response=await cloud_service.send(request.request_id, request.session_id))
    except CloudRequestError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/api/v1/cloud/cancel")
def cloud_cancel(request: CloudActionRequest) -> dict:
    try:
        cloud_service.cancel(request.request_id, request.session_id)
    except CloudRequestError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "cancelled"}


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
