from sqlalchemy import (
    Column,
    Integer,
    ForeignKey,
    DateTime,
    String,
    Text,
    UUID
)
import uuid
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core import Base


class Session(Base):
    __tablename__ = "sessions"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    title = Column(
        String,
        nullable=False
    )

    history_summary = Column(
        Text,
        nullable=True
    )

    unsummarized_count = Column(
        Integer,
        nullable=False,
        default=0
    )

    user = relationship(
        "User",
        back_populates="sessions"
    )

    messages = relationship(
        "Message",
        back_populates="session"
    )