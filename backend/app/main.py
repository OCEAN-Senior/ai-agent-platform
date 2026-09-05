from fastapi import Depends, FastAPI

from backend.app.api.public_router import router as public_router
from backend.app.api.v1.router import router as v1_router
from backend.app.core.config import settings
from backend.app.core.security import verify_api_key

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
)

app.include_router(public_router)
app.include_router(v1_router, dependencies=[Depends(verify_api_key)])
