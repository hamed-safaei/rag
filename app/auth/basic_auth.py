from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session
from app.core import get_app_db
from app.models.database import User
from app.core import verify_password

security = HTTPBasic()


def get_current_username(
    credentials: HTTPBasicCredentials = Depends(security),
    db: Session = Depends(get_app_db)
):
    user = db.query(User).filter_by(username=credentials.username).one_or_none()

    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )

    return user


