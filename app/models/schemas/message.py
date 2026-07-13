from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """
    ورودی endpoint ارسال پیام.

    نکته مهم: در جدول messages ستون session_id از نوع uuid است.
    اگر در پروژه‌ی شما session.id از نوع int (autoincrement) است،
    این تایپ را به int تغییر دهید تا با مدل SessionModel هم‌خوان شود.
    """
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
 
