from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from ml.xgboost import XGBoostModel
from training.trainer import train, save_model
from training.configs import FEATURE_GROUPS

router = APIRouter()


class TrainRequest(BaseModel):
    symbol: str
    signal: str = "signal_5"
    features: list[str] = ["ReturnsFeatures", "Sentiment"]
    hyperparameters: dict = {}


@router.post("/train")
def train_model(request: TrainRequest, req: Request):
    unknown = [f for f in request.features if f not in FEATURE_GROUPS]
    if unknown:
        raise HTTPException(
            status_code=400, detail=f"Unknown feature groups: {unknown}"
        )

    app_models = getattr(req.app.state, "models", None)
    if app_models is None:
        app_models = {}
        req.app.state.models = app_models

    try:
        model = XGBoostModel(**request.hyperparameters)
        report = train(model, request.features, request.signal, request.symbol)
        model_path = save_model(model, request.features, request.signal, request.symbol)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Training failed: {e}")

    ensemble_key = "+".join(f.replace("Features", "") for f in request.features)
    app_models[ensemble_key] = {"model": model, "features": request.features}

    return {
        "symbol": request.symbol,
        "signal": request.signal,
        "features": request.features,
        "ensemble_key": ensemble_key,
        "model_path": model_path,
        "report": report,
    }
