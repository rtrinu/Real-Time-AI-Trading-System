from ingestion.yfinance_download import (
    download_market_data,
    download_todays_market_data,
)
from db.crud.general import bulk_insert
from db.create_engine import get_session
from db.market_models import (
    OHLCV,
    ReturnsFeatures,
    MomentumFeatures,
    VolatilityFeatures,
    MeanReversionFeatures,
    VolumeFeatures,
    RegimeFeatures,
)
from features.market.feature_engineering import build_all_features, split_features
from core.logger_config import logger
from sqlmodel import select
from datetime import datetime, date, timedelta
import pandas as pd


def run_yfinance_pipeline():
    session = get_session()
    data = download_market_data()
    raw = bulk_insert(data, OHLCV, session)

    logger.info("Creating market data features")
    features = build_all_features(raw)
    split = split_features(features)
    logger.info(type(split))

    logger.info("Bulk inserting into features' tables")
    bulk_insert(split["returns"], ReturnsFeatures, session)
    bulk_insert(split["momentum"], MomentumFeatures, session)
    bulk_insert(split["volatility"], VolatilityFeatures, session)
    bulk_insert(split["mean_reversion"], MeanReversionFeatures, session)
    bulk_insert(split["volume"], VolumeFeatures, session)
    bulk_insert(split["regime"], RegimeFeatures, session)


def update_market_data():
    session = get_session()
    data = download_todays_market_data()

    today = date.today()
    start = datetime(today.year, today.month, today.day)
    end = datetime(today.year, today.month, today.day, 23, 59, 59)
    existing = session.exec(
        select(OHLCV).where(
            OHLCV.symbol == data["symbol"].iloc[0],
            OHLCV.timestamp >= start,
            OHLCV.timestamp <= end,
        )
    ).first()
    if existing:
        logger.info("Data for today already exists, skipping")
        return

    lookback = datetime.today() - timedelta(days=60)
    history = session.exec(
        select(OHLCV)
        .where(
            OHLCV.symbol == data["symbol"].iloc[0],
            OHLCV.timestamp >= lookback,
        )
        .order_by(OHLCV.timestamp)
    ).all()

    history_df = pd.DataFrame([r.model_dump() for r in history])
    combined = pd.concat([history_df, data], ignore_index=True)

    features = build_all_features(combined)
    latest = features.iloc[[-1]]
    split = split_features(latest)

    bulk_insert(data, OHLCV, session)
    bulk_insert(split["returns"], ReturnsFeatures, session)
    bulk_insert(split["momentum"], MomentumFeatures, session)
    bulk_insert(split["volatility"], VolatilityFeatures, session)
    bulk_insert(split["mean_reversion"], MeanReversionFeatures, session)
    bulk_insert(split["volume"], VolumeFeatures, session)
    bulk_insert(split["regime"], RegimeFeatures, session)
