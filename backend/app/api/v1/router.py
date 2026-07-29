from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def root():
    return {
        "message": "AI Agent Platform API"
    }


@router.get("/health")
def health():
    return {
        "status": "ok"
    }