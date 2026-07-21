from redis import Redis
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database.database import AppSessionLocal
from app.models.database import Session as ChatSession

from app.services.memory.extractor import (
    build_conversation,
    get_history_summary,
)
from app.services.memory.summarizer import summarize

redis = Redis(
    host="localhost",
    port=6379,
    decode_responses=True,
    socket_timeout=None,

)


while True:
    job = redis.brpop("summary_queue", timeout=0)

    _, session_id = job

    db = AppSessionLocal()

    try:
        session = (
            db.query(ChatSession)
            .filter(ChatSession.id == session_id)
            .first()
        )

        if session is None:
            continue

        if session.unsummarized_count == 0:
            continue

        history_summary = get_history_summary(
            db,
            session_id,
        )

        conversation = build_conversation(
            db=db,
            session_id=session_id,
            limit=session.unsummarized_count,
        )

        summary = summarize(
            conversation=conversation,
            history_summary=history_summary,
        )

        session.history_summary = summary
        session.unsummarized_count = 0

        db.commit()

        print(f"✔ summarized {session_id}")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()