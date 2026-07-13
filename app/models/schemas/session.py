
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from uuid import UUID


class SessionSummary(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class SessionInfo(BaseModel):
    id: UUID
    title: str


class SessionTitleUpdate(BaseModel):
    title: str