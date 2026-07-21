import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
from training.data_loader import add_calendar_features


class TestAddCalendarFeatures:
    def test_adds_all_columns(self):
        df = pd.DataFrame(
            {
                "symbol": ["AAPL"],
                "date": ["2026-06-22"],
                "value": [1.0],
            }
        )
        result = add_calendar_features(df)
        expected_cols = [
            "day_of_week",
            "month",
            "quarter",
            "week_of_year",
            "is_month_end",
            "is_month_start",
            "is_friday",
            "is_monday",
        ]
        for col in expected_cols:
            assert col in result.columns

    def test_day_of_week_values(self):
        df = pd.DataFrame({"date": ["2026-06-22"]})  # Monday
        result = add_calendar_features(df)
        assert result["day_of_week"].iloc[0] == 0  # Monday = 0

    def test_is_monday(self):
        df = pd.DataFrame({"date": ["2026-06-22"]})  # Monday
        result = add_calendar_features(df)
        assert result["is_monday"].iloc[0] == 1
        assert result["is_friday"].iloc[0] == 0

    def test_is_friday(self):
        df = pd.DataFrame({"date": ["2026-06-26"]})  # Friday
        result = add_calendar_features(df)
        assert result["is_friday"].iloc[0] == 1
        assert result["is_monday"].iloc[0] == 0

    def test_month_value(self):
        df = pd.DataFrame({"date": ["2026-06-22"]})
        result = add_calendar_features(df)
        assert result["month"].iloc[0] == 6

    def test_quarter_value(self):
        df = pd.DataFrame({"date": ["2026-06-22"]})
        result = add_calendar_features(df)
        assert result["quarter"].iloc[0] == 2

    def test_multiple_rows(self):
        df = pd.DataFrame(
            {
                "date": ["2026-06-22", "2026-06-23", "2026-06-26"],
            }
        )
        result = add_calendar_features(df)
        assert len(result) == 3
        assert result["day_of_week"].tolist() == [0, 1, 4]

    def test_preserves_existing_columns(self):
        df = pd.DataFrame(
            {
                "symbol": ["AAPL", "AAPL"],
                "date": ["2026-06-22", "2026-06-23"],
                "value": [1.0, 2.0],
            }
        )
        result = add_calendar_features(df)
        assert "symbol" in result.columns
        assert "value" in result.columns
        assert result["value"].tolist() == [1.0, 2.0]

    def test_is_month_end(self):
        df = pd.DataFrame({"date": ["2026-06-30"]})
        result = add_calendar_features(df)
        assert result["is_month_end"].iloc[0] == 1

    def test_is_month_start(self):
        df = pd.DataFrame({"date": ["2026-07-01"]})
        result = add_calendar_features(df)
        assert result["is_month_start"].iloc[0] == 1


class TestLoadTrainingData:
    @patch("training.data_loader.get_session")
    def test_returns_X_and_y(self, mock_session):
        from training.data_loader import load_training_data

        mock_return_row = MagicMock()
        mock_return_row.model_dump.return_value = {
            "symbol": "AAPL",
            "timestamp": "2026-06-22 00:00:00",
            "log_ret_1": 0.01,
            "log_ret_5": 0.02,
            "log_ret_10": 0.03,
            "log_ret_20": 0.04,
            "pct_ret_1": 0.01,
            "pct_ret_5": 0.02,
            "pct_ret_10": 0.03,
            "pct_ret_20": 0.04,
            "roll_cum_ret_20": 0.05,
            "roll_mean_ret_20": 0.01,
            "roll_ret_z_20": 0.5,
            "signal_5": 1,
        }
        mock_sentiment_row = MagicMock()
        mock_sentiment_row.model_dump.return_value = {
            "symbol": "AAPL",
            "timestamp": "2026-06-22 00:00:00",
            "sentiment_mean": 0.3,
            "confidence_mean": 0.8,
            "headline_count": 5,
            "positive_count": 3,
            "negative_count": 2,
        }

        mock_exec = MagicMock()
        mock_exec.all.side_effect = [[mock_return_row], [mock_sentiment_row]]
        mock_session.return_value.exec.return_value = mock_exec

        X, y = load_training_data("AAPL", ["ReturnsFeatures", "Sentiment"], "signal_5")
        assert len(X) == 1
        assert len(y) == 1
        assert y.iloc[0] == 2  # signal_5=1 maps to class 2


class TestLoadLatestFeatures:
    @patch("training.data_loader.get_session")
    def test_returns_X_and_date(self, mock_session):
        from training.data_loader import load_latest_features

        mock_return_row = MagicMock()
        mock_return_row.model_dump.return_value = {
            "symbol": "AAPL",
            "timestamp": "2026-06-22 00:00:00",
            "log_ret_1": 0.01,
            "log_ret_5": 0.02,
            "log_ret_10": 0.03,
            "log_ret_20": 0.04,
            "pct_ret_1": 0.01,
            "pct_ret_5": 0.02,
            "pct_ret_10": 0.03,
            "pct_ret_20": 0.04,
            "roll_cum_ret_20": 0.05,
            "roll_mean_ret_20": 0.01,
            "roll_ret_z_20": 0.5,
            "signal_5": 1,
        }
        mock_sentiment_row = MagicMock()
        mock_sentiment_row.model_dump.return_value = {
            "symbol": "AAPL",
            "timestamp": "2026-06-22 00:00:00",
            "sentiment_mean": 0.3,
            "confidence_mean": 0.8,
            "headline_count": 5,
            "positive_count": 3,
            "negative_count": 2,
        }

        mock_exec = MagicMock()
        mock_exec.all.side_effect = [[mock_return_row], [mock_sentiment_row]]
        mock_session.return_value.exec.return_value = mock_exec

        X, date = load_latest_features(["ReturnsFeatures", "Sentiment"], "AAPL", "signal_5")
        assert not X.empty
        assert "signal_5" not in X.columns
        assert date == "2026-06-22"

    @patch("training.data_loader.get_session")
    def test_returns_empty_when_no_data(self, mock_session):
        from training.data_loader import load_latest_features

        mock_exec = MagicMock()
        mock_exec.all.return_value = []
        mock_session.return_value.exec.return_value = mock_exec

        X, date = load_latest_features(["ReturnsFeatures"], "AAPL", "signal_5")
        assert X.empty
        assert date == ""
