from db.create_engine import get_session
from training.configs import TABLE_MAP, FEATURE_GROUPS, CALENDAR_FEATURES
from training.data_loader import add_calendar_features
from ml.xgboost import XGBoostModel
from core.logger_config import logger
import pandas as pd
import numpy as np
from db.market_models import OHLCV, ReturnsFeatures
from sqlmodel import select
from backtesting.metrics import calc_metrics
from backtesting.visualisation import save_all_charts


class VectorisedBacktest:
    def __init__(
        self,
        model,
        symbol: str,
        features: list[str],
        signal: str,
        initial_capital: int = 10_000,
        transaction_cost: int = 0.001,
        save_charts: bool = True,
        min_confidence: float = 0.6,
    ):
        self.model = model
        self.symbol = symbol
        self.features = features
        self.signal = signal
        self.initial_capital = initial_capital
        self.transaction_cost = transaction_cost
        self.save_charts = save_charts
        self.min_confidence = min_confidence

    def load_data(self):
        session = get_session()
        dfs = {}
        features = self.features
        symbol = self.symbol
        signal = self.signal

        for table_name in features:
            model = TABLE_MAP[table_name]
            rows = session.exec(select(model).where(model.symbol == symbol)).all()
            df = pd.DataFrame([r.model_dump() for r in rows])
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df["date"] = df["timestamp"].dt.date
            df = df.drop(columns=["id", "timestamp"], errors="ignore")
            dfs[table_name] = df

        merged = dfs[features[0]]
        for table_name in features[1:]:
            merged = pd.merge(
                merged, dfs[table_name], on=["symbol", "date"], how="left"
            )

        all_cols = []
        for table_name in features:
            all_cols.extend(FEATURE_GROUPS[table_name])

        feature_cols = [c for c in all_cols if c != signal]

        keep = ["symbol", "date"] + feature_cols + [signal]
        merged = merged[[c for c in keep if c in merged.columns]]

        if signal not in merged.columns:
            signal_rows = session.exec(
                select(ReturnsFeatures).where(ReturnsFeatures.symbol == symbol)
            ).all()
            signal_df = pd.DataFrame([r.model_dump() for r in signal_rows])
            signal_df["timestamp"] = pd.to_datetime(signal_df["timestamp"])
            signal_df["date"] = signal_df["timestamp"].dt.date
            merged = pd.merge(
                merged, signal_df[["date", signal]], on="date", how="left"
            )

        merged = add_calendar_features(merged)
        merged[feature_cols] = merged[feature_cols].fillna(0)

        ohlcv = session.exec(select(OHLCV).where(OHLCV.symbol == symbol)).all()
        ohlcv_df = pd.DataFrame([r.model_dump() for r in ohlcv])
        ohlcv_df["date"] = ohlcv_df["timestamp"].dt.date
        merged = pd.merge(merged, ohlcv_df[["date", "close"]], on="date", how="left")

        return merged

    def run(self):
        df = self.load_data()

        all_cols = []
        for table_name in self.features:
            all_cols.extend(FEATURE_GROUPS[table_name])
        feature_cols = [c for c in all_cols if c != self.signal]
        X = df[feature_cols]
        predictions = self.model.predict(X)
        probabilities = self.model.predict_proba(X)

        df["predicted"] = predictions
        df["confidence"] = probabilities.max(axis=1)
        df["position"] = df.apply(
            lambda row: (
                {0: -1, 1: 0, 2: 1}[row["predicted"]]
                if row["confidence"] >= self.min_confidence
                else 0
            ),
            axis=1,
        )

        # Daily returns
        df["daily_return"] = df["close"].pct_change()

        # Transaction costs
        df["position_change"] = df["position"].diff().fillna(0).abs() > 0
        df["cost"] = df["position_change"] * self.transaction_cost

        # Strategy return (net of costs)
        df["strategy_return"] = df["daily_return"] * df["position"] - df["cost"]

        # Equity curve
        df["equity"] = self.initial_capital * (1 + df["strategy_return"]).cumprod()

        # Metrics
        metrics = calc_metrics(df, self.initial_capital)

        results = {"daily": df, "metrics": metrics}

        if self.save_charts:
            paths = save_all_charts({"daily": df, "metrics": metrics})
            results["chart_paths"] = paths

        return results


