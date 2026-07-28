from core.config import settings
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from broker.risk import check_can_trade


def create_client() -> TradingClient:
    client = TradingClient(
        api_key=settings.alpaca_api_key,
        secret_key=settings.alpaca_secret_key,
        paper=settings.alpaca_paper,
    )
    return client


def execute_signal(client, symbol, signal, confidence, max_shares: int = 10):
    if signal == "hold":
        return {"executed": False, "reason": "hold signal"}

    can_trade, reason = check_can_trade(client, symbol, signal)
    if not can_trade:
        return {"executed": False, "reason": reason}

    side = OrderSide.BUY if signal == "buy" else OrderSide.SELL
    qty = max(1, min(max_shares, int(confidence * max_shares)))
    order = client.submit_order(
        MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=side,
            time_in_force=TimeInForce.DAY,
        )
    )

    return {"executed": True, "order_id": order.id, "qty": qty, "side": side.value}
