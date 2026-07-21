import pytest
import pandas as pd
import numpy as np
from features.market.feature_engineering import (
    log_returns,
    pct_returns,
    rolling_cumulative_return,
    forward_returns,
    create_signal,
    rolling_return_stats,
    rsi,
    classify_volatility_regime,
    classify_trend_regime,
    classify_regime,
    build_all_features,
    split_features,
)


@pytest.fixture
def ohlcv_df():
    np.random.seed(42)
    n = 100
    dates = pd.date_range("2026-01-01", periods=n, freq="B")
    close = 150 + np.cumsum(np.random.randn(n) * 2)
    return pd.DataFrame(
        {
            "symbol": "AAPL",
            "timestamp": dates,
            "open": close + np.random.randn(n) * 0.5,
            "high": close + abs(np.random.randn(n)),
            "low": close - abs(np.random.randn(n)),
            "close": close,
            "volume": np.random.randint(1_000_000, 10_000_000, size=n),
        }
    )


class TestLogReturns:
    def test_adds_log_ret_columns(self, ohlcv_df):
        result = log_returns(ohlcv_df.copy())
        for p in [1, 5, 10, 20]:
            assert f"log_ret_{p}" in result.columns

    def test_log_ret_values(self, ohlcv_df):
        result = log_returns(ohlcv_df.copy())
        assert result["log_ret_1"].iloc[25] == pytest.approx(
            np.log(ohlcv_df["close"].iloc[25] / ohlcv_df["close"].iloc[24]), abs=1e-10
        )

    def test_first_rows_are_nan(self, ohlcv_df):
        result = log_returns(ohlcv_df.copy())
        assert pd.isna(result["log_ret_5"].iloc[0])


class TestPctReturns:
    def test_adds_pct_ret_columns(self, ohlcv_df):
        result = pct_returns(ohlcv_df.copy())
        for p in [1, 5, 10, 20]:
            assert f"pct_ret_{p}" in result.columns


class TestRollingCumulativeReturn:
    def test_adds_column(self, ohlcv_df):
        result = rolling_cumulative_return(ohlcv_df.copy())
        assert "roll_cum_ret_20" in result.columns

    def test_first_rows_nan(self, ohlcv_df):
        result = rolling_cumulative_return(ohlcv_df.copy())
        assert pd.isna(result["roll_cum_ret_20"].iloc[0])


class TestForwardReturns:
    def test_adds_columns(self, ohlcv_df):
        result = forward_returns(ohlcv_df.copy())
        for h in [1, 5, 10, 20]:
            assert f"fwd_ret_{h}" in result.columns

    def test_last_rows_nan(self, ohlcv_df):
        result = forward_returns(ohlcv_df.copy())
        assert pd.isna(result["fwd_ret_5"].iloc[-1])


class TestCreateSignal:
    def test_signal_values(self, ohlcv_df):
        df = forward_returns(ohlcv_df.copy())
        result = create_signal(df)
        for h in [1, 5, 10, 20]:
            assert f"signal_{h}" in result.columns
            assert set(result[f"signal_{h}"].unique()).issubset({-1, 0, 1})

    def test_signal_distribution(self, ohlcv_df):
        df = forward_returns(ohlcv_df.copy())
        result = create_signal(df)
        for h in [1, 5, 10, 20]:
            counts = result[f"signal_{h}"].value_counts()
            assert counts.get(0, 0) > 0  # at least some neutral signals


class TestRollingReturnStats:
    def test_adds_columns(self, ohlcv_df):
        result = rolling_return_stats(ohlcv_df.copy())
        assert "roll_mean_ret_20" in result.columns
        assert "roll_ret_z_20" in result.columns

    def test_z_score_centered(self, ohlcv_df):
        result = rolling_return_stats(ohlcv_df.copy())
        valid = result["roll_ret_z_20"].dropna()
        assert abs(valid.mean()) < 1.0


class TestRSI:
    def test_rsi_range(self, ohlcv_df):
        rsi_vals = rsi(ohlcv_df["close"], 14)
        valid = rsi_vals.dropna()
        assert valid.min() >= 0
        assert valid.max() <= 100

    def test_rsi_different_periods(self, ohlcv_df):
        rsi7 = rsi(ohlcv_df["close"], 7).dropna()
        rsi14 = rsi(ohlcv_df["close"], 14).dropna()
        assert len(rsi7) > len(rsi14)


class TestClassifyVolatilityRegime:
    def test_high_vol(self):
        assert classify_volatility_regime(2.0) == "high_vol"

    def test_low_vol(self):
        assert classify_volatility_regime(0.5) == "low_vol"

    def test_normal(self):
        assert classify_volatility_regime(1.0) == "normal"

    def test_boundary_high(self):
        assert classify_volatility_regime(1.5) == "normal"

    def test_boundary_low(self):
        assert classify_volatility_regime(0.7) == "normal"


class TestClassifyTrendRegime:
    def test_bull(self):
        assert classify_trend_regime(0.05, 0.1) == "bull"

    def test_bear(self):
        assert classify_trend_regime(-0.05, -0.1) == "bear"

    def test_neutral_mixed(self):
        assert classify_trend_regime(0.05, -0.1) == "neutral"

    def test_neutral_zero(self):
        assert classify_trend_regime(0, 0) == "neutral"


class TestClassifyRegime:
    def test_high_vol_overrides_to_neutral(self):
        result = classify_regime(2.0, "bull", "high_vol")
        assert result == "neutral"

    def test_bull_high_vol_z(self):
        result = classify_regime(1.5, "bull", "normal")
        assert result == "bull"

    def test_bear_high_vol_z(self):
        result = classify_regime(1.5, "bear", "normal")
        assert result == "bear"

    def test_neutral_low_vol_z(self):
        result = classify_regime(0.5, "bull", "normal")
        assert result == "neutral"

    def test_neutral_default(self):
        result = classify_regime(0.0, "neutral", "normal")
        assert result == "neutral"


class TestBuildAllFeatures:
    def test_returns_dataframe(self, ohlcv_df):
        result = build_all_features(ohlcv_df.copy())
        assert isinstance(result, pd.DataFrame)

    def test_no_nans(self, ohlcv_df):
        result = build_all_features(ohlcv_df.copy())
        assert not result.isna().any().any()

    def test_has_key_features(self, ohlcv_df):
        result = build_all_features(ohlcv_df.copy())
        expected = [
            "log_ret_1",
            "pct_ret_1",
            "signal_5",
            "rsi_14",
            "vol_20",
            "zscore_20",
            "regime",
        ]
        for col in expected:
            assert col in result.columns

    def test_fewer_rows_than_input(self, ohlcv_df):
        result = build_all_features(ohlcv_df.copy())
        assert len(result) < len(ohlcv_df)


class TestSplitFeatures:
    def test_returns_dict(self, ohlcv_df):
        df = build_all_features(ohlcv_df.copy())
        result = split_features(df)
        assert isinstance(result, dict)

    def test_expected_keys(self, ohlcv_df):
        df = build_all_features(ohlcv_df.copy())
        result = split_features(df)
        expected_keys = {"returns", "momentum", "volatility", "mean_reversion", "volume", "regime"}
        assert set(result.keys()) == expected_keys

    def test_returns_has_signal(self, ohlcv_df):
        df = build_all_features(ohlcv_df.copy())
        result = split_features(df)
        assert "signal_5" in result["returns"].columns

    def test_regime_has_regime(self, ohlcv_df):
        df = build_all_features(ohlcv_df.copy())
        result = split_features(df)
        assert "regime" in result["regime"].columns
