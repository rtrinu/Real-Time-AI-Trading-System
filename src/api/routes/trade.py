from fastapi import APIRouter, Request
from pydantic import BaseModel
from broker.risk import check_can_trade, validate_order
from broker.alpaca import execute_signal
from training.trainer import save_prediction
from alpaca.trading.enums import OrderSide

router = APIRouter()


class TradeRequest(BaseModel):
    symbol: str = "AAPL"
    signal: str
    confidence: float
    max_shares: int = 10


@router.post("/trade")
def trade(body: TradeRequest, request: Request):
    client = request.app.state.alpaca_client

    if body.signal == "hold":
        return {"executed": False, "reason": "Signal is hold"}

    can_trade, reason = check_can_trade(client, body.symbol, body.signal)
    if not can_trade:
        return {"executed": False, "reason": reason}

    side = OrderSide.BUY if body.signal == "buy" else OrderSide.SELL
    qty = max(1, min(body.max_shares, int(body.confidence * body.max_shares)))

    validation = validate_order(client, body.symbol, side, qty)
    if not validation["valid"]:
        return {"executed": False, "reason": validation["reason"]}

    order = execute_signal(
        client, body.symbol, body.signal, body.confidence, body.max_shares
    )

    save_prediction(
        symbol=body.symbol,
        signal=body.signal,
        confidence=body.confidence,
        position_size=body.confidence,
    )

    return order
