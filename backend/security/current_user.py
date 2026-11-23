from fastapi import Cookie,HTTPException,status
from security.auth_security import decode_token

async def get_user(access_token: str | None = Cookie(default=None)) -> dict:
    payload = decode_token(access_token) if access_token else None
    if payload is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    return {
        "id": int(payload["sub"]),
        "username": payload["username"],
    }