from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from broker.alpaca import execute_signal
from training.trainer import save_prediction
from core.logger_config import logger
from db.create_engine import get_session

router = APIRouter()


class TradeRequest(BaseModel):
    symbol: str = "AAPL"
    signal: str
    confidence: float
    max_shares: int = 10


@router.post("/trade")
def trade(body: TradeRequest, request: Request):
    client = getattr(request.app.state, "alpaca_client", None)
    if not client:
        raise HTTPException(status_code=503, detail="Alpaca client not initialized")

    session = get_session()
    try:
        order = execute_signal(
            client, body.symbol, body.signal, body.confidence, body.max_shares,
            session=session, source="manual"
        )
    except Exception as e:
        session.close()
        raise HTTPException(status_code=502, detail=f"Order execution failed: {e}")
    session.close()

    try:
        save_prediction(
            symbol=body.symbol,
            signal=body.signal,
            confidence=body.confidence,
            position_size=body.confidence,
        )
    except Exception as e:
        logger.error(f"Failed to save trade prediction: {e}")

    return order