def walk_forward(
    features: list[str],
    signal: str,
    symbol: str,
    train_pct: float = 0.8,
    retrain_every: int = 60,
    min_confidence: float = 0.6,
    initial_capital: int = 10_000,
    transaction_cost: float = 0.001,
    _model_params: dict = None,
):
    session = get_session()
    dfs = {}

    for table_name in features:
        model_cls = TABLE_MAP[table_name]
        rows = session.exec(select(model_cls).where(model_cls.symbol == symbol)).all()
        df = pd.DataFrame([r.model_dump() for r in rows])
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df["date"] = df["timestamp"].dt.date
        df = df.drop(columns=["id", "timestamp"], errors="ignore")
        dfs[table_name] = df

    merged = dfs[features[0]]
    for table_name in features[1:]:
        merged = pd.merge(merged, dfs[table_name], on=["symbol", "date"], how="left")

    all_cols = []
    for table_name in features:
        all_cols.extend(FEATURE_GROUPS[table_name])

    feature_cols = [c for c in all_cols if c != signal]

    keep = ["symbol", "date"] + feature_cols + [signal]
    merged = merged[[c for c in keep if c in merged.columns]]

    if signal not in merged.columns:
        signal_rows = session.exec(
            select(ReturnsFeatures).where(ReturnsFeatures.symbol == symbol)
        ).all()
        signal_df = pd.DataFrame([r.model_dump() for r in signal_rows])
        signal_df["timestamp"] = pd.to_datetime(signal_df["timestamp"])
        signal_df["date"] = signal_df["timestamp"].dt.date
        merged = pd.merge(merged, signal_df[["date", signal]], on="date", how="left")

    merged = add_calendar_features(merged)
    merged = merged.dropna(subset=[signal])
    merged[feature_cols] = merged[feature_cols].fillna(0)
    merged = merged.sort_values("date").reset_index(drop=True)

    ohlcv = session.exec(select(OHLCV).where(OHLCV.symbol == symbol)).all()
    ohlcv_df = pd.DataFrame([r.model_dump() for r in ohlcv])
    ohlcv_df["date"] = ohlcv_df["timestamp"].dt.date
    merged = pd.merge(merged, ohlcv_df[["date", "close"]], on="date", how="left")
    merged = merged.dropna(subset=["close"])

    signal_map = {0: "sell", 1: "hold", 2: "buy"}
    y_mapped = merged[signal].map({-1: 0, 0: 1, 1: 2})

    n = len(merged)
    train_size = int(n * train_pct)
    window_size = retrain_every

    logger.info(
        f"Walk-forward: {n} rows, train={train_size}, window={window_size}, retrain_every={retrain_every}"
    )

    all_predictions = []
    start = 0
    fold = 0

    while start + train_size + window_size <= n:
        fold += 1
        train_end = start + train_size
        test_end = train_end + window_size

        X_train = merged.iloc[start:train_end][feature_cols]
        y_train = y_mapped.iloc[start:train_end]
        X_test = merged.iloc[train_end:test_end][feature_cols]
        test_dates = merged.iloc[train_end:test_end]["date"]
        test_close = merged.iloc[train_end:test_end]["close"]

        if len(X_test) == 0:
            break

        if _model_params:
            model = XGBoostModel(**_model_params)
        else:
            model = XGBoostModel()
        model.train(X_train, y_train)

        preds = model.predict(X_test)
        probas = model.predict_proba(X_test)
        confidences = probas.max(axis=1)

        for i in range(len(preds)):
            row_idx = train_end + i
            all_predictions.append(
                {
                    "date": test_dates.iloc[i],
                    "actual": signal_map.get(y_mapped.iloc[row_idx], "hold"),
                    "predicted": signal_map.get(preds[i], "hold"),
                    "confidence": confidences[i],
                    "close": test_close.iloc[i],
                }
            )

        logger.info(
            f"Fold {fold}: train={start}-{train_end}, test={train_end}-{test_end}"
        )
        start += retrain_every

    if not all_predictions:
        logger.warning("No walk-forward predictions generated")
        return None

    preds_df = pd.DataFrame(all_predictions)
    preds_df["position"] = preds_df.apply(
        lambda r: (
            {"sell": -1, "hold": 0, "buy": 1}[r["predicted"]]
            if r["confidence"] >= min_confidence
            else 0
        ),
        axis=1,
    )
    preds_df["daily_return"] = preds_df["close"].pct_change()
    preds_df["position_change"] = preds_df["position"].diff().fillna(0).abs() > 0
    preds_df["cost"] = preds_df["position_change"] * transaction_cost
    preds_df["strategy_return"] = (
        preds_df["daily_return"] * preds_df["position"] - preds_df["cost"]
    )
    preds_df["equity"] = initial_capital * (1 + preds_df["strategy_return"]).cumprod()

    metrics = calc_metrics(preds_df, initial_capital)
    logger.info(f"Walk-forward metrics: {metrics}")

    return {"daily": preds_df, "metrics": metrics}
