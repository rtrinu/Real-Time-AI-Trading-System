from sqlmodel import Session, SQLModel
from sqlalchemy import insert
from db.market_models import OHLCV
from ingestion.yfinance_download import download_market_data
from db.create_engine import get_session
from core.logger_config import logger
from typing import Type


def bulk_insert(df, model, session):
    if df is None or df.empty:
        raise ValueError("Empty DataFrame")

    table_cols = {c.name for c in model.__table__.columns}

    # ONLY columns that exist in BOTH
    cols = [c for c in df.columns if c in table_cols and c != "id"]

    if not cols:
        raise ValueError(
            f"No overlapping columns between DF and {model.__name__}. "
            f"DF cols={df.columns.tolist()}, model cols={list(table_cols)}"
        )

    df = df[cols]

    records = df.to_dict("records")

    if len(records) == 0:
        raise ValueError("No records after column alignment")

    session.execute(insert(model), records)
    session.commit()
    return df
