from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    JSON,
    DateTime ,
    UUID
)

from sqlalchemy.orm import relationship
from datetime import datetime

from app.core import Base


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id"),
        nullable=False,
        index=True
    )
    role = Column(
        String,
        nullable=False
    )
    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )
    content = Column(
        String,
        nullable=True
    )
    agent_metadata = Column(
        JSON,
        nullable=True
    )
    session = relationship(
        "Session",
        back_populates="messages"
    )


    feedbacks = relationship(
    "Feedback",
    back_populates="message",
    cascade="all, delete-orphan"
    )