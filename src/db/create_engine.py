from sqlalchemy import create_engine, text
from sqlmodel import Session
from core.config import settings

engine = create_engine(
    settings.db_url, pool_size=10, max_overflow=20, pool_pre_ping=True
)


def check_db():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print("DB FAILED:", e)
        return False


def get_session():
    return Session(engine)
