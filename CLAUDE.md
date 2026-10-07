# AI Agent Platform — Claude uchun eslatma

> Bu fayl har sessiya boshida avtomatik o'qiladi. Loyihani noldan skanerlamang —
> avval shu faylni va `PROGRESS.md` ni o'qing, keyin faqat kerakli fayllarni oching.
> Sessiya oxirida `PROGRESS.md` ni yangilang.

## Ish qoidalari
- Hamma ish **WSL Ubuntu** ichida: repo `~/ai-agent-platform` (Windows'da emas).
- Foydalanuvchi dasturlashni o'rganyapti: har qadamni qisqa tushuntiring, kichik qismlarda ishlang.
- Har tugallangan bosqichdan keyin `main` ga commit + push (so'ramasdan). Commit uslubi: `feat: ...`, `fix: ...`, `docs: ...`.
- Maxfiy narsalar faqat `.env` da (git'ga tushmaydi). Kalit/parollarni chatga va loglarga chiqarmang.

## Arxitektura (qisqa xarita)
| Qism | Joyi |
|---|---|
| FastAPI kirish nuqtasi | `backend/app/main.py` (public `/`, `/health`; `/api/v1/*` API-key bilan) |
| API endpointlar | `backend/app/api/v1/router.py` — chat, chat/stream, agent/run, agent/orchestrate, documents/ingest, rag/query, execute |
| Sozlamalar | `backend/app/core/config.py` (pydantic-settings, `.env`) |
| LLM provayderlar | `backend/app/services/llm/` — `base.py` (LLMProvider), `ollama_provider.py`, `openai_compatible_provider.py` (OmniRoute), `factory.py` (`LLM_PROVIDER` bo'yicha tanlaydi) |
| Agentlar | `backend/app/agents/` — simple_chat, planner, research (RAG + SearXNG), coder (sandbox'da ishga tushiradi), tool_agent (tool-calling + MCP), orchestrator |
| RAG | `services/rag/` + Qdrant; embedding har doim to'g'ridan-to'g'ri Ollama (`nomic-embed-text`) |
| Tools / MCP / Sandbox | `services/tools/registry.py`, `services/mcp/`, `mcp_servers/example_server.py`, `services/execution/sandbox.py` |
| Frontend | `frontend/index.html` → `/ui` |
| Suhbat xotirasi | `services/memory/conversation_memory.py` — SQLite (`DATA_DIR/conversations.db`, Docker volume `app_data`). Hamma xabar abadiy saqlanadi (admin uchun); `clear()` faqat model kontekstini yangilaydi |
| Telegram bot (xodimlar uchun) | `backend/app/telegram/bot.py` — alohida compose xizmati `telegram-bot`, platformaga HTTP API orqali ulanadi (session `tg:<user_id>`), allowlist `TELEGRAM_ALLOWED_USER_IDS` |
| Chat system prompt | `CHAT_SYSTEM_PROMPT` (config) — standart: doim o'zbekcha javob |
| Modellar | **8K kontekstli nusxalar** (`ai-launcher\ollama_8k_models.ps1`): `.env` da `OLLAMA_MODEL=uzbek-llama-8k:latest`, `OLLAMA_TOOL_MODEL=llama3.1-8k:latest` — 128K kontekstda model 23 GB bo'lib RAM/CPU'ga tushardi; Ollama app sozlamasi 256K, env o'zgaruvchisini bosib ketadi, shuning uchun num_ctx model ichida. Yangi model yaratilsa OmniRoute'da qayta import kerak. Asl: `OLLAMA_MODEL` (chat/Telegram; o'zbekcha `uzbek-llama-3.1-8B`), `OLLAMA_TOOL_MODEL` (tool_agent, `llama3.1:8b` — o'zbekcha model tool chaqirmaydi), `OLLAMA_CODER_MODEL` (`qwen2.5-coder:7b`) |

## Ishga tushirish
- Docker (asosiy): `docker compose up -d --build` → backend `127.0.0.1:8000`, qdrant `6333`, searxng `8080`, telegram-bot.
- 2026-10-06 dan **AI Brain shu loyihaga birlashtirildi**; eski Windows loyihasi arxivda
  (`C:\Users\user\Documents\_arxiv\ai-brain-2026-10-06`). Undagi qolgan imkoniyatlar (hujjat/jadval/rasm
  tahlili, uzoq muddatli faktlar xotirasi) hali ko'chirilmagan — `PROGRESS.md` ga qarang.
- **`localhost` emas, `127.0.0.1` ishlating** — localhost IPv6 ga ketib, Docker portida qotib qoladi.
- Windows ish stolidagi "AI - Hammasini ishga tushirish" tugmasi hammasini ko'taradi
  (`C:\Users\user\Documents\ai-launcher\start_all.bat`).

## LLM yo'nalishi (2026-10-06 dan)
- `.env`: `LLM_PROVIDER=openai_compatible` → so'rovlar **OmniRoute** (`127.0.0.1:20128/v1`, WSL Docker konteyner `omniroute`) orqali Ollama'ga boradi.
- Model nomlari `OLLAMA_MODEL` / `OLLAMA_CODER_MODEL` dan olinadi, oldiga `OPENAI_COMPAT_MODEL_PREFIX` (`ollama/`) qo'shiladi.
- Konteynerga faqat `LLM_PROVIDER`, `OPENAI_COMPAT_*` uzatiladi (compose interpolation) — `API_KEYS` ataylab uzatilmaydi.
- Orqaga qaytish: `.env` da `LLM_PROVIDER=ollama` va `docker compose up -d backend`.

## Tekshiruv
- Tez sinov skripti: `/mnt/c/Users/user/Documents/ai-launcher/aap_omniroute_test.sh`
  (chat, session xotira, streaming, tool_agent kalkulyator 47*89=4183, coder_agent).
- OmniRoute'ga borganini tekshirish: `docker logs --since 10m omniroute | grep chat/completions`.
