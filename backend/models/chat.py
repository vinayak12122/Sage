from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
import uuid

class ChatRequest(BaseModel):
    text: str = Field(min_length=1, max_length=8000)

class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    role: str
    content: str
    created_at: datetime

class SessionPreview(BaseModel):
    session_id: uuid.UUID
    created_at: datetime
    preview: str