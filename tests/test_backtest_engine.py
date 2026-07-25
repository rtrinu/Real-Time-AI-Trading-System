import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
from backtesting.engine import VectorisedBacktest


def make_mock_df(n=50):
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    close = 150 + np.cumsum(np.random.randn(n) * 2)
    feature_cols = [
        "log_ret_1", "log_ret_5", "log_ret_10", "log_ret_20",
        "pct_ret_1", "pct_ret_5", "pct_ret_10", "pct_ret_20",
        "roll_cum_ret_20", "roll_mean_ret_20", "roll_ret_z_20",
        "sentiment_mean", "confidence_mean", "headline_count",
        "positive_count", "negative_count",
    ]
    data = {col: np.random.randn(n) * 0.01 for col in feature_cols}
    data.update({
        "symbol": ["AAPL"] * n,
        "date": dates,
        "close": close,
        "signal_5": np.random.choice([-1, 0, 1], size=n),
    })
    return pd.DataFrame(data)


class MockModel:
    def predict(self, X):
        return np.random.choice([0, 1, 2], size=len(X))

    def predict_proba(self, X):
        probs = np.random.dirichlet([1, 1, 1], size=len(X))
        return probs


class TestVectorisedBacktestInit:
    def test_default_params(self):
        bt = VectorisedBacktest(
            model=MockModel(),
            symbol="AAPL",
            features=["ReturnsFeatures", "Sentiment"],
            signal="signal_5",
        )
        assert bt.symbol == "AAPL"
        assert bt.initial_capital == 10_000
        assert bt.transaction_cost == 0.001
        assert bt.min_confidence == 0.6

    def test_custom_params(self):
        bt = VectorisedBacktest(
            model=MockModel(),
            symbol="AAPL",
            features=["ReturnsFeatures"],
            signal="signal_5",
            initial_capital=20_000,
            transaction_cost=0.002,
            min_confidence=0.7,
        )
        assert bt.initial_capital == 20_000
        assert bt.transaction_cost == 0.002
        assert bt.min_confidence == 0.7


class TestVectorisedBacktestRun:
    @patch.object(VectorisedBacktest, "load_data")
    def test_returns_dict_keys(self, mock_load):
        mock_load.return_value = make_mock_df()
        bt = VectorisedBacktest(
            model=MockModel(),
            symbol="AAPL",
            features=["ReturnsFeatures", "Sentiment"],
            signal="signal_5",
            save_charts=False,
        )
        results = bt.run()
        assert "daily" in results
        assert "metrics" in results

    @patch.object(VectorisedBacktest, "load_data")
    def test_metrics_has_expected_keys(self, mock_load):
        mock_load.return_value = make_mock_df()
        bt = VectorisedBacktest(
            model=MockModel(),
            symbol="AAPL",
            features=["ReturnsFeatures", "Sentiment"],
            signal="signal_5",
            save_charts=False,
        )
        results = bt.run()
        assert "total_return" in results["metrics"]
        assert "sharpe_ratio" in results["metrics"]
        assert "max_drawdown" in results["metrics"]

    @patch.object(VectorisedBacktest, "load_data")
    def test_daily_has_prediction_columns(self, mock_load):
        mock_load.return_value = make_mock_df()
        bt = VectorisedBacktest(
            model=MockModel(),
            symbol="AAPL",
            features=["ReturnsFeatures", "Sentiment"],
            signal="signal_5",
            save_charts=False,
        )
        results = bt.run()
        df = results["daily"]
        assert "predicted" in df.columns
        assert "confidence" in df.columns
        assert "position" in df.columns
        assert "daily_return" in df.columns
        assert "strategy_return" in df.columns
        assert "equity" in df.columns

    @patch.object(VectorisedBacktest, "load_data")
    def test_equity_starts_at_initial_capital(self, mock_load):
        mock_load.return_value = make_mock_df()
        bt = VectorisedBacktest(
            model=MockModel(),
            symbol="AAPL",
            features=["ReturnsFeatures", "Sentiment"],
            signal="signal_5",
            save_charts=False,
            initial_capital=10_000,
        )
        results = bt.run()
        df = results["daily"]
        first_valid = df["equity"].dropna().iloc[0]
        assert first_valid >= 10_000 * 0.9


class TestConfidenceFiltering:
    @patch.object(VectorisedBacktest, "load_data")
    def test_low_confidence_defaults_to_hold(self, mock_load):
        df = make_mock_df()

        class AlwaysLowConfModel:
            def predict(self, X):
                return np.array([2] * len(X))

            def predict_proba(self, X):
                return np.array([[0.1, 0.1, 0.8]] * len(X))

        bt = VectorisedBacktest(
            model=AlwaysLowConfModel(),
            symbol="AAPL",
            features=["ReturnsFeatures", "Sentiment"],
            signal="signal_5",
            save_charts=False,
            min_confidence=0.9,
        )
        mock_load.return_value = df
        results = bt.run()
        assert (results["daily"]["position"] == 0).all()

    @patch.object(VectorisedBacktest, "load_data")
    def test_high_confidence_takes_position(self, mock_load):
        df = make_mock_df()

        class AlwaysHighConfModel:
            def predict(self, X):
                return np.array([2] * len(X))

            def predict_proba(self, X):
                return np.array([[0.05, 0.05, 0.9]] * len(X))

        bt = VectorisedBacktest(
            model=AlwaysHighConfModel(),
            symbol="AAPL",
            features=["ReturnsFeatures", "Sentiment"],
            signal="signal_5",
            save_charts=False,
            min_confidence=0.6,
        )
        mock_load.return_value = df
        results = bt.run()
        assert (results["daily"]["position"] == 1).any()


class TestTransactionCosts:
    @patch.object(VectorisedBacktest, "load_data")
    def test_costs_applied_on_position_change(self, mock_load):
        mock_load.return_value = make_mock_df()
        bt = VectorisedBacktest(
            model=MockModel(),
            symbol="AAPL",
            features=["ReturnsFeatures", "Sentiment"],
            signal="signal_5",
            save_charts=False,
            transaction_cost=0.01,
        )
        results = bt.run()
        df = results["daily"]
        assert "cost" in df.columns
        assert df["cost"].sum() >= 0
