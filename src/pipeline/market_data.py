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
