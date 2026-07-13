from typing import Optional, Sequence
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.database import User


def create_user(
    db: Session,
    username: str,
    password_hash: str
) -> User:

    user = User(
        username=username,
        password_hash=password_hash
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user

def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.get(User, user_id)


def get_user_by_username(
    db: Session,
    username: str
) -> Optional[User]:

    stmt = (
        select(User)
        .where(User.username == username)
    )

    return db.execute(stmt).scalar_one_or_none()


def list_users(
    db: Session,
    limit: int = 100,
    offset: int = 0
) -> Sequence[User]:

    stmt = (
        select(User)
        .order_by(User.id)
        .limit(limit)
        .offset(offset)
    )

    return db.execute(stmt).scalars().all()