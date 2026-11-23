import uuid
from datetime import datetime

from sqlalchemy import String,Text,ForeignKey,func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped,mapped_column
from database.session import Base

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id:Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),primary_key=True)
    user_id:Mapped[int] = mapped_column(ForeignKey("users.id"),index=True)
    created_at:Mapped[datetime] = mapped_column(server_default=func.now())


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chat_sessions.id"), index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())