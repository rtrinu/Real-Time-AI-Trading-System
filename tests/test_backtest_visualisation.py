import pytest
import pandas as pd
import numpy as np
import os
import tempfile
from backtesting.visualisation import (
    plot_equity_curve,
    plot_drawdown,
    plot_signal_overlay,
    save_all_charts,
)


@pytest.fixture
def sample_df():
    dates = pd.date_range("2024-01-01", periods=50, freq="D")
    close = 150 + np.cumsum(np.random.randn(50) * 2)
    equity = 10_000 * (1 + np.random.randn(50) * 0.02).cumprod()
    position = np.zeros(50)
    position[5] = 1
    position[15] = -1
    position[25] = 1
    position[35] = -1
    return pd.DataFrame({
        "date": dates,
        "close": close,
        "equity": equity,
        "position": position,
    })


@pytest.fixture
def sample_metrics():
    return {
        "total_return": 20.43,
        "annualized_return": 29.92,
        "sharpe_ratio": 2.1,
        "max_drawdown": -5.59,
        "win_rate": 13.41,
        "profit_factor": 2.22,
        "total_trades": 39,
        "final_equity": 12043.2,
    }


class TestPlotEquityCurve:
    def test_creates_file(self, sample_df, sample_metrics, tmp_path):
        path = str(tmp_path / "equity.png")
        result = plot_equity_curve(sample_df, sample_metrics, path)
        assert os.path.exists(result)

    def test_returns_path(self, sample_df, sample_metrics, tmp_path):
        path = str(tmp_path / "equity.png")
        result = plot_equity_curve(sample_df, sample_metrics, path)
        assert result == path


class TestPlotDrawdown:
    def test_creates_file(self, sample_df, tmp_path):
        path = str(tmp_path / "drawdown.png")
        result = plot_drawdown(sample_df, path)
        assert os.path.exists(result)

    def test_returns_path(self, sample_df, tmp_path):
        path = str(tmp_path / "drawdown.png")
        result = plot_drawdown(sample_df, path)
        assert result == path


class TestPlotSignalOverlay:
    def test_creates_file(self, sample_df, tmp_path):
        path = str(tmp_path / "signals.png")
        result = plot_signal_overlay(sample_df, path)
        assert os.path.exists(result)

    def test_returns_path(self, sample_df, tmp_path):
        path = str(tmp_path / "signals.png")
        result = plot_signal_overlay(sample_df, path)
        assert result == path

    def test_no_trades(self, sample_df, tmp_path):
        sample_df["position"] = 0
        path = str(tmp_path / "signals.png")
        result = plot_signal_overlay(sample_df, path)
        assert os.path.exists(result)


class TestSaveAllCharts:
    def test_creates_all_files(self, sample_df, sample_metrics, tmp_path):
        output_dir = str(tmp_path / "charts")
        results = {"daily": sample_df, "metrics": sample_metrics}
        paths = save_all_charts(results, output_dir)
        assert os.path.exists(paths["equity_curve"])
        assert os.path.exists(paths["drawdown"])
        assert os.path.exists(paths["signal_overlay"])

    def test_creates_directory(self, sample_df, sample_metrics, tmp_path):
        output_dir = str(tmp_path / "new_charts")
        results = {"daily": sample_df, "metrics": sample_metrics}
        save_all_charts(results, output_dir)
        assert os.path.isdir(output_dir)

    def test_returns_dict_keys(self, sample_df, sample_metrics, tmp_path):
        output_dir = str(tmp_path / "charts")
        results = {"daily": sample_df, "metrics": sample_metrics}
        paths = save_all_charts(results, output_dir)
        assert set(paths.keys()) == {"equity_curve", "drawdown", "signal_overlay"}
