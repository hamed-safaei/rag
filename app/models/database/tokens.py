from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from datetime import datetime, timezone

from app.core import Base
from sqlalchemy.orm import relationship


class TokenModel(Base):
    __tablename__ = "tokens"

    id = Column(Integer, primary_key=True, index=True)

    refresh_token = Column(String, unique=True, index=True, nullable=False)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    expires_at = Column(DateTime, nullable=False)

    revoked = Column(Boolean, default=False)

    user = relationship("User")