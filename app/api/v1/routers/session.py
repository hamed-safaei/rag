from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session as DBSession
from app.api.v1.dependencies import get_jwt_auth_user
from app.core import get_app_db
from app.models.schemas import( 
SessionSummary , SessionTitleUpdate ,MessageItem
# MessageRead 
)
from uuid import UUID
from sqlalchemy.orm import Session
from app.repositories import (
    get_session_by_id,
    get_sessions_by_user_id,
    get_messages_by_session_id ,
    delete_session ,
    update_session_title
    )
# from app.agent.schemas.states import message_read_mapper



router = APIRouter(
    prefix="/sessions",
    tags=["Session"]
)




def _get_authorized_session(db: Session, session_id: int, user_id: int):
    session =  get_session_by_id(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return session





@router.get("/", response_model=list[SessionSummary])
def get_user_sessions(
    db: Session = Depends(get_app_db),
    current_user=Depends(get_jwt_auth_user)
):
    return  get_sessions_by_user_id(db, current_user.id)





# @router.get("/{session_id}/messages", response_model=list[MessageRead])
# def get_session_messages(
#     session_id: UUID,
#     db: Session = Depends(get_app_db),
#     current_user=Depends(get_jwt_auth_user)
# ):
#     _get_authorized_session(db, session_id, current_user.id)
#     messages = get_messages_by_session_id(
#         db,
#         session_id,
#     )

#     return [
#         message_read_mapper(message)
#         for message in messages
#     ]




@router.patch("/{session_id}", response_model=SessionSummary)
def update_title(
    session_id: UUID,
    body: SessionTitleUpdate,
    db: Session = Depends(get_app_db),
    current_user=Depends(get_jwt_auth_user)
):
    _get_authorized_session(db, session_id, current_user.id)
    updated =  update_session_title(db, session_id, body.title)
    return updated




@router.delete("/{session_id}", status_code=204)
def deletesession(
    session_id: UUID,
    db: Session = Depends(get_app_db),
    current_user=Depends(get_jwt_auth_user)
):
    _get_authorized_session(db, session_id, current_user.id)
    delete_session(db, session_id)






@router.get("/{session_id}/messages", response_model=list[MessageItem])
def get_session_messages(
    session_id: UUID,
    db: Session = Depends(get_app_db),
    current_user=Depends(get_jwt_auth_user),
):
    session = get_session_by_id(db, session_id)

    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    messages = get_messages_by_session_id(db, session_id)

    # به ترتیب از اولین پیام به آخرین (get_messages_by_session_id از قبل
    # با order_by(created_at.asc()) مرتب شده است)
    return [MessageItem(role=m.role, content=m.content) for m in messages]