from fastapi import APIRouter, Request
from pydantic import BaseModel
from training.trainer import predict

router = APIRouter()


class PredictRequest(BaseModel):
    symbol: str
    signal: str = "signal_5"
    features: list[str] = ["ReturnsFeatures", "Sentiment"]


@router.post("/predict")
def predict_signal(request: PredictRequest, req: Request):
    model = req.app.state.model
    result = predict(model, request.features, request.signal, request.symbol)
    return result
