# PROGRESS — qayerda to'xtadik

> Har sessiya oxirida yangilanadi. Eng yangi yozuv eng tepada.

## 2026-10-07 — Milestone 25: savol turiga qarab avtomatik model tanlash ✅ (DeepSeek OmniRoute importi kutilmoqda)
- Solishtirish (`ai-launcher/compare_models.py`, natijalar `compare_result*.txt`): hisob/jadval/mantiq savollarida
  uzbek-llama-8k 0/3, deepseek-r1-8k 2/3 ("Sarda" ~ Sardor). O'zbekcha matnda ikkalasi zaif, faktlarda ikkalasi to'qiydi.
  DeepSeek system prompt bilan butunlay ma'nosiz yozdi — ko'rsatma user xabariga qo'shilganda normal.
- `services/llm/model_router.py`: qoidaga asoslangan tanlov (ifoda `47*89`, hisob so'zlari + raqam, mantiq so'zlari,
  yaqinda Excel yuklangan bo'lsa) → `REASONING_MODEL` (`.env`: deepseek-r1-8k:latest), qolgani → OLLAMA_MODEL.
- DeepSeek uchun: system prompt user xabariga qo'shiladi, `max_tokens=REASONING_MAX_TOKENS` (3072, aylanib qolmasin),
  `<think>` bloklari javobdan va oqimdan olib tashlanadi (`strip_think`, `ThinkFilter`). `ChatResponse.model` — kim javob berdi.
- Zaxira: reasoning model xato bersa → chat modeli javob beradi (logda "falling back"). Sinaldi: DeepSeek OmniRoute'da
  hali import qilinmagan holatda 47*89 → 4183 (uzbek-llama).
- `tests/test_model_router.py` (16 test) — jami 22 test o'tadi.
- **Kutilmoqda:** foydalanuvchi OmniRoute'da Ollama provayderi → "Импорт из /модели" (va "Автоматически получать
  модели из upstream" ni yoqish). Keyin `ai-launcher/m25_test.sh` bilan jonli tekshirish.
- `start_all.bat`: Docker ishlamayotgan bo'lsa, ishga tushirishdan oldin eskirgan socket fayllarni WSL orqali tozalaydi
  (qayta yoqishdan keyin Docker yiqilardi).

## 2026-10-07 — RAM: modellar GPU'ga sig'adigan qilindi ✅
- Muammo: RAM 86% — `llama-server` 16–22 GB. O'zbekcha model 131072 kontekst bilan 23 GB, 74% CPU.
  Ollama app'ning global "Context length" = 256K, `OLLAMA_CONTEXT_LENGTH` env'ini bosib ketadi.
- Yechim: `uzbek-llama-8k` va `llama3.1-8k` (PARAMETER num_ctx 8192, og'irliklar umumiy) + `OLLAMA_MAX_LOADED_MODELS=1`
  (User env). OmniRoute'da qayta import, `.env`: `OLLAMA_MODEL=uzbek-llama-8k:latest`, `OLLAMA_TOOL_MODEL=llama3.1-8k:latest`.
- Natija: 5.8 GB, 100% GPU, chat 1.1–1.5 s (avval 4.5–11 s), RAM 27 → 14.7 GB. Tool agent ishlaydi (4183).
- Coder ham 8K: `qwen2.5-coder-8k:latest` (32K da 6.8 GB, 8% CPU edi → 5.0 GB, 100% GPU); compose `OLLAMA_CODER_MODEL` ni
  `.env` dan uzatadi. To'liq sinov (`ai-launcher/full_test.sh`, ~2 daqiqa) — hammasi o'tdi, sinovdan keyin RAM 14.4 GB.
- Yo'l-yo'lakay: Docker Desktop ishga tushmadi — kechagi majburan yopishdan qolgan eskirgan AF_UNIX socket fayllari
  (`Docker\run\dockerInference`, `docker-secrets-engine\engine.sock`; Windows'dan 1920-xato) — WSL `rm` bilan o'chirildi.
  `stop_all.ps1` endi avval `docker desktop stop` (to'g'ri yopish), keyin zaxira sifatida kill.

## 2026-10-07 — Milestone 24 (c): admin veb panel ✅
- `/admin` (frontend/admin.html + backend/app/api/admin_router.py): xodimlar ro'yxati, to'liq suhbatlar (/clear dan oldingilari
  xiralashgan holda), bulutga yuborilganlar (asl ↔ niqoblangan ↔ javob). HTTP Basic, parol `.env` dagi `ADMIN_PASSWORD`
  (bo'sh = panel 503, ochilmaydi). **Parolni foydalanuvchi o'zi qo'yadi** → `docker compose up -d backend`.
- Xavfsizlik: compose portlari 127.0.0.1 ga bog'landi (backend 8000, qdrant 6333, searxng 8080) — avval barcha
  interfeyslarda ochiq edi, Qdrant'da parol yo'q (xodim hujjatlari LAN'dan o'qilishi mumkin edi).
- Sinov `ai-launcher/m24_test.sh`: 503 / 401 / 200, ro'yxat va xabarlar, portlar, OmniRoute→SearXNG — o'tdi.
  Claude sinovlaridan qolgan test sessiyalari bazadan tozalandi.

## 2026-10-07 — Milestone 23 (b): niqoblash + bulut zaxirasi ✅ (bulut modeli hali TANLANMAGAN)
- `services/privacy/masking.py`: TEL, PASPORT, JSHSHIR, STIR, KARTA, HISOB, EMAIL, SUMMA, MANZIL, ISM → `[TEL_1]`...;
  bir xil qiymat = bir xil belgi; `unmask()` qavssiz/"TEL 1" variantlarini ham qaytaradi. `tests/test_masking.py` (6 test, pytest).
- `services/cloud/cloud_service.py` + `/api/v1/cloud/{preview,send,cancel}`: preview oxirgi savolni (+ kontekst, CLOUD_CONTEXT_MESSAGES=6)
  niqoblab `cloud_requests` jadvaliga yozadi (asl matn va mapping lokal qoladi); send faqat o'sha sessiyadan, bir marta;
  javob unmask qilinib suhbatga yoziladi. Admin uchun: asl, niqobli, model javobi — hammasi `cloud_requests` da.
- Bot: har javob ostida "☁️ Kuchliroq AI'dan so'rash" → niqoblangan ko'rinish + "✅ Yuborish / ❌ Bekor qilish".
- **`CLOUD_MODEL` bo'sh = o'chiq** (bot "sozlanmagan" deydi). Foydalanuvchi bulut modelini hali tanlamadi:
  tavsiya — rasmiy API (Claude/GPT/Gemini) o'z kaliti bilan OmniRoute'ga qo'shiladi; OmniRoute'dagi bepul hovuzlar
  (dva, aug, cxa, ddgw, oc, zc, cfp...) norasmiy/noma'lum operatorlar — ish ma'lumoti uchun tavsiya qilinmagan.
  Yoqish: `.env` da `CLOUD_MODEL=<gateway model id>` → `docker compose up -d backend`.
- Sinov: `ai-launcher/m23_test.sh` ("bulut" o'rnida LOKAL ollama/llama3.1:8b) — niqoblash, sizib chiqish yo'q, unmask,
  egalik tekshiruvi, qayta yuborish va bekor qilish — o'tdi.

**Keyingi:** (c) admin veb panel (barcha suhbatlar + cloud_requests, faqat admin; parolni foydalanuvchi `.env` ga o'zi qo'yadi).

## 2026-10-07 — Milestone 22 (a): hujjat + Excel ✅
- Har xodimning hujjatlari alohida: Qdrant payload `owner` (tg:<id>) + `source`; egasiz qidiruv faqat umumiy hujjatlarni ko'radi;
  qayta yuklash almashtiradi. `POST /api/v1/files/ingest` (base64): PDF/DOCX/TXT → shaxsiy RAG, CSV/XLSX → xulosa suhbatga.
  Chat'da `use_documents` (faqat model ko'radi). Bot: hujjat qabul qiladi (20 MB), rasmga "hozircha yo'q".
- Topilgan va tuzatilgan: Qdrant ~5s dan keyin bo'sh keep-alive ulanishni yopadi → birinchi so'rov "Server disconnected"
  (500) — `_retry_once`. `nomic-embed-text` uchun `search_document:` / `search_query:` prefikslari qo'shildi.
- O'lchov: nomic o'zbekcha matnda tegishli/tegishsiz savollarni yaxshi ajratmaydi (ballar 0.63–0.72 oralig'ida aralash),
  shuning uchun RAG_MIN_SCORE=0.6 + qat'iy prompt. **Haqiqiy yechim — ko'p tilli embedding (masalan bge-m3, ~1.2 GB,
  1024 o'lcham → Qdrant kolleksiyasini qayta yaratish kerak); foydalanuvchi ruxsati bilan.**
- Sinov: `ai-launcher/m22_test.sh` — A/B izolyatsiya, KAPALAK-8812, takrorlanmaslik, Excel, 415 — hammasi o'tdi.

**Keyingi:** (b) niqoblash + bulut (xodim tasdig'i bilan), (c) admin veb panel.

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
