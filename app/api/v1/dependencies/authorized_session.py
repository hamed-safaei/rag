# from fastapi import Depends, HTTPException
# from sqlalchemy.orm import Session

# from app.core import get_app_db
# from app.api.v1.dependencies.authorized_jwt import get_jwt_auth_user
# from app.repositories import get_session_by_id
# from app.models.schemas import ChatRequest


# def get_authorized_session(
#     req: ChatRequest,
#     db: Session = Depends(get_app_db),
#     current_user=Depends(get_jwt_auth_user),
# ):
#     if req.session_id is None:
#         return None

#     session = get_session_by_id(db, req.session_id)

#     if session is None:
#         raise HTTPException(status_code=404, detail="Session not found")

#     if session.user_id != current_user.id:
#         raise HTTPException(status_code=403, detail="Access denied")

#     return session