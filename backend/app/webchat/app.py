"""Public-facing web chat, reachable from the office network (and later a tunnel).

Deliberately small: it serves the chat page and a handful of chat endpoints, authenticates
every request with a personal invite (cookie), and forwards to the platform API over the
internal Docker network. It stores nothing itself and exposes no admin or raw API routes.
Run: uvicorn backend.app.webchat.app:app --host 0.0.0.0 --port 8090
"""
import time
from collections import defaultdict, deque
from pathlib import Path

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field

from backend.app.core.config import settings

COOKIE = "wc_token"
COOKIE_MAX_AGE = 180 * 24 * 3600
MAX_MESSAGE_CHARS = 4000
MAX_UPLOAD_B64_CHARS = 28_000_000  # ~20 MB file
RATE_LIMIT = 30  # requests per minute per person
_PAGE = Path(__file__).resolve().parents[3] / "frontend" / "webchat.html"
_INVALID = """<!doctype html><html lang="uz"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Havola yaroqsiz</title>
<style>body{font:16px system-ui,sans-serif;display:grid;place-items:center;min-height:90vh;margin:0;padding:16px;
background:#f6f6f4;color:#1f2328}@media(prefers-color-scheme:dark){body{background:#16181d;color:#e8e6e1}}</style></head>
<body><div><h2>🔒 Havola yaroqsiz yoki bekor qilingan</h2>
<p>Iltimos, administratordan yangi shaxsiy havola so'rang.</p></div></body></html>"""

app = FastAPI(title="AI yordamchi", docs_url=None, redoc_url=None, openapi_url=None)
_hits: dict[int, deque] = defaultdict(deque)


async def _platform(method: str, path: str, json: dict | None = None, timeout: float = 300.0) -> httpx.Response:
    headers = {"Authorization": f"Bearer {settings.PLATFORM_API_KEY}"} if settings.PLATFORM_API_KEY else {}
    async with httpx.AsyncClient(timeout=timeout) as client:
        return await client.request(method, f"{settings.PLATFORM_URL}{path}", json=json, headers=headers)


async def _verify(token: str | None) -> dict | None:
    if not token:
        return None
    response = await _platform("POST", "/api/v1/invites/verify", {"token": token}, timeout=10.0)
    return response.json() if response.status_code == 200 else None


async def current_user(request: Request) -> dict:
    user = await _verify(request.cookies.get(COOKIE))
    if user is None:
        raise HTTPException(status_code=401, detail="Havola yaroqsiz")
    hits = _hits[user["id"]]
    now = time.monotonic()
    while hits and now - hits[0] > 60:
        hits.popleft()
    if len(hits) >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Juda ko'p so'rov. Bir daqiqadan keyin urinib ko'ring.")
    hits.append(now)
    return user


def _forward(response: httpx.Response) -> dict:
    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", "Xatolik")
        except ValueError:
            detail = "Xatolik"
        raise HTTPException(status_code=response.status_code, detail=detail)
    return response.json()


@app.get("/healthz", include_in_schema=False)
def healthz() -> dict:
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
async def index(request: Request, t: str | None = None):
    if t:
        # Opening the personal link: remember it in a cookie, then drop the token from the URL bar.
        if await _verify(t) is None:
            return HTMLResponse(_INVALID, status_code=403)
        response = RedirectResponse("/", status_code=303)
        https = request.headers.get("x-forwarded-proto", request.url.scheme) == "https"
        response.set_cookie(COOKIE, t, max_age=COOKIE_MAX_AGE, httponly=True, samesite="lax", secure=https)
        return response
    if await _verify(request.cookies.get(COOKIE)) is None:
        return HTMLResponse(_INVALID, status_code=403)
    return FileResponse(_PAGE, headers={"Cache-Control": "no-store"})


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)


class UploadIn(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_base64: str = Field(max_length=MAX_UPLOAD_B64_CHARS)


class CloudIn(BaseModel):
    request_id: int


@app.get("/api/me")
async def me(user: dict = Depends(current_user)) -> dict:
    return {"name": user["name"]}


@app.get("/api/history")
async def history(user: dict = Depends(current_user)) -> dict:
    return _forward(await _platform("GET", f"/api/v1/chat/{user['session_id']}/history"))


@app.post("/api/chat")
async def chat(body: ChatIn, user: dict = Depends(current_user)) -> dict:
    data = _forward(await _platform("POST", "/api/v1/chat", {
        "message": body.message,
        "session_id": user["session_id"],
        "user_name": f"{user['name']} (veb)",
        "use_documents": True,
    }))
    return {"response": data["response"]}


@app.post("/api/clear")
async def clear(user: dict = Depends(current_user)) -> dict:
    return _forward(await _platform("DELETE", f"/api/v1/chat/{user['session_id']}/history"))


@app.post("/api/upload")
async def upload(body: UploadIn, user: dict = Depends(current_user)) -> dict:
    return _forward(await _platform("POST", "/api/v1/files/ingest", {
        "filename": body.filename,
        "content_base64": body.content_base64,
        "session_id": user["session_id"],
        "user_name": f"{user['name']} (veb)",
    }, timeout=600.0))


@app.post("/api/cloud/preview")
async def cloud_preview(user: dict = Depends(current_user)) -> dict:
    return _forward(await _platform("POST", "/api/v1/cloud/preview", {"session_id": user["session_id"]}))


@app.post("/api/cloud/send")
async def cloud_send(body: CloudIn, user: dict = Depends(current_user)) -> dict:
    return _forward(await _platform("POST", "/api/v1/cloud/send",
                                    {"request_id": body.request_id, "session_id": user["session_id"]}))


@app.post("/api/cloud/cancel")
async def cloud_cancel(body: CloudIn, user: dict = Depends(current_user)) -> dict:
    return _forward(await _platform("POST", "/api/v1/cloud/cancel",
                                    {"request_id": body.request_id, "session_id": user["session_id"]}))
