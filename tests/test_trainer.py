import pytest
import numpy as np
import pandas as pd
import os
import tempfile
import json
from unittest.mock import patch, MagicMock
from ml.xgboost import XGBoostModel
from training.trainer import create_split, save_model, load_trained_model, predict


@pytest.fixture
def sample_X():
    return pd.DataFrame(
        {
            "feat_a": range(100),
            "feat_b": range(100),
            "feat_c": range(100),
        }
    )


@pytest.fixture
def sample_y():
    return pd.Series([0] * 30 + [1] * 40 + [2] * 30)


@pytest.fixture
def trained_model():
    np.random.seed(42)
    X = pd.DataFrame(
        {
            "feat_a": np.random.randn(100),
            "feat_b": np.random.randn(100),
        }
    )
    y = pd.Series(np.random.choice([0, 1, 2], size=100))
    model = XGBoostModel()
    model.train(X, y)
    return model


class TestCreateSplit:
    def test_split_sizes(self, sample_X, sample_y):
        x_train, x_test, y_train, y_test = create_split(sample_X, sample_y, test_ratio=0.2)
        assert len(x_train) == 80
        assert len(x_test) == 20
        assert len(y_train) == 80
        assert len(y_test) == 20

    def test_split_preserves_order(self, sample_X, sample_y):
        x_train, x_test, y_train, y_test = create_split(sample_X, sample_y, test_ratio=0.2)
        assert x_train["feat_a"].iloc[0] == 0
        assert x_test["feat_a"].iloc[0] == 80

    def test_split_different_ratios(self, sample_X, sample_y):
        x_train, x_test, _, _ = create_split(sample_X, sample_y, test_ratio=0.3)
        assert len(x_train) == 70
        assert len(x_test) == 30

    def test_split_data_not_shuffled(self, sample_X, sample_y):
        x_train, x_test, _, _ = create_split(sample_X, sample_y)
        assert list(x_train["feat_a"]) == list(range(80))
        assert list(x_test["feat_a"]) == list(range(80, 100))


class TestSaveModel:
    def test_save_creates_files(self, trained_model):
        features = ["ReturnsFeatures", "Sentiment"]
        signal = "signal_5"
        symbol = "AAPL"
        with tempfile.TemporaryDirectory() as tmpdir:
            save_model(trained_model, features, signal, symbol, path=tmpdir)
            assert os.path.exists(os.path.join(tmpdir, "AAPL_signal_5.joblib"))
            assert os.path.exists(os.path.join(tmpdir, "AAPL_signal_5_meta.json"))

    def test_save_metadata_content(self, trained_model):
        features = ["ReturnsFeatures", "Sentiment"]
        signal = "signal_5"
        symbol = "AAPL"
        with tempfile.TemporaryDirectory() as tmpdir:
            save_model(trained_model, features, signal, symbol, path=tmpdir)
            meta_path = os.path.join(tmpdir, "AAPL_signal_5_meta.json")
            with open(meta_path) as f:
                meta = json.load(f)
            assert meta["features"] == features
            assert meta["signal"] == signal
            assert meta["symbol"] == symbol

    def test_save_creates_directory(self, trained_model):
        features = ["ReturnsFeatures"]
        signal = "signal_5"
        symbol = "TEST"
        with tempfile.TemporaryDirectory() as tmpdir:
            nested = os.path.join(tmpdir, "sub", "dir")
            save_model(trained_model, features, signal, symbol, path=nested)
            assert os.path.exists(os.path.join(nested, "TEST_signal_5.joblib"))


class TestLoadTrainedModel:
    def test_load_returns_model(self, trained_model):
        features = ["ReturnsFeatures", "Sentiment"]
        signal = "signal_5"
        symbol = "AAPL"
        with tempfile.TemporaryDirectory() as tmpdir:
            save_model(trained_model, features, signal, symbol, path=tmpdir)
            loaded = load_trained_model(features, signal, symbol, path=tmpdir)
            assert loaded is not None
            assert isinstance(loaded, XGBoostModel)

    def test_load_preserves_predictions(self, trained_model):
        features = ["ReturnsFeatures", "Sentiment"]
        signal = "signal_5"
        symbol = "AAPL"
        np.random.seed(99)
        X = pd.DataFrame({"feat_a": np.random.randn(5), "feat_b": np.random.randn(5)})
        original_preds = trained_model.predict(X)

        with tempfile.TemporaryDirectory() as tmpdir:
            save_model(trained_model, features, signal, symbol, path=tmpdir)
            loaded = load_trained_model(features, signal, symbol, path=tmpdir)
            loaded_preds = loaded.predict(X)

        np.testing.assert_array_equal(original_preds, loaded_preds)

    def test_load_returns_none_when_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = load_trained_model(["a"], "sig", "SYM", path=tmpdir)
            assert result is None

    def test_load_returns_none_on_feature_mismatch(self, trained_model):
        features = ["ReturnsFeatures", "Sentiment"]
        signal = "signal_5"
        symbol = "AAPL"
        with tempfile.TemporaryDirectory() as tmpdir:
            save_model(trained_model, features, signal, symbol, path=tmpdir)
            result = load_trained_model(["OtherFeatures"], signal, symbol, path=tmpdir)
            assert result is None

    def test_load_returns_none_on_signal_mismatch(self, trained_model):
        features = ["ReturnsFeatures", "Sentiment"]
        signal = "signal_5"
        symbol = "AAPL"
        with tempfile.TemporaryDirectory() as tmpdir:
            save_model(trained_model, features, signal, symbol, path=tmpdir)
            result = load_trained_model(features, "signal_10", symbol, path=tmpdir)
            assert result is None


class TestPredict:
    def test_predict_returns_dict(self, trained_model):
        mock_features = pd.DataFrame(
            {
                "feat_a": [0.5],
                "feat_b": [0.3],
            }
        )
        mock_date = "2026-06-22"
        with patch("training.trainer.load_latest_features", return_value=(mock_features, mock_date)):
            result = predict(trained_model, ["test"], "signal_5", "AAPL")
        assert isinstance(result, dict)
        assert "signal" in result
        assert "confidence" in result
        assert "date" in result

    def test_predict_signal_values(self, trained_model):
        mock_features = pd.DataFrame(
            {
                "feat_a": [0.5],
                "feat_b": [0.3],
            }
        )
        mock_date = "2026-06-22"
        with patch("training.trainer.load_latest_features", return_value=(mock_features, mock_date)):
            result = predict(trained_model, ["test"], "signal_5", "AAPL")
        assert result["signal"] in {"sell", "hold", "buy"}
        assert 0 <= result["confidence"] <= 1
        assert result["date"] == "2026-06-22"

    def test_predict_empty_features(self, trained_model):
        mock_features = pd.DataFrame()
        mock_date = ""
        with patch("training.trainer.load_latest_features", return_value=(mock_features, mock_date)):
            result = predict(trained_model, ["test"], "signal_5", "AAPL")
        assert result["signal"] == "hold"
        assert result["confidence"] == 0.0
        assert result["date"] == ""
