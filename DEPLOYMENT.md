# Deployment

## Pre-deployment checklist

- [ ] `.env` has a real `API_KEYS` value (comma-separated). An empty value disables auth entirely -- never leave this empty outside localhost.
- [ ] `OLLAMA_BASE_URL` points at a reachable Ollama instance with `OLLAMA_MODEL`, `OLLAMA_CODER_MODEL`, and `EMBEDDING_MODEL` already pulled (`ollama pull <model>`).
- [ ] `QDRANT_URL` / `QDRANT_COLLECTION` match the `qdrant` service in `docker-compose.yml` (default `http://qdrant:6333` when the backend itself runs in Docker).
- [ ] Docker Desktop's WSL integration is enabled for this distro, and `docker` / `docker compose` run without sudo.
- [ ] If running under WSL2, mirrored networking is enabled (`%USERPROFILE%\.wslconfig` -> `[wsl2]\nnetworkingMode=mirrored`, then `wsl --shutdown`) so the container can reach Ollama via `host.docker.internal`.

## Deploy / redeploy

```bash
cd ~/ai-agent-platform
git pull
docker compose up -d --build
```

`--build` picks up any code or dependency changes; omit it for a plain restart. `depends_on` starts `qdrant` first.

## Verify it's healthy

```bash
docker ps                              # backend should show "healthy" once HEALTHCHECK passes
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/agent/run -H "Authorization: Bearer <your-key>" \
     -H "Content-Type: application/json" -d '{"agent":"simple_chat_agent","task":"hi"}'
```

## Logs

```bash
docker compose logs -f backend      # follow live
docker compose logs backend --tail 100
```

Log format and noise filtering are configured in `backend/app/core/logging_config.py` -- request lines and agent activity are INFO, third-party HTTP client chatter is suppressed to WARNING.

## Auto-start on boot (WSL2 + Windows host)

Since Ollama and this project both live under WSL2 on a Windows machine (not a standalone Linux server), use Windows Task Scheduler to bring the stack up at login, the same pattern as the `ai-brain` project's Telegram bot:

1. Task Scheduler -> **Create Task** (not "Create Basic Task").
2. General: name it "AI Agent Platform", "Run only when user is logged on".
3. Triggers -> New -> "At log on".
4. Actions -> New -> "Start a program":
   - Program: `wsl.exe`
   - Arguments: `-d Ubuntu -- bash -lc "cd ~/ai-agent-platform && docker compose up -d"`
5. Settings -> check "If the task fails, restart every: 1 minute", up to 3 attempts.

For a real standalone Linux server instead, use a systemd unit that runs `docker compose up` in the repo directory with `Restart=always`, or rely on each container's own `restart: unless-stopped` policy (already set) plus Docker's own daemon-starts-on-boot behavior.

## Backups

- **Qdrant data** lives in the named volume `qdrant_data`. Back it up with:
  ```bash
  docker run --rm -v ai-agent-platform_qdrant_data:/data -v $(pwd):/backup \
    alpine tar czf /backup/qdrant_backup_$(date +%Y%m%d).tar.gz /data
  ```
- **Secrets** (`.env`) are never in git (`.gitignore`) or the image (`.dockerignore`) -- keep your own copy somewhere safe; losing it means regenerating API keys.
- **Conversation memory** is intentionally NOT backed up: it's an in-process, non-persistent store (see the Milestone 9/19 notes in `backend/app/services/memory/conversation_memory.py` and `Dockerfile`) and is expected to reset on restart.

## Known constraints to respect when scaling

- **Single worker only.** `ConversationMemory` is an in-memory dict inside one process. Running multiple `uvicorn` workers or multiple backend replicas would silently split chat history between them. Don't add `--workers` or scale replicas until that memory is backed by something shared (Redis, etc.) -- that's follow-up work, not done yet.
- **Docker-outside-of-Docker.** `/api/v1/execute` and the MCP-backed `tool_agent` both call the host's Docker engine via the mounted `docker.sock`. If you move the backend to a host where mounting that socket isn't possible (e.g. some managed container platforms), those two features will fail until re-architected (e.g. a dedicated execution sandbox service).
- **GPU-bound LLM.** Ollama runs on the host's GPU. If you deploy the backend somewhere without access to that Ollama instance (or an equivalent), swap `OLLAMA_BASE_URL` to point at one that is reachable, or implement a new `LLMProvider` (the abstraction from Milestone 2 makes this a contained change: one new class in `backend/app/services/llm/`, one branch in `factory.py`).
