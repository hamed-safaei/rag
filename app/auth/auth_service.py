from fastapi import HTTPException , Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone

from app import repositories
from app.core import hash_password, verify_password
from app.auth.jwt_auth import (
    generate_access_token,
    generate_refresh_token,
    decode_refresh_token
)

from app.models.database import TokenModel
import secrets


def register_user(
    db: Session,
    username: str,
    password: str
):
    existing_user = repositories.get_user_by_username(
        db,
        username
    )

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Username already exists"
        )

    hashed_password = hash_password(password)

    new_user = repositories.create_user(
        db=db,
        username=username,
        password_hash=hashed_password
    )

    return new_user


def generate_token(length: int = 32):
    return secrets.token_hex(length)


def login_token(
    db: Session,
    username: str,
    password: str
):
    db_user = repositories.get_user_by_username(
        db,
        username
    )

    if not db_user:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    if not verify_password(
        password,
        db_user.password_hash
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    expires_at = (
        datetime.now(timezone.utc)
        + timedelta(days=7)
    )

    token_obj = TokenModel(
        user_id=db_user.id,
        refresh_token=generate_token(),
        expires_at=expires_at,
        revoked=False
    )

    db.add(token_obj)
    db.commit()
    db.refresh(token_obj)

    return JSONResponse(
        content={
            "detail": "logged in successfully",
            "token": token_obj.refresh_token
        }
    )




# def login_jwt(
#     db: Session,
#     username: str,
#     password: str
# ):
#     db_user = repositories.get_user_by_username(
#         db,
#         username
#     )

#     if not db_user:
#         raise HTTPException(
#             status_code=401,
#             detail="Invalid credentials"
#         )

#     if not verify_password(
#         password,
#         db_user.password_hash
#     ):
#         raise HTTPException(
#             status_code=401,
#             detail="Invalid credentials"
#         )

#     access_token = generate_access_token(
#         db_user.id
#     )

#     refresh_token = generate_refresh_token(
#         db_user.id
#     )

#     repositories.create_refresh_token_record(
#         db=db,
#         user_id=db_user.id,
#         refresh_token=refresh_token
#     )

#     return JSONResponse(
#         content={
#             "detail": "logged in successfully",
#             "access_token": access_token,
#             "refresh_token": refresh_token
#         }
#     )




def login_jwt(
    db: Session,
    username: str,
    password: str
):
    db_user = repositories.get_user_by_username(
        db,
        username
    )

    if not db_user:
        raise HTTPException(
            status_code=401,
            detail="Invalid Username Or Password"
        )

    if not verify_password(
        password,
        db_user.password_hash
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid Username Or Password"
        )

    access_token = generate_access_token(
        db_user.id
    )

    refresh_token = generate_refresh_token(
        db_user.id
    )

    repositories.create_refresh_token_record(
        db=db,
        user_id=db_user.id,
        refresh_token=refresh_token
    )

    response = JSONResponse(
        content={
            "detail": "logged in successfully",
            "access_token": access_token,
            "refresh_token": refresh_token
        }
    )

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,      
        samesite="lax",
        max_age=60 * 120
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,     
        samesite="lax",
        max_age= 60 * 60 * 24
        
    )

    return response



# def refresh_access_token(
#     token: str
# ):
#     user_id = decode_refresh_token(
#         token
#     )

#     access_token = generate_access_token(
#         user_id
#     )

#     return JSONResponse(
#         content={
#             "access_token": access_token
#         }
#     )






def refresh_access_token(
    request: Request,
    db
):
    refresh_token = request.cookies.get(
        "refresh_token"
    )

    if not refresh_token:
        raise HTTPException(
            status_code=401,
            detail="Refresh token not found"
        )

    token_record = repositories.get_refresh_token(
        db,
        refresh_token
    )

    if not token_record:
        raise HTTPException(
            status_code=401,
            detail="Invalid refresh token"
        )

    if token_record.revoked:
        raise HTTPException(
            status_code=401,
            detail="Refresh token revoked"
        )

    user_id = decode_refresh_token(
        refresh_token
    )

    access_token = generate_access_token(
        user_id
    )

    response = JSONResponse(
        content={
            "detail": "access token refreshed"
        }
    )

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,      # localhost
        samesite="lax",
        max_age=60 * 5
    )

    return response







def logout_user(
    request: Request,
    db
):
    refresh_token = request.cookies.get(
        "refresh_token"
    )

    if refresh_token:

        token_record = repositories.get_refresh_token(
            db,
            refresh_token
        )

        if token_record:
            repositories.revoke_token(
                db,
                refresh_token
            )

    response = JSONResponse(
        content={
            "detail": "Logged out successfully"
        }
    )

    response.delete_cookie(
        "access_token"
    )

    response.delete_cookie(
        "refresh_token"
    )

    return response