from sqlmodel import Session
from sqlalchemy import insert
from db.market_models import OHLCV
from ingestion.yfinance_download import download_market_data
from db.create_engine import get_session
from core.logger_config import logger


def bulk_insert_ohlcv(symbol: str = "AAPL") -> None:

    records = download_market_data(symbol)

    if not records:
        raise ValueError("No records to insert")

    session: Session = get_session()

    logger.info("Attempting to insert to database")
    try:
        session.execute(insert(OHLCV), records)
        session.commit()

    except Exception as e:
        session.rollback()
        raise RuntimeError(f"Bulk insert failed: {e}")

    finally:
        session.close()
