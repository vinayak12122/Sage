from fastapi import APIRouter,Depends,HTTPException,status,Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from database.user import User
from models.auth import Credentials
from security.auth_security import create_token,hash_password,verify_password,DUMMY_HASH
from security.cookies import set_auth_cookie,clear_auth_cookie
from security.current_user import get_user


router = APIRouter(prefix='/auth')

@router.post('/signup',status_code=status.HTTP_201_CREATED)
async def signup(body:Credentials,response:Response,db:AsyncSession=Depends(get_db)):
    user = User(
        username=body.username.lower(),
        password_hash=await hash_password(body.password),
    )

    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT,"Username already taken")
    set_auth_cookie(response,create_token(user.id,user.username))
    return {"message":"Created"}

@router.post('/login',status_code=status.HTTP_200_OK)
async def login(body:Credentials,response:Response,db:AsyncSession=Depends(get_db)):
    user = (
        await db.execute(
            select(User.id,User.username,User.password_hash).where(
                User.username == body.username.lower()
            )
        )
    ).first()

    ok = await verify_password(body.password,user.password_hash if user else DUMMY_HASH)

    if user is None or not ok:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")
    set_auth_cookie(response,create_token(user.id,user.username))
    return {"message":"Successful"}

@router.post('/logout',status_code=status.HTTP_204_NO_CONTENT)
async def logout(response:Response):
    clear_auth_cookie(response)

@router.get("/me")
async def me(user:dict = Depends(get_user)):
    return user