from sqlmodel import Session, SQLModel, select
import pandas as pd
from sqlalchemy import insert
from db.market_models import (
    OHLCV,
    ReturnsFeatures,
    MomentumFeatures,
    VolatilityFeatures,
    MeanReversionFeatures,
    VolumeFeatures,
)
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


def load_ohlcv(symbols: list[str], start=None, end=None):
    session = get_session()
    stmt = select(OHLCV).where(OHLCV.symbol.in_(symbols))
    if start:
        stmt = stmt.where(OHLCV.timestamp >= start)
    if end:
        stmt = stmt.where(OHLCV.timestamp >= end)
    reults = session.exec(stmt).all()
    df = pd.DataFrame([r.model_dump() for r in results])

    return df


def load_returns(symbols: list[str], start=None, end=None):
    session = get_session()
    stmt = select(ReturnsFeatures).where(ReturnsFeatures.symbol.in_(symbols))
    if start:
        stmt = stmt.where(ReturnsFeatures.timestamp >= start)
    if end:
        stmt = stmt.where(ReturnsFeatures.timestamp >= end)
    reults = session.exec(stmt).all()
    df = pd.DataFrame([r.model_dump() for r in results])

    return df


def load_momentum(symbols: list[str], start=None, end=None):
    session = get_session()
    stmt = select(MomentumFeatures).where(MomentumFeatures.symbol.in_(symbols))
    if start:
        stmt = stmt.where(MomentumFeatures.timestamp >= start)
    if end:
        stmt = stmt.where(MomentumFeatures.timestamp >= end)
    reults = session.exec(stmt).all()
    df = pd.DataFrame([r.model_dump() for r in results])

    return df


def load_volatility(symbols: list[str], start=None, end=None):
    session = get_session()
    stmt = select(VolatilityFeatures).where(VolatilityFeatures.symbol.in_(symbols))
    if start:
        stmt = stmt.where(VolatilityFeatures.timestamp >= start)
    if end:
        stmt = stmt.where(VolatilityFeatures.timestamp >= end)
    reults = session.exec(stmt).all()
    df = pd.DataFrame([r.model_dump() for r in results])

    return df


def load_mean_revision(symbols: list[str], start=None, end=None):
    session = get_session()
    stmt = select(MeanReversionFeatures).where(
        MeanReversionFeatures.symbol.in_(symbols)
    )
    if start:
        stmt = stmt.where(MeanReversionFeatures.timestamp >= start)
    if end:
        stmt = stmt.where(MeanReversionFeatures.timestamp >= end)
    reults = session.exec(stmt).all()
    df = pd.DataFrame([r.model_dump() for r in results])

    return df


def load_volume(symbols: list[str], start=None, end=None):
    session = get_session()
    stmt = select(VolumeFeatures).where(VolumeFeatures.symbol.in_(symbols))
    if start:
        stmt = stmt.where(VolumeFeatures.timestamp >= start)
    if end:
        stmt = stmt.where(VolumeFeatures.timestamp >= end)
    reults = session.exec(stmt).all()
    df = pd.DataFrame([r.model_dump() for r in results])

    return df
