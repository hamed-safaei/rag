from sqlalchemy.orm import Session

from app.models.database.message import Message


def create_message(
    db: Session,
    session_id,
    role: str,
    content: str,
    agent_metadata: dict | None = None,
) -> Message:
    """
    یک رکورد جدید در جدول messages ایجاد می‌کند.

    نکته: بر اساس ستون‌های اعلام‌شده‌ی جدول messages، این جدول ستون
    user_id ندارد (فقط session_id, role, content, agent_metadata,
    created_at, id). ارتباط پیام با کاربر از طریق session (که خودش
    user_id دارد) برقرار می‌شود. اگر واقعاً ستون user_id هم در جدول
    وجود دارد، کافی‌ست پارامتر user_id را به این تابع و مدل Message
    اضافه کنید.
    """
    new_message = Message(
        session_id=session_id,
        role=role,
        content=content,
        agent_metadata=agent_metadata,
    )
    db.add(new_message)
    db.commit()
    db.refresh(new_message)
    return new_message


def get_messages_by_session_id(db: Session, session_id) -> list[Message]:
    return (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.created_at.asc())
        .all()
    )