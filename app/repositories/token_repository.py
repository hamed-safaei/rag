from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from app.models.database import TokenModel


def create_refresh_token_record(
    db: Session,
    user_id: int,
    refresh_token: str,
    expires_days: int = 1
):
    token = TokenModel(
        user_id=user_id,
        refresh_token=refresh_token,
        expires_at=datetime.now(timezone.utc) + timedelta(days=expires_days),
        revoked=False
    )

    db.add(token)
    db.commit()
    db.refresh(token)
    return token


def get_refresh_token(db: Session, token: str):
    return db.query(TokenModel).filter(
        TokenModel.refresh_token == token,
        TokenModel.revoked == False
    ).first()


def revoke_token(
    db: Session,
    token: str
):
    db.query(TokenModel).filter(
        TokenModel.refresh_token == token
    ).update(
        {"revoked": True}
    )

    db.commit()