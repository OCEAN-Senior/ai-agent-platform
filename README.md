# AI Agent Platform

A local-first, extensible AI agent platform: FastAPI backend, Ollama-backed
LLMs, multiple specialized agents, RAG, tool calling (including MCP), a
sandboxed code executor, and a small test-panel frontend.

## Texnologiyalar

- Python, FastAPI, Uvicorn, Pydantic
- Ollama (local LLM + embeddings)
- Qdrant (vector DB / RAG)
- MCP (Model Context Protocol)
- Docker, Docker Compose

## Quick start

```bash
cp .env.example .env      # then set API_KEYS, review OLLAMA_* / QDRANT_*
docker compose up -d --build
```

Open `http://localhost:8000/ui/` for the test panel, or `http://localhost:8000/docs` for the interactive API docs. See [DEPLOYMENT.md](DEPLOYMENT.md) for the full production checklist, auto-start, backups, and scaling notes.

## API

All `/api/v1/*` routes require `Authorization: Bearer <key>` once `API_KEYS` is set (`/` and `/health` stay public).

| Endpoint | Description |
|---|---|
| `POST /api/v1/chat` | Single-turn chat, optional `session_id` for memory |
| `POST /api/v1/chat/stream` | Same, streamed as Server-Sent Events |
| `GET/DELETE /api/v1/chat/{session_id}/history` | Inspect / clear a session's memory |
| `POST /api/v1/agent/run` | Run one named agent on a task |
| `POST /api/v1/agent/orchestrate` | Planner -> Research/Coder per subtask -> Synthesizer |
| `POST /api/v1/documents/ingest` | Add text to the RAG vector store |
| `POST /api/v1/rag/query` | Retrieve matching chunks |
| `POST /api/v1/execute` | Run Python in a sandboxed, network-disabled container |

## Agents (`agent` field for `/api/v1/agent/run`)

- `simple_chat_agent` -- plain LLM passthrough
- `planner_agent` -- breaks a task into numbered subtasks
- `research_agent` -- answers using RAG context when available, else its own knowledge (`metadata.source` says which)
- `coder_agent` -- uses a separate code model, auto-runs its own generated code in the sandbox and reports the result
- `tool_agent` -- real LLM tool-calling: a local registry (calculator, clock) plus tools from an MCP server, merged into one call loop

## Project layout

- `backend/app/main.py` -- app wiring: routers, auth dependency, logging middleware, `/ui` static mount
- `backend/app/api/` -- `public_router.py` (no auth) and `v1/router.py` (all `/api/v1/*`)
- `backend/app/agents/` -- `base.py` (BaseAgent/AgentInput/AgentResult), `manager.py` (AgentManager), `orchestrator.py`, and one file per agent
- `backend/app/services/llm/` -- `LLMProvider` abstraction (`base.py`), `OllamaProvider`, `factory.py`
- `backend/app/services/rag/`, `services/embeddings/` -- Qdrant vector store + Ollama embeddings
- `backend/app/services/mcp/` -- MCP client; `mcp_servers/example_server.py` is the bundled demo MCP server
- `backend/app/services/execution/sandbox.py` -- Docker-based sandboxed code execution
- `backend/app/services/memory/conversation_memory.py` -- in-process short-term chat memory
- `backend/app/core/` -- `config.py` (env-driven settings), `security.py` (API key auth), `logging_config.py`
- `frontend/index.html` -- single-file test panel (no build step), served at `/ui`
- `mcp_servers/` -- MCP servers this backend connects to as a client

## Not yet built

- Web search (needs a Tavily API key -- opt-in, not created on your behalf)
- Persistent/long-term memory and a real user/project database (Postgres) -- deferred until actually needed
- Multi-worker scaling (blocked on moving `ConversationMemory` to a shared store first -- see `DEPLOYMENT.md`)
