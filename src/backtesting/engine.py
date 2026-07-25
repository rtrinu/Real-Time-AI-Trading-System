from db.create_engine import get_session
from training.configs import TABLE_MAP, FEATURE_GROUPS, CALENDAR_FEATURES
from training.data_loader import add_calendar_features
import pandas as pd
from db.market_models import OHLCV
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
            cols = FEATURE_GROUPS[table_name] + CALENDAR_FEATURES
            rows = session.exec(select(model).where(model.symbol == symbol)).all()
            df = pd.DataFrame([r.model_dump() for r in rows])
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df["date"] = df["timestamp"].dt.date
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
        merged = add_calendar_features(merged)
        merged[feature_cols] = merged[feature_cols].fillna(0)

        ohlcv = session.exec(select(OHLCV).where(OHLCV.symbol == self.symbol)).all()
        ohlcv_df = pd.DataFrame([r.model_dump() for r in ohlcv])
        ohlcv_df["date"] = ohlcv_df["timestamp"].dt.date
        merged = pd.merge(merged, ohlcv_df[["date", "close"]], on="date", how="left")

        return merged

    def run(self):
        df = self.load_data()

        # Predictions
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
