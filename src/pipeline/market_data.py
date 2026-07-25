from ingestion.yfinance_download import download_market_data
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
from datetime import datetime, timedelta
import pandas as pd


def run_yfinance_pipeline():
    session = get_session()
    data = download_market_data()
    raw = bulk_insert(data, OHLCV, session)

    logger.info("Creating market data features")
    features = build_all_features(raw)
    split = split_features(features)

    logger.info("Bulk inserting into features' tables")
    bulk_insert(split["returns"], ReturnsFeatures, session)
    bulk_insert(split["momentum"], MomentumFeatures, session)
    bulk_insert(split["volatility"], VolatilityFeatures, session)
    bulk_insert(split["mean_reversion"], MeanReversionFeatures, session)
    bulk_insert(split["volume"], VolumeFeatures, session)
    bulk_insert(split["regime"], RegimeFeatures, session)


def update_market_data():
    if datetime.today().weekday() >= 5:
        logger.info("Weekend — skipping market data update")
        return

    session = get_session()
    data = download_market_data(period="1d")

    symbol = data["symbol"].iloc[0]
    data_ts = data["timestamp"].iloc[0]
    data_date = pd.Timestamp(data_ts).date()
    start = datetime(data_date.year, data_date.month, data_date.day)
    end = datetime(data_date.year, data_date.month, data_date.day, 23, 59, 59)

    existing = session.exec(
        select(OHLCV).where(
            OHLCV.symbol == symbol,
            OHLCV.timestamp >= start,
            OHLCV.timestamp <= end,
        )
    ).first()
    if existing:
        logger.info(f"Data for {data_date} already exists, skipping")
        return

    lookback = datetime.today() - timedelta(days=60)
    history = session.exec(
        select(OHLCV)
        .where(
            OHLCV.symbol == symbol,
            OHLCV.timestamp >= lookback,
        )
        .order_by(OHLCV.timestamp)
    ).all()

    history_df = pd.DataFrame([r.model_dump() for r in history])
    combined = pd.concat([history_df, data], ignore_index=True)

    features = build_all_features(combined)

    if features.empty:
        logger.warning("No features generated — DB may lack history. Falling back to full download.")
        run_yfinance_pipeline()
        return

    latest = features.iloc[[-1]]
    split = split_features(latest)

    bulk_insert(data, OHLCV, session)
    bulk_insert(split["returns"], ReturnsFeatures, session)
    bulk_insert(split["momentum"], MomentumFeatures, session)
    bulk_insert(split["volatility"], VolatilityFeatures, session)
    bulk_insert(split["mean_reversion"], MeanReversionFeatures, session)
    bulk_insert(split["volume"], VolumeFeatures, session)
    bulk_insert(split["regime"], RegimeFeatures, session)
