import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from backend.app.core.config import settings


class ConversationMemory:
    """Persistent chat memory backed by SQLite.

    Every message is kept forever (the admin can read full conversations), while
    get_history() only returns the current *context*: the latest messages since the
    session's last clear(). So a user's /clear gives the model a fresh start without
    erasing the record, and history survives restarts so users resume where they stopped.
    """

    def __init__(self, db_path: str | Path | None = None, max_messages: int | None = None) -> None:
        self._db_path = Path(db_path or Path(settings.DATA_DIR) / "conversations.db")
        self._max_messages = max_messages or settings.MEMORY_MAX_MESSAGES
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as conn, conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_messages_session ON messages (session_id, id);
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_name TEXT,
                    context_start_id INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def get_history(self, session_id: str) -> list[dict[str, str]]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                """
                SELECT role, content FROM messages
                WHERE session_id = ?
                  AND id > COALESCE((SELECT context_start_id FROM sessions WHERE session_id = ?), 0)
                ORDER BY id DESC LIMIT ?
                """,
                (session_id, session_id, self._max_messages),
            ).fetchall()
        return [{"role": role, "content": content} for role, content in reversed(rows)]

    def add_exchange(
        self,
        session_id: str,
        user_message: str,
        assistant_message: str,
        user_name: str | None = None,
    ) -> None:
        now = _now()
        with closing(self._connect()) as conn, conn:
            conn.executemany(
                "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                [
                    (session_id, "user", user_message, now),
                    (session_id, "assistant", assistant_message, now),
                ],
            )
            conn.execute(
                """
                INSERT INTO sessions (session_id, user_name, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    user_name = COALESCE(excluded.user_name, sessions.user_name),
                    updated_at = excluded.updated_at
                """,
                (session_id, user_name, now, now),
            )

    def clear(self, session_id: str) -> None:
        """Start a fresh context for the model; the stored messages are kept."""
        now = _now()
        with closing(self._connect()) as conn, conn:
            last_id = conn.execute(
                "SELECT COALESCE(MAX(id), 0) FROM messages WHERE session_id = ?", (session_id,)
            ).fetchone()[0]
            conn.execute(
                """
                INSERT INTO sessions (session_id, context_start_id, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    context_start_id = excluded.context_start_id,
                    updated_at = excluded.updated_at
                """,
                (session_id, last_id, now, now),
            )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
