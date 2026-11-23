import asyncio
import uuid
from contextlib import aclosing

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db, SessionLocal
from database.chat import Message, ChatSession
from models.chat import ChatRequest, MessageOut, SessionPreview
from security.current_user import get_user
from llm.engine import engine

router = APIRouter(prefix="/chat")


async def get_owned_session(session_id: uuid.UUID, user: dict, db: AsyncSession) -> ChatSession:
    session = await db.get(ChatSession, session_id)
    if session is None:
        session = ChatSession(id=session_id, user_id=user["id"])
        db.add(session)
        await db.commit()
        return session
    if session.user_id != user["id"]:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    return session


@router.get("", response_model=list[SessionPreview])
async def list_chats(user: dict = Depends(get_user), db: AsyncSession = Depends(get_db)):
    first_msg = (
        select(Message.session_id, func.min(Message.id).label("mid"))
        .where(Message.role == "user", Message.user_id == user["id"])
        .group_by(Message.session_id)
        .subquery()
    )
    result = await db.execute(
        select(ChatSession.id, ChatSession.created_at, Message.content)
        .join(first_msg, first_msg.c.session_id == ChatSession.id)
        .join(Message, Message.id == first_msg.c.mid)
        .where(ChatSession.user_id == user["id"])
        .order_by(ChatSession.created_at.desc())
    )
    return [
        {"session_id": r.id, "created_at": r.created_at, "preview": r.content[:60]}
        for r in result.all()
    ]


@router.get("/{session_id}", response_model=list[MessageOut])
async def get_chat(session_id: uuid.UUID, user: dict = Depends(get_user), db: AsyncSession = Depends(get_db)):
    session = await db.get(ChatSession, session_id)
    if session is None or session.user_id != user["id"]:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    result = await db.execute(
        select(Message).where(Message.session_id == session_id).order_by(Message.id)
    )
    return result.scalars().all()


async def save_reply(session_id: uuid.UUID, user_id: int, content: str):
    async with SessionLocal() as db:
        db.add(Message(session_id=session_id, user_id=user_id, role="assistant", content=content))
        await db.commit()


async def stream_and_save(session_id: uuid.UUID, user_id: int):
    reply = ""
    try:
        async with SessionLocal() as db:
            rows = await db.execute(
                select(Message.role, Message.content)
                .where(Message.session_id == session_id).order_by(Message.id)
            )
            history = [{"role": r, "content": c} for r, c in rows.all()]
        async with aclosing(engine.stream(history)) as gen:
            async for chunk in gen:
                reply += chunk
                yield chunk
    finally:
        if reply.strip():
            await asyncio.shield(save_reply(session_id, user_id, reply.strip()))



@router.post("/{session_id}")
async def post_chat(session_id: uuid.UUID, body: ChatRequest,user: dict = Depends(get_user), db: AsyncSession = Depends(get_db)):
    if engine.busy():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "The model is busy, try again in a few seconds",headers={"Retry-After": "5"})
    await get_owned_session(session_id, user, db)
    db.add(Message(session_id=session_id, user_id=user["id"], role="user", content=body.text))
    await db.commit()

    return StreamingResponse(
        stream_and_save(session_id, user["id"]),
        media_type="text/plain; charset=utf-8",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )