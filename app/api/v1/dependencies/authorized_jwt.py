from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core import get_app_db
from app.models.database import User
from app.auth.jwt_auth import decode_access_token


def get_jwt_auth_user(
    request: Request,
    db: Session = Depends(get_app_db)
):
    access_token = request.cookies.get(
        "access_token"
    )

    if not access_token:
        raise HTTPException(
            status_code=401,
            detail="Access token not found"
        )

    payload = decode_access_token(
        access_token
    )

    user_id = payload["user_id"]

    user = db.query(User).filter_by(
        id=user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )

    return user