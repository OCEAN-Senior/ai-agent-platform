"""Personal invite links for the web chat.

Each invite is a random secret token shown to the admin once; only its SHA-256 hash is stored,
so a leaked database can't be turned back into working links. An invite maps to one chat
session ("web:<id>"), and the admin can revoke it at any time.
"""
import hashlib
import secrets
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from backend.app.core.config import settings


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class InviteStore:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self._db_path = Path(db_path or Path(settings.DATA_DIR) / "conversations.db")
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as conn, conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS invites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    token_hash TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    last_used_at TEXT,
                    revoked_at TEXT
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def create(self, name: str) -> dict:
        token = secrets.token_urlsafe(24)
        with closing(self._connect()) as conn, conn:
            invite_id = conn.execute(
                "INSERT INTO invites (name, token_hash, created_at) VALUES (?, ?, ?)",
                (name.strip(), _hash(token), _now()),
            ).lastrowid
        return {"id": invite_id, "name": name.strip(), "token": token}

    def verify(self, token: str) -> dict | None:
        """The active invite for this token (and mark it used), or None."""
        if not token:
            return None
        with closing(self._connect()) as conn, conn:
            row = conn.execute(
                "SELECT id, name FROM invites WHERE token_hash = ? AND revoked_at IS NULL",
                (_hash(token),),
            ).fetchone()
            if row is None:
                return None
            conn.execute("UPDATE invites SET last_used_at = ? WHERE id = ?", (_now(), row["id"]))
        return {"id": row["id"], "name": row["name"], "session_id": f"web:{row['id']}"}

    def list(self) -> list[dict]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT id, name, created_at, last_used_at, revoked_at FROM invites ORDER BY id DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def revoke(self, invite_id: int) -> bool:
        with closing(self._connect()) as conn, conn:
            changed = conn.execute(
                "UPDATE invites SET revoked_at = ? WHERE id = ? AND revoked_at IS NULL",
                (_now(), invite_id),
            ).rowcount
        return changed > 0
