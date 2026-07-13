from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core import settings

APP_DATABASE_URL = (
    f"postgresql://{settings.DB_USER}:"
    f"{settings.DB_PASSWORD}@"
    f"{settings.DB_SERVER}:"
    f"{settings.DB_PORT}/"
    f"{settings.DB_DATABASE}"
)

app_engine = create_engine(
    APP_DATABASE_URL,
    echo=True,
)

AppSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=app_engine,
)

Base = declarative_base()


def get_app_db():
    db = AppSessionLocal()
    try:
        yield db
    finally:
        db.close()