from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    SmallInteger,
    String,
    Text,
    DateTime,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core import Base


class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(
        Integer,
        primary_key=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    message_id = Column(
        Integer,
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # 1 = Like
    # -1 = Dislike
    rating = Column(
        SmallInteger,
        nullable=False
    )


    reason_code = Column(
        String(50),
        nullable=True
    )

    comment = Column(
        Text,
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    user = relationship(
        "User",
        back_populates="feedbacks"
    )

    message = relationship(
        "Message",
        back_populates="feedbacks"
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "message_id",
            name="uq_feedback_user_message",
        ),
    )