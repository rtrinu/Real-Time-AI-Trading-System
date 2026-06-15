from sqlalchemy import create_engine, text
from sqlmodel import Session
from sqlalchemy.orm import sessionmaker
from core.config import settings

engine = create_engine(
    settings.db_url, pool_size=10, max_overflow=20, pool_pre_ping=True
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def check_db():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print("DB FAILED:", e)
        return False


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_session():
    return Session(engine)
