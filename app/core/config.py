import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

    DB_SERVER = os.getenv("DB_SERVER", "")
    DB_PORT = os.getenv("DB_PORT", "")
    DB_USER = os.getenv("DB_USER", "")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_DATABASE = os.getenv("DB_DATABASE", "")

    JWT_SECRET_KEY = os.getenv("SECRET_KEY", "")

    NEO4J_URI = os.getenv("NEO4J_URI", "")
    NEO4J_USER = os.getenv("NEO4J_USER", "")
    NEO4J_PASS = os.getenv("NEO4J_PASS", "")

    LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")
    LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "")

settings = Settings()