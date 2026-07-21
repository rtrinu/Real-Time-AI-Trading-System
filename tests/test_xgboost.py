import pytest
import numpy as np
import pandas as pd
import os
import tempfile
from ml.xgboost import XGBoostModel


@pytest.fixture
def sample_data():
    np.random.seed(42)
    n = 100
    X = pd.DataFrame(
        {
            "feat_a": np.random.randn(n),
            "feat_b": np.random.randn(n),
            "feat_c": np.random.randn(n),
        }
    )
    y = pd.Series(np.random.choice([0, 1, 2], size=n))
    return X, y


@pytest.fixture
def model():
    return XGBoostModel()


class TestXGBoostModelInit:
    def test_default_params(self, model):
        assert model.n_estimators == 50
        assert model.max_depth == 3
        assert model.learning_rate == 0.05
        assert model.subsample == 0.8
        assert model.colsample_bytree == 0.8

    def test_model_is_xgb_classifier(self, model):
        from xgboost import XGBClassifier

        assert isinstance(model.model, XGBClassifier)


class TestTrain:
    def test_train_basic(self, model, sample_data):
        X, y = sample_data
        model.train(X, y)
        preds = model.predict(X)
        assert len(preds) == len(y)
        assert set(preds).issubset({0, 1, 2})

    def test_train_with_eval_set(self, model, sample_data):
        X, y = sample_data
        split = 80
        model.train(X[:split], y[:split], x_val=X[split:], y_val=y[split:])
        preds = model.predict(X)
        assert len(preds) == len(y)

    def test_train_without_eval_set(self, model, sample_data):
        X, y = sample_data
        model.train(X, y)
        preds = model.predict(X)
        assert len(preds) == len(y)


class TestPredict:
    def test_predict_returns_numpy_array(self, model, sample_data):
        X, y = sample_data
        model.train(X, y)
        preds = model.predict(X.iloc[:5])
        assert isinstance(preds, np.ndarray)

    def test_predict_single_row(self, model, sample_data):
        X, y = sample_data
        model.train(X, y)
        pred = model.predict(X.iloc[:1])
        assert len(pred) == 1
        assert pred[0] in {0, 1, 2}


class TestPredictProba:
    def test_predict_proba_returns_probabilities(self, model, sample_data):
        X, y = sample_data
        model.train(X, y)
        proba = model.predict_proba(X.iloc[:5])
        assert proba.shape == (5, 3)
        assert np.allclose(proba.sum(axis=1), 1.0)

    def test_predict_proba_all_positive(self, model, sample_data):
        X, y = sample_data
        model.train(X, y)
        proba = model.predict_proba(X.iloc[:5])
        assert np.all(proba >= 0)


class TestEvaluate:
    def test_evaluate_returns_string(self, model, sample_data):
        X, y = sample_data
        model.train(X[:80], y[:80])
        report = model.evaluate(X[80:], y[80:])
        assert isinstance(report, str)

    def test_evaluate_contains_classes(self, model, sample_data):
        X, y = sample_data
        model.train(X[:80], y[:80])
        report = model.evaluate(X[80:], y[80:])
        assert "sell" in report
        assert "hold" in report
        assert "buy" in report


class TestSaveLoad:
    def test_save_creates_file(self, model, sample_data):
        X, y = sample_data
        model.train(X, y)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test_model.joblib")
            model.save(path)
            assert os.path.exists(path)

    def test_load_restores_model(self, model, sample_data):
        X, y = sample_data
        model.train(X, y)
        original_preds = model.predict(X.iloc[:5])

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test_model.joblib")
            model.save(path)

            new_model = XGBoostModel()
            new_model.load(path)
            loaded_preds = new_model.predict(X.iloc[:5])

        np.testing.assert_array_equal(original_preds, loaded_preds)

    def test_save_load_preserves_predictions(self, model, sample_data):
        X, y = sample_data
        model.train(X, y)
        original_proba = model.predict_proba(X.iloc[:3])

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test_model.joblib")
            model.save(path)

            new_model = XGBoostModel()
            new_model.load(path)
            loaded_proba = new_model.predict_proba(X.iloc[:3])

        np.testing.assert_array_almost_equal(original_proba, loaded_proba)
