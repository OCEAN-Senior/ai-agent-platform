import logging
import time
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles

from backend.app.api.public_router import router as public_router
from backend.app.api.v1.router import router as v1_router
from backend.app.core.config import settings
from backend.app.core.logging_config import configure_logging
from backend.app.core.security import verify_api_key

configure_logging()
logger = logging.getLogger("ai_agent_platform.request")


class LoggingMiddleware:
    """Pure ASGI middleware -- BaseHTTPMiddleware (the @app.middleware("http")
    shortcut) wraps each request in its own anyio task group, which conflicts
    with endpoints that spawn subprocesses with their own task groups (our MCP
    client) or return StreamingResponse, raising 'Attempted to exit a cancel
    scope that isn't the current task's'. This form avoids that entirely.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start = time.perf_counter()
        status_code = 500

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        await self.app(scope, receive, send_wrapper)
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "%s %s -> %s (%.1fms)",
            scope["method"],
            scope["path"],
            status_code,
            duration_ms,
        )


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
)

app.add_middleware(LoggingMiddleware)

app.include_router(public_router)
app.include_router(v1_router, dependencies=[Depends(verify_api_key)])

_FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
if _FRONTEND_DIR.is_dir():
    app.mount("/ui", StaticFiles(directory=str(_FRONTEND_DIR), html=True), name="frontend")
