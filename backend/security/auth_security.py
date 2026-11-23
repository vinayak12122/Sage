import os
import time
import jwt

import asyncio
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError,VerifyMismatchError
# from dotenv import load_dotenv

# load_dotenv() 

_ph = PasswordHasher()

DUMMY_HASH = _ph.hash("not-a-real-password")

JWT_SECRET = os.getenv("JWT_SECRET")
TOKEN_TTL = 60*60*24

def create_token(user_id:int,username:str) -> str:
    now = int(time.time())
    payload = {"sub":str(user_id),"username":username,"iat":now,"exp":now+TOKEN_TTL}

    return jwt.encode(payload,JWT_SECRET,algorithm="HS256")

def decode_token(token:str) -> dict | None:
    try:
        return jwt.decode(token,JWT_SECRET,algorithms=["HS256"])
    except jwt.PyJWTError:
        return None

async def hash_password(password:str) -> str:
    return await asyncio.to_thread(_ph.hash,password)

async def verify_password(password:str,hash_password:str) -> bool:
    try:
        return await asyncio.to_thread(_ph.verify,hash_password,password)
    except (VerifyMismatchError,InvalidHashError):
        return False

