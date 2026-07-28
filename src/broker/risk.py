from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from broker.alpaca import client, get_account


def check_can_trade(client, symbol, signal, max_position_pct: float = 0.3):
    positions = client.get_all_positions()
    equity = float(account.equity)
    for pos in positions:
        if pos.symbol != symbol:
            continue
        qty = float(pos.qty)
        current_pct = float(pos.market_value) / equity

        if qty > 0 and signal == "buy":
            return False, "Already long, skipping buy signal"
        if qty < 0 and signal == "sell":
            return False, "Already short, skipping sell signal"
        if current_pct >= max_position_pct:
            return (
                False,
                f"Position ({current_pct:.1%}) exceeds max ({max_position_pct:.0%})",
            )
        return True, ""


def execute_signal(client, symbol, signal, confidence, max_shares: int = 10):
    if signal == "hold":
        return {"executed": False, "reason": "hold signal"}

    can_trade = reason = check_can_trade(client, symbol, signal)
    if not can_trade:
        return {"executed": False, "reason": reason}

    side = OrderSide.BUY if signal == "buy" else OrderSide.SELL
    qty = max(1, min(max_shares, int(confidence * max_shares)))
    order = client.submit_order(MarketOrderRequest(symbol, qty, side, TimeInForce.DAY))

    return {"executed": True, "order_id": order.id, "qty": qty, "side": side.value}


def validate_order(client, symbol, side, qty):
    account = client.get_account()
    if not client.get_clock().is_open:
        return {"Order Validated": False, "reason": "Market is closed"}
    trade = client.get_latest_trade(symbol)
    price = trade.price
    valid_buying_power = float(account.buying_power) >= qty * price
    if not valid_buying_power:
        return {"Order Validated": False, "reason": "Invalid buying power"}
    return {"Order Validated": True, "reason": ""}
