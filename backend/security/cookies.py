from fastapi import Response
from security.auth_security import TOKEN_TTL

COOKIE_NAME = 'access_token'
_FLAGS = {
    "httponly":True,
    "secure":True,
    "samesite":"lax",
    "path":"/"
}

def set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(COOKIE_NAME, token, max_age=TOKEN_TTL, **_FLAGS)

def clear_auth_cookie(response:Response):
    response.delete_cookie(COOKIE_NAME,**_FLAGS)