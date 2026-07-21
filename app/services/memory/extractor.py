from sqlalchemy import desc
from app.models.database import Message ,Session


def build_conversation(db, session_id, limit: int) -> str:
    messages = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(desc(Message.created_at))
        .limit(limit * 2)
        .all()
    )

    messages.reverse()

    return "\n\n".join(
        f"{m.role.upper()}:\n{m.content}"
        for m in messages
    )


def get_history_summary(db, session_id) -> str:
    session = (
        db.query(Session.history_summary)
        .filter(Session.id == session_id)
        .first()
    )

    if session is None:
        return ""

    return session.history_summary or ""