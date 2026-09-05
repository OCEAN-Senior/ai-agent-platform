from fastapi import Header, HTTPException

from backend.app.core.config import settings


def verify_api_key(authorization: str | None = Header(default=None)) -> None:
    """Require a valid `Authorization: Bearer <key>` header.

    If API_KEYS is unset, auth is disabled (local dev convenience) --
    this MUST be set in any environment reachable outside localhost.
    """
    valid_keys = {key.strip() for key in settings.API_KEYS.split(",") if key.strip()}
    if not valid_keys:
        return

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header.")

    token = authorization.removeprefix("Bearer ").strip()
    if token not in valid_keys:
        raise HTTPException(status_code=401, detail="Invalid API key.")
