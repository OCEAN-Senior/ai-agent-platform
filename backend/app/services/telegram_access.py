"""Who may use the Telegram bot -- managed from the admin panel or the admin's own Telegram.

IDs in TELEGRAM_ALLOWED_USER_IDS are the admins: always allowed, and they get approval
requests. Everyone else starts as a pending request the first time they write to the bot
and is then allowed or blocked by an admin.
"""
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from backend.app.core.config import settings

STATUSES = ("pending", "allowed", "blocked")


def admin_ids() -> set[int]:
    return {int(x) for x in settings.TELEGRAM_ALLOWED_USER_IDS.split(",") if x.strip().isdigit()}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class TelegramAccess:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self._db_path = Path(db_path or Path(settings.DATA_DIR) / "conversations.db")
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as conn, conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS telegram_access (
                    user_id INTEGER PRIMARY KEY,
                    name TEXT,
                    status TEXT NOT NULL,
                    requested_at TEXT NOT NULL,
                    decided_at TEXT
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def check(self, user_id: int, name: str | None = None) -> dict:
        """Is this user allowed? Unknown users are recorded as a new pending request."""
        if user_id in admin_ids():
            return {"allowed": True, "status": "admin", "new_request": False}
        with closing(self._connect()) as conn, conn:
            row = conn.execute("SELECT status FROM telegram_access WHERE user_id = ?", (user_id,)).fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO telegram_access (user_id, name, status, requested_at) VALUES (?, ?, 'pending', ?)",
                    (user_id, name, _now()),
                )
                return {"allowed": False, "status": "pending", "new_request": True}
            if name:
                conn.execute("UPDATE telegram_access SET name = ? WHERE user_id = ?", (name, user_id))
        return {"allowed": row["status"] == "allowed", "status": row["status"], "new_request": False}

    def set_status(self, user_id: int, status: str) -> bool:
        if status not in STATUSES or user_id in admin_ids():
            return False
        with closing(self._connect()) as conn, conn:
            changed = conn.execute(
                "UPDATE telegram_access SET status = ?, decided_at = ? WHERE user_id = ?",
                (status, _now(), user_id),
            ).rowcount
        return changed > 0

    def list(self) -> list[dict]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT user_id, name, status, requested_at, decided_at FROM telegram_access "
                "ORDER BY CASE status WHEN 'pending' THEN 0 WHEN 'allowed' THEN 1 ELSE 2 END, requested_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]
