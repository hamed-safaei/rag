from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from app.core import get_app_db
from app.models.database import User , TokenModel
from app.core import verify_password


security = HTTPBearer(scheme_name="Token")


def get_auth_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_app_db)
):
    
    token_obj = db.query(TokenModel).filter_by(refresh_token=credentials.credentials).one_or_none()

    if not token_obj :
        raise HTTPException(
            status_code=401,
            detail="credentials are not provided",
        )
    #other logic

    return token_obj.user


