from sqlmodel import Session
from sqlalchemy import insert
from db.news_models import NewsAPI
from ingestion.news.newsapi import NewsAPISource
from db.create_engine import get_session
from core.logger_config import logger
from core.config import settings


def bulk_insert_newsapi(symbol: str = "AAPL") -> None:

    source = NewsAPISource(settings.newsapi_key)
    records = source.fetch_raw_data(symbol)

    if not records:
        raise ValueError("No records to insert")

    session: Session = get_session()

    try:
        logger.info("Attempting to insert to database")
        cleaned = [source.normalise(r, symbol) for r in records]
        stmt = insert(NewsAPI).values(cleaned)
        session.exec(stmt)
        session.commit()

    except Exception as e:
        session.rollback()
        raise RuntimeError(f"Bulk insert failed: {e}")

    finally:
        session.close()
