from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core import get_app_db
from app.api.v1.dependencies import get_jwt_auth_user , get_authorized_session
from app.models.schemas import ChatRequest, ChatResponse
from app.repositories import create_session , create_message
from app.agent.agent import run_agent

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/send", response_model=ChatResponse)
def send_message(
    req: ChatRequest,
    db: Session = Depends(get_app_db),
    current_user=Depends(get_jwt_auth_user),
    session=Depends(get_authorized_session),
):
    # اگر session_id در ورودی وجود نداشت، یک session جدید برای همین کاربر ساخته می‌شود
    if session is None:
        session = create_session(db, user_id=current_user.id)

    # ذخیره پیام کاربر
    user_message = create_message(
        db=db,
        session_id=session.id,
        role="user",
        content=req.content,
    )

    # اجرای agent برای گرفتن پاسخ
    agent_result = run_agent(query=req.content)

    # run_agent بر اساس GraphState یک dict برمی‌گرداند که فیلد answer دارد
    if isinstance(agent_result, dict):
        answer = agent_result.get("answer", "")
    else:
        answer = str(agent_result)

    # ذخیره پاسخ agent
    assistant_message = create_message(
        db=db,
        session_id=session.id,
        role="agent",
        content=answer,
    )

    return ChatResponse(
        session_id=session.id,
        answer=answer,
        user_message=user_message,
        assistant_message=assistant_message,
    )