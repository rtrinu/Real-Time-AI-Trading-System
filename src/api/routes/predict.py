from fastapi import APIRouter, Request
from pydantic import BaseModel
from training.trainer import ensemble_predict, save_prediction

router = APIRouter()


class PredictRequest(BaseModel):
    symbol: str
    signal: str = "signal_5"


@router.post("/predict")
def predict_signal(request: PredictRequest, req: Request):
    models = req.app.state.models
    result = ensemble_predict(models, request.signal, request.symbol)
    position_size = result["confidence"] if result["signal"] != "hold" else 0
    actions = {"buy": "Buy", "sell": "Sell", "hold": "Hold"}
    action = actions[result["signal"]]
    suggested = f"{action} {round(position_size*100)}%" if position_size > 0 else "Hold"

    save_prediction(
        symbol=request.symbol,
        signal=result["signal"],
        confidence=result["confidence"],
        position_size=position_size,
    )

    return {
        "symbol": request.symbol,
        "signal": result["signal"],
        "confidence": result["confidence"],
        "position_size": position_size,
        "suggested_action": suggested,
        "date": result["date"],
    }
