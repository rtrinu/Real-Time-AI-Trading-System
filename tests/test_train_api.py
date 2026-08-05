import pytest
from unittest.mock import MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from api.routes.train import router

app = FastAPI()
app.include_router(router)
app.state.models = {}
client = TestClient(app)


@pytest.fixture
def mock_training():
    model = MagicMock()
    with patch("api.routes.train.XGBoostModel", return_value=model), patch(
        "api.routes.train.train", return_value="classification report"
    ), patch("api.routes.train.save_model", return_value="models/AAPL.joblib"):
        yield model


class TestTrainModel:
    def test_trains_and_registers_model(self, mock_training):
        response = client.post(
            "/train",
            json={"symbol": "AAPL", "features": ["MomentumFeatures", "Sentiment"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"
        assert data["signal"] == "signal_5"
        assert data["features"] == ["MomentumFeatures", "Sentiment"]
        assert data["ensemble_key"] == "Momentum+Sentiment"
        assert data["model_path"] == "models/AAPL.joblib"
        assert data["report"] == "classification report"
        assert app.state.models["Momentum+Sentiment"]["features"] == [
            "MomentumFeatures",
            "Sentiment",
        ]

    def test_applies_defaults(self, mock_training):
        response = client.post("/train", json={"symbol": "AAPL"})
        assert response.status_code == 200
        data = response.json()
        assert data["signal"] == "signal_5"
        assert data["features"] == ["ReturnsFeatures", "Sentiment"]
        assert data["ensemble_key"] == "Returns+Sentiment"

    def test_passes_hyperparameters(self, mock_training):
        client.post(
            "/train",
            json={
                "symbol": "AAPL",
                "hyperparameters": {"n_estimators": 200, "max_depth": 5},
            },
        )
        from api.routes import train as train_module

        train_module.XGBoostModel.assert_called_once_with(
            n_estimators=200, max_depth=5
        )

    def test_returns_400_on_unknown_feature_group(self):
        response = client.post(
            "/train", json={"symbol": "AAPL", "features": ["BogusFeatures"]}
        )
        assert response.status_code == 400
        assert "BogusFeatures" in response.json()["detail"]

    def test_returns_400_on_no_training_data(self):
        with patch("api.routes.train.XGBoostModel", return_value=MagicMock()), patch(
            "api.routes.train.train",
            side_effect=ValueError("No data found for ReturnsFeatures symbol=MSFT"),
        ):
            response = client.post("/train", json={"symbol": "MSFT"})
        assert response.status_code == 400
        assert "No data found for ReturnsFeatures symbol=MSFT" in response.json()["detail"]

    def test_returns_502_on_training_error(self):
        with patch("api.routes.train.XGBoostModel", return_value=MagicMock()), patch(
            "api.routes.train.train", side_effect=Exception("no data")
        ):
            response = client.post("/train", json={"symbol": "AAPL"})
        assert response.status_code == 502
        assert "no data" in response.json()["detail"]

    def test_initializes_models_state_if_missing(self, mock_training):
        app.state.models = None
        response = client.post("/train", json={"symbol": "AAPL"})
        assert response.status_code == 200
        assert "Returns+Sentiment" in app.state.models
        app.state.models = {}
