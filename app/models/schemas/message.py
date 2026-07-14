from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: Optional[UUID] = Field(default=None, examples=[None])
    content: str = Field(..., min_length=1)


class MessageResponse(BaseModel):
    id: int
    session_id: UUID
    role: str
    content: str
    created_at: datetime
    agent_metadata: Optional[dict[str, Any]] = None

    class Config:
        from_attributes = True


class ChatResponse(BaseModel):
    session_id: UUID
    answer: str
    # user_message: MessageResponse
    # assistant_message: MessageResponse

 
class MessageItem(BaseModel):

    role: str
    content: str
 
    class Config:
        from_attributes = True
 
