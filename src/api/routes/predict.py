from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from training.trainer import ensemble_predict, save_prediction
from core.logger_config import logger

router = APIRouter()


class PredictRequest(BaseModel):
    symbol: str
    signal: str = "signal_5"


@router.post("/predict")
def predict_signal(request: PredictRequest, req: Request):
    models = getattr(req.app.state, "models", None)
    if not models:
        raise HTTPException(status_code=503, detail="Models not loaded")

    try:
        result = ensemble_predict(models, request.signal, request.symbol)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Prediction failed: {e}")

    position_size = result["confidence"] if result["signal"] != "hold" else 0
    actions = {"buy": "Buy", "sell": "Sell", "hold": "Hold"}
    action = actions[result["signal"]]
    suggested = f"{action} {round(position_size*100)}%" if position_size > 0 else "Hold"

    try:
        save_prediction(
            symbol=request.symbol,
            signal=result["signal"],
            confidence=result["confidence"],
            position_size=position_size,
        )
    except Exception as e:
        logger.error(f"Failed to save prediction: {e}")

    return {
        "symbol": request.symbol,
        "signal": result["signal"],
        "confidence": result["confidence"],
        "position_size": position_size,
        "suggested_action": suggested,
        "date": result["date"],
    }
