# PROGRESS — qayerda to'xtadik

> Har sessiya oxirida yangilanadi. Eng yangi yozuv eng tepada.

## 2026-10-06 (2) — AI Brain birlashtirildi (Milestone 21)
**Qilindi**
- Suhbat xotirasi doimiy (SQLite, volume `app_data`): restartdan keyin davom etadi; `/clear` tarixni o'chirmaydi.
- Telegram bot platformaga ko'chirildi (`telegram-bot` xizmati): allowlist, /start (saqlanish haqida ogohlantirish),
  /clear, uzun javoblarni bo'lish, "typing" ko'rsatkichi, bir vaqtda ko'p foydalanuvchi (concurrent_updates + chat lock).
- Token va allowlist AI Brain `.env` dan ko'chirildi. `CHAT_SYSTEM_PROMPT` — doim o'zbekcha.
- Sinovlar: xotira unit testi, restartdan keyin PELICAN-42 eslandi, regressiya (chat, tool, coder) o'tdi.

**Keyingi qadamlar (xodimlar uchun bot rejasi)**
- [x] Telegram'da haqiqiy xabar bilan sinaldi (@oqdaryo_ai_bot): javob OmniRoute orqali keldi, suhbat bazada saqlandi.
- Chat modeli o'zbekcha `uzbek-llama-3.1-8B` ga o'tkazildi (`.env` OLLAMA_MODEL); tool_agent uchun alohida
  `OLLAMA_TOOL_MODEL=llama3.1:8b` (o'zbekcha model tool chaqirmay matn yozib qo'ydi). Javob sifati 8B darajasida —
  murakkab vazifalar uchun bulut zaxirasi (niqoblash bilan) rejada.
- [ ] AI Brain'dan qolganlar: hujjat yuklash (RAG, har xodimga alohida), Excel/CSV tahlili, rasm tahlili, uzoq muddatli faktlar.
- [ ] Navbat ko'rsatkichi ("Navbatingiz: N") va Ollama parallelligi (`OLLAMA_NUM_PARALLEL`).
- [ ] Niqoblash/deniqoblash moduli + lokal → bulut (OmniRoute) yo'nalishi, xodim tasdig'i bilan.
- [ ] Admin ko'rinishi: barcha suhbatlar faqat admin uchun (`sessions` + `messages` jadvallari tayyor).
- [ ] Bot tokenini @BotFather orqali yangilash (avval eski logda ochiq turgan).

## 2026-10-06
**Qilindi**
- OmniRoute (AI gateway) WSL Docker'da o'rnatildi va Ollama ulandi (5 model).
- Yangi `OpenAICompatibleProvider` (`backend/app/services/llm/openai_compatible_provider.py`):
  OpenAI formatini Ollama formatiga va aksincha tarjima qiladi (tool_call id, arguments JSON-string).
- `.env` → `LLM_PROVIDER=openai_compatible`; platforma endi OmniRoute orqali ishlaydi.
- Sinovlar o'tdi: chat, session xotira, streaming, tool_agent (calculator), coder_agent (sandbox natijasi 55).
- Docker Desktop'da Ubuntu WSL integratsiyasi yoqildi.

**To'xtagan joy / keyingi qadamlar**
- [x] OmniRoute'da SearXNG search provayder sifatida ulandi (`local-searxng`,
  `http://host.docker.internal:8080/search`; `/api/v1/search` orqali sinaldi).
- [ ] OmniRoute bepul bulut provayderlari (aihorde, duckduckgo-web, ...) foydalanuvchi tomonidan yoqilgan — maxfiy ma'lumot yubormaslik haqida ogohlantirilgan; kerak bo'lmasa o'chirish.
- [ ] Foydalanuvchi OmniRoute parolini va API kalitini almashtirishi kerak (chatda ko'ringan). Kalit almashsa: `.env` dagi `OPENAI_COMPAT_API_KEY` ni yangilab, `docker compose up -d backend`.
- [ ] Avtomatik testlar yo'q — `tests/` papkasi va pytest qo'shish foydali bo'lardi.
