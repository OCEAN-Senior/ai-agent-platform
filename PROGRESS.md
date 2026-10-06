# PROGRESS — qayerda to'xtadik

> Har sessiya oxirida yangilanadi. Eng yangi yozuv eng tepada.

## 2026-10-06
**Qilindi**
- OmniRoute (AI gateway) WSL Docker'da o'rnatildi va Ollama ulandi (5 model).
- Yangi `OpenAICompatibleProvider` (`backend/app/services/llm/openai_compatible_provider.py`):
  OpenAI formatini Ollama formatiga va aksincha tarjima qiladi (tool_call id, arguments JSON-string).
- `.env` → `LLM_PROVIDER=openai_compatible`; platforma endi OmniRoute orqali ishlaydi.
- Sinovlar o'tdi: chat, session xotira, streaming, tool_agent (calculator), coder_agent (sandbox natijasi 55).
- Docker Desktop'da Ubuntu WSL integratsiyasi yoqildi.

**To'xtagan joy / keyingi qadamlar**
- [ ] OmniRoute'da SearXNG'ni search provayder sifatida ulash (ixtiyoriy).
- [ ] OmniRoute bepul bulut provayderlari (aihorde, duckduckgo-web, ...) foydalanuvchi tomonidan yoqilgan — maxfiy ma'lumot yubormaslik haqida ogohlantirilgan; kerak bo'lmasa o'chirish.
- [ ] Foydalanuvchi OmniRoute parolini va API kalitini almashtirishi kerak (chatda ko'ringan). Kalit almashsa: `.env` dagi `OPENAI_COMPAT_API_KEY` ni yangilab, `docker compose up -d backend`.
- [ ] Avtomatik testlar yo'q — `tests/` papkasi va pytest qo'shish foydali bo'lardi.
