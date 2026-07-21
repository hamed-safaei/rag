from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core import get_app_db
from app.api.v1.dependencies import get_jwt_auth_user, get_authorized_session
from app.models.schemas import ChatRequest, ChatResponse
from app.repositories import create_session, create_message ,increment_unsummarized_count
from app.agent.agent import run_agent
from redis import Redis

redis = Redis(
    host="localhost",
    port=6379,
    decode_responses=True
)

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/send", response_model=ChatResponse)
def send_message(
    req: ChatRequest,
    db: Session = Depends(get_app_db),
    current_user=Depends(get_jwt_auth_user),
    session=Depends(get_authorized_session),
):
    if session is None:
        session = create_session(db, user_id=current_user.id)

    user_message = create_message(
        db=db,
        session_id=session.id,
        role="user",
        content=req.content,
    )
    

    agent_result = run_agent(
        query=req.content,
        session_id=str(session.id),
        db=db,
    )
    if isinstance(agent_result, dict):
        answer = agent_result.get("answer", "")
    else:
        answer = str(agent_result)

    assistant_message = create_message(
        db=db,
        session_id=session.id,
        role="agent",
        content=answer,
    )
    
    counter = increment_unsummarized_count(db, session.id)
    if counter == 5:
        result = redis.lpush("summary_queue", str(session.id))

    return ChatResponse(
        session_id=session.id,
        answer=answer,
        user_message=user_message,
        assistant_message=assistant_message,
    )