"""Admin view of every conversation and every cloud request -- for the admin only.

Protected by HTTP Basic auth against ADMIN_PASSWORD (any username). With no password set
the whole panel answers 503, so it can't be opened by accident.
"""
import secrets
import sqlite3
from contextlib import closing
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from backend.app.core.config import settings
from backend.app.services.invites import InviteStore
from backend.app.services.telegram_access import TelegramAccess

_security = HTTPBasic(realm="AI Agent Platform admin")
_ADMIN_PAGE = Path(__file__).resolve().parents[3] / "frontend" / "admin.html"


def require_admin(credentials: HTTPBasicCredentials = Depends(_security)) -> None:
    if not settings.ADMIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin panel is disabled: set ADMIN_PASSWORD in .env",
        )
    if not secrets.compare_digest(credentials.password.encode(), settings.ADMIN_PASSWORD.encode()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Wrong password",
            headers={"WWW-Authenticate": 'Basic realm="AI Agent Platform admin"'},
        )


router = APIRouter(prefix="/admin", dependencies=[Depends(require_admin)])


def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(Path(settings.DATA_DIR) / "conversations.db", timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


@router.get("", include_in_schema=False)
def admin_page() -> FileResponse:
    return FileResponse(_ADMIN_PAGE)


@router.get("/api/sessions")
def list_sessions() -> list[dict]:
    with closing(_db()) as conn:
        rows = conn.execute(
            """
            SELECT s.session_id, s.user_name, s.created_at, s.updated_at,
                   COUNT(m.id) AS messages,
                   (SELECT COUNT(*) FROM cloud_requests c
                     WHERE c.session_id = s.session_id AND c.status = 'sent') AS cloud_sent
            FROM sessions s LEFT JOIN messages m ON m.session_id = s.session_id
            GROUP BY s.session_id ORDER BY s.updated_at DESC
            """
        ).fetchall()
    return [dict(r) for r in rows]


@router.get("/api/sessions/{session_id}/messages")
def session_messages(session_id: str) -> list[dict]:
    with closing(_db()) as conn:
        start = conn.execute(
            "SELECT context_start_id FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        rows = conn.execute(
            "SELECT id, role, content, created_at FROM messages WHERE session_id = ? ORDER BY id",
            (session_id,),
        ).fetchall()
    context_start = start["context_start_id"] if start else 0
    # cleared=True marks messages from before the user's last /clear (no longer in the AI's context).
    return [{**dict(r), "cleared": r["id"] <= context_start} for r in rows]


@router.get("/api/cloud-requests")
def cloud_requests(limit: int = 200) -> list[dict]:
    with closing(_db()) as conn:
        rows = conn.execute(
            """
            SELECT c.id, c.session_id, s.user_name, c.status, c.model, c.original_json, c.masked_json,
                   c.response_masked, c.response, c.created_at
            FROM cloud_requests c LEFT JOIN sessions s ON s.session_id = c.session_id
            ORDER BY c.id DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


_invites = InviteStore()
_telegram = TelegramAccess()


def _base_urls() -> list[str]:
    return [u.strip().rstrip("/") for u in settings.WEBCHAT_BASE_URLS.split(",") if u.strip()]


@router.get("/api/telegram-users")
def telegram_users() -> list[dict]:
    return _telegram.list()


@router.post("/api/telegram-users/{user_id}")
def telegram_user_set(user_id: int, body: dict) -> dict:
    if not _telegram.set_status(user_id, body.get("status", "")):
        raise HTTPException(status_code=404, detail="User not found or status invalid")
    return {"user_id": user_id, "status": body["status"]}


@router.get("/api/invites")
def invites() -> dict:
    return {"base_urls": _base_urls(), "invites": _invites.list()}


@router.post("/api/invites")
def invite_create(body: dict) -> dict:
    name = str(body.get("name", "")).strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    invite = _invites.create(name)
    # The token is only ever shown here, at creation time.
    invite["links"] = [f"{base}/?t={invite['token']}" for base in _base_urls()]
    return invite


@router.post("/api/invites/{invite_id}/revoke")
def invite_revoke(invite_id: int) -> dict:
    if not _invites.revoke(invite_id):
        raise HTTPException(status_code=404, detail="Invite not found or already revoked")
    return {"id": invite_id, "revoked": True}
