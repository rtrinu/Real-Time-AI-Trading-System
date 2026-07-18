from training.configs import FEATURE_GROUPS, TABLE_MAP
from db.create_engine import get_session
from sqlmodel import select
from db.market_models import ReturnsFeatures
from db.news_models import Sentiment
from core.logger_config import logger
import pandas as pd


def load_training_data(symbol: str, features: list[str], signal: str):
    session = get_session()
    dfs = {}

    for table_name in features:
        model = TABLE_MAP[table_name]
        cols = FEATURE_GROUPS[table_name]
        rows = session.exec(select(model).where(model.symbol == symbol)).all()
        df = pd.DataFrame([r.model_dump() for r in rows])
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df["date"] = df["timestamp"].dt.date
        dfs[table_name] = df

    # Merge all tables
    merged = dfs[features[0]]
    for table_name in features[1:]:
        merged = pd.merge(merged, dfs[table_name], on=["symbol", "date"], how="left")

    # All columns from config
    all_cols = []
    for table_name in features:
        all_cols.extend(FEATURE_GROUPS[table_name])

    # Remove signal from features — it's the target
    feature_cols = [c for c in all_cols if c != signal]

    keep = ["symbol", "date"] + feature_cols + [signal]
    merged = merged[[c for c in keep if c in merged.columns]]
    merged[feature_cols] = merged[feature_cols].fillna(0)

    X = merged[feature_cols]
    y = merged[signal].map({-1: 0, 0: 1, 1: 2})

    return X, y
