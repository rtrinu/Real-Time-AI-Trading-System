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


def load_ohlcv(symbols: list[str], start=None, end=None):
    session = get_session()
    stmt = select(OHLCV).where(OHLCV.symbol.in_(symbols))
    if start:
        stmt = stmt.where(OHLCV.timestamp >= start)
    if end:
        stmt = stmt.where(OHLCV.timestamp >= end)
    results = session.exec(stmt).all()
    df = pd.DataFrame([r.model_dump() for r in results])

    return df


def load_returns(symbols: list[str], start=None, end=None):
    session = get_session()
    stmt = select(ReturnsFeatures).where(ReturnsFeatures.symbol.in_(symbols))
    if start:
        stmt = stmt.where(ReturnsFeatures.timestamp >= start)
    if end:
        stmt = stmt.where(ReturnsFeatures.timestamp >= end)
    results = session.exec(stmt).all()
    df = pd.DataFrame([r.model_dump() for r in results])

    return df


def load_momentum(symbols: list[str], start=None, end=None):
    session = get_session()
    stmt = select(MomentumFeatures).where(MomentumFeatures.symbol.in_(symbols))
    if start:
        stmt = stmt.where(MomentumFeatures.timestamp >= start)
    if end:
        stmt = stmt.where(MomentumFeatures.timestamp >= end)
    results = session.exec(stmt).all()
    df = pd.DataFrame([r.model_dump() for r in results])

    return df


def load_volatility(symbols: list[str], start=None, end=None):
    session = get_session()
    stmt = select(VolatilityFeatures).where(VolatilityFeatures.symbol.in_(symbols))
    if start:
        stmt = stmt.where(VolatilityFeatures.timestamp >= start)
    if end:
        stmt = stmt.where(VolatilityFeatures.timestamp >= end)
    results = session.exec(stmt).all()
    df = pd.DataFrame([r.model_dump() for r in results])

    return df


def load_mean_reversion(symbols: list[str], start=None, end=None):
    session = get_session()
    stmt = select(MeanReversionFeatures).where(
        MeanReversionFeatures.symbol.in_(symbols)
    )
    if start:
        stmt = stmt.where(MeanReversionFeatures.timestamp >= start)
    if end:
        stmt = stmt.where(MeanReversionFeatures.timestamp >= end)
    results = session.exec(stmt).all()
    df = pd.DataFrame([r.model_dump() for r in results])

    return df


def load_volume(symbols: list[str], start=None, end=None):
    session = get_session()
    stmt = select(VolumeFeatures).where(VolumeFeatures.symbol.in_(symbols))
    if start:
        stmt = stmt.where(VolumeFeatures.timestamp >= start)
    if end:
        stmt = stmt.where(VolumeFeatures.timestamp >= end)
    results = session.exec(stmt).all()
    df = pd.DataFrame([r.model_dump() for r in results])

    return df
