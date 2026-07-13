from sqlalchemy.orm import Session
from app.models.database.session import Session as SessionModel
from app.models.database.message import Message


def create_session(db: Session, user_id: int) -> SessionModel:
    new_session = SessionModel(
        user_id=user_id,
        title="text"
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return new_session


def get_session_by_id(db: Session, session_id: int) -> SessionModel | None:
    return db.query(SessionModel).filter(SessionModel.id == session_id).first()


def get_sessions_by_user_id(db: Session, user_id: int) -> list[SessionModel]:
    return (
        db.query(SessionModel)
        .filter(SessionModel.user_id == user_id)
        .order_by(SessionModel.created_at.desc())
        .all()
    )


def update_session_title(
    db: Session,
    session_id: int,
    new_title: str
) -> SessionModel:
    session = get_session_by_id(db, session_id)
    session.title = new_title
    db.commit()
    db.refresh(session)
    return session


def delete_session(db: Session, session_id: int) -> None:
    db.query(Message).filter(Message.session_id == session_id).delete()
    db.query(SessionModel).filter(SessionModel.id == session_id).delete()
    db.commit()