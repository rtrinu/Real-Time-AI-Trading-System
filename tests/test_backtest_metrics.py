import pytest
import pandas as pd
import numpy as np
from backtesting.metrics import calc_metrics


def make_df(strategy_returns, initial_capital=10_000):
    df = pd.DataFrame({"strategy_return": strategy_returns})
    df["equity"] = initial_capital * (1 + df["strategy_return"]).cumprod()
    df["position_change"] = [False] + [True] * (len(df) - 1)
    return df


class TestCalcMetrics:
    def test_returns_all_keys(self):
        df = make_df([0.01, -0.005, 0.02, -0.01, 0.015])
        result = calc_metrics(df)
        assert set(result.keys()) == {
            "total_return",
            "annualized_return",
            "sharpe_ratio",
            "max_drawdown",
            "win_rate",
            "profit_factor",
            "total_trades",
            "final_equity",
        }

    def test_positive_returns(self):
        df = make_df([0.01, 0.02, 0.01, 0.01, 0.01])
        result = calc_metrics(df)
        assert result["total_return"] > 0
        assert result["final_equity"] > 10_000
        assert result["win_rate"] == 100.0

    def test_negative_returns(self):
        df = make_df([-0.01, -0.02, -0.01, -0.01, -0.01])
        result = calc_metrics(df)
        assert result["total_return"] < 0
        assert result["final_equity"] < 10_000
        assert result["win_rate"] == 0.0

    def test_zero_returns(self):
        df = make_df([0.0, 0.0, 0.0, 0.0])
        result = calc_metrics(df)
        assert result["total_return"] == 0.0
        assert result["sharpe_ratio"] == 0

    def test_profit_factor_all_wins(self):
        df = make_df([0.01, 0.02, 0.03])
        result = calc_metrics(df)
        assert result["profit_factor"] == float("inf")

    def test_profit_factor_mixed(self):
        df = make_df([0.02, 0.04, -0.01, -0.01])
        result = calc_metrics(df)
        assert result["profit_factor"] > 1

    def test_custom_initial_capital(self):
        df = make_df([0.1], initial_capital=20_000)
        result = calc_metrics(df, initial_capital=20_000)
        assert result["final_equity"] == round(20_000 * 1.1, 2)

    def test_total_trades(self):
        df = make_df([0.01] * 5)
        df["position_change"] = [True, False, True, False, True]
        result = calc_metrics(df)
        assert result["total_trades"] == 3

    def test_max_drawdown_always_negative(self):
        df = make_df([0.01, -0.05, 0.03, -0.02, 0.01])
        result = calc_metrics(df)
        assert result["max_drawdown"] <= 0

    def test_single_row(self):
        df = make_df([0.01])
        result = calc_metrics(df)
        assert result["total_return"] > 0
        assert result["final_equity"] > 10_000
