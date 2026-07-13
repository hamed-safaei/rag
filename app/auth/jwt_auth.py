from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from app.core import get_app_db
from app.models.database import User , TokenModel
from app.core import verify_password
from app.core import settings

import jwt
from jwt import DecodeError , ExpiredSignatureError , InvalidSignatureError
from datetime import datetime, timedelta, timezone


def generate_access_token(user_id: int, expires_in : int = 60*120) -> str:
    now = datetime.now(timezone.utc)

    payload = {
        "user_id": user_id,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
        "type" : "access"
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm="HS256"
    )    


def generate_refresh_token(user_id: int, expires_in : int = 3600 * 24) -> str:
    now = datetime.now(timezone.utc)

    payload = {
        "user_id": user_id,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
        "type" : "refresh"
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm="HS256"
    )    




def decode_refresh_token(token) :
 try:
      decoded = jwt.decode(token , settings.JWT_SECRET_KEY ,algorithms="HS256")
      user_id = decoded.get("user_id" , None)

      if not user_id :
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED , detail="Authentication Failed , user id not in payload")
        
      if decoded.get("type") != "refresh" :
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED , detail="Authentication Failed , invalid token type")

      if datetime.fromtimestamp(decoded.get("exp")) < datetime.now() :
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED , detail="Authentication Failed , token expired")
  
      return user_id


 except InvalidSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED , detail="Authentication Failed , InvalidSignature")
 except DecodeError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED , detail="Authentication Failed , Decode failed")
 except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED , detail=f"Authentication Failed , {e}")




def decode_access_token(token: str):
    try:
        decoded = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=["HS256"]
        )

        if decoded.get("type") != "access":
            raise HTTPException(
                status_code=401,
                detail="Invalid token type"
            )

        return decoded

    except ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token expired"
        )

    except InvalidSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Invalid signature"
        )

    except DecodeError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )