from fastapi import APIRouter, Request
from pydantic import BaseModel
from training.trainer import ensemble_predict

router = APIRouter()


class PredictRequest(BaseModel):
    symbol: str
    signal: str = "signal_5"


@router.post("/predict")
def predict_signal(request: PredictRequest, req: Request):
    models = req.app.state.models
    result = ensemble_predict(models, request.signal, request.symbol)
    return result
