"""Send a conversation to a stronger cloud model -- masked, and only after the user confirms.

Flow: preview() masks the recent context and stores a pending request (originals never
leave this machine); send() forwards the masked text to CLOUD_MODEL through the
OpenAI-compatible gateway, restores the placeholders in the reply and records everything,
so the admin can later see exactly what was sent. Empty CLOUD_MODEL = feature disabled.
"""
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from backend.app.core.config import settings
from backend.app.services.llm.openai_compatible_provider import OpenAICompatibleProvider
from backend.app.services.memory.conversation_memory import ConversationMemory
from backend.app.services.privacy.masking import mask, unmask

CLOUD_PROMPT_SUFFIX = (
    " Placeholders such as [TEL_1], [ISM_2] or [SUMMA_1] stand for values hidden for privacy. "
    "Keep them exactly as written in your answer and don't try to guess what they contain."
)


class CloudRequestError(Exception):
    pass


class CloudService:
    def __init__(self, memory: ConversationMemory, db_path: str | Path | None = None) -> None:
        self._memory = memory
        self._db_path = Path(db_path or Path(settings.DATA_DIR) / "conversations.db")
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self._db_path)) as conn, conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cloud_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    status TEXT NOT NULL,          -- pending | sent | cancelled | failed
                    original_json TEXT NOT NULL,   -- messages as written (stays local)
                    masked_json TEXT NOT NULL,     -- what is sent to the cloud
                    mapping_json TEXT NOT NULL,    -- placeholder -> original (stays local)
                    model TEXT,
                    response_masked TEXT,
                    response TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    @property
    def enabled(self) -> bool:
        return bool(settings.CLOUD_MODEL)

    def preview(self, session_id: str) -> dict:
        history = self._memory.get_history(session_id)
        last_user = max((i for i, m in enumerate(history) if m["role"] == "user"), default=None)
        if last_user is None:
            raise CloudRequestError("Bulutga yuboriladigan savol topilmadi.")
        # Context up to and including the latest question; the local answer is left out.
        messages = history[: last_user + 1][-settings.CLOUD_CONTEXT_MESSAGES :]
        masked_texts, mapping = mask([m["content"] for m in messages])
        masked = [{"role": m["role"], "content": t} for m, t in zip(messages, masked_texts)]

        now = _now()
        with closing(sqlite3.connect(self._db_path)) as conn, conn:
            request_id = conn.execute(
                "INSERT INTO cloud_requests (session_id, status, original_json, masked_json, mapping_json,"
                " created_at, updated_at) VALUES (?, 'pending', ?, ?, ?, ?, ?)",
                (session_id, json.dumps(messages, ensure_ascii=False), json.dumps(masked, ensure_ascii=False),
                 json.dumps(mapping, ensure_ascii=False), now, now),
            ).lastrowid

        counts: dict[str, int] = {}
        for placeholder in mapping:
            kind = placeholder.strip("[]").rsplit("_", 1)[0]
            counts[kind] = counts.get(kind, 0) + 1
        return {
            "request_id": request_id,
            "enabled": self.enabled,
            "masked_question": masked[-1]["content"],
            "context_messages": len(masked),
            "hidden": counts,
        }

    async def send(self, request_id: int, session_id: str) -> str:
        row = self._get(request_id, session_id)
        if row["status"] != "pending":
            raise CloudRequestError("Bu so'rov allaqachon yuborilgan yoki bekor qilingan.")
        if not self.enabled:
            raise CloudRequestError("Bulut AI hali sozlanmagan.")

        masked = json.loads(row["masked_json"])
        mapping = json.loads(row["mapping_json"])
        original = json.loads(row["original_json"])
        provider = OpenAICompatibleProvider(model=settings.CLOUD_MODEL, model_prefix="")
        system = [{"role": "system", "content": settings.CHAT_SYSTEM_PROMPT + CLOUD_PROMPT_SUFFIX}]
        try:
            reply_masked = await provider.chat(masked[-1]["content"], history=system + masked[:-1])
        except Exception as exc:
            self._update(request_id, status="failed", model=settings.CLOUD_MODEL, response_masked=str(exc))
            raise CloudRequestError(f"Bulut AI javob bermadi: {exc}") from exc

        reply = unmask(reply_masked, mapping)
        self._update(request_id, status="sent", model=settings.CLOUD_MODEL,
                     response_masked=reply_masked, response=reply)
        self._memory.add_exchange(session_id, f"[☁️ Bulut AI'ga yuborildi] {original[-1]['content']}", reply)
        return reply

    def cancel(self, request_id: int, session_id: str) -> None:
        row = self._get(request_id, session_id)
        if row["status"] == "pending":
            self._update(request_id, status="cancelled")

    def _get(self, request_id: int, session_id: str) -> sqlite3.Row:
        with closing(sqlite3.connect(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM cloud_requests WHERE id = ?", (request_id,)).fetchone()
        # A request can only be confirmed or cancelled from the session that created it.
        if row is None or row["session_id"] != session_id:
            raise CloudRequestError("So'rov topilmadi.")
        return row

    def _update(self, request_id: int, **fields) -> None:
        fields["updated_at"] = _now()
        assignments = ", ".join(f"{key} = ?" for key in fields)
        with closing(sqlite3.connect(self._db_path)) as conn, conn:
            conn.execute(f"UPDATE cloud_requests SET {assignments} WHERE id = ?", (*fields.values(), request_id))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
