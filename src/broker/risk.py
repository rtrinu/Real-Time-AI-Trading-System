from alpaca.trading.client import TradingClient
from core.logger_config import logger


def check_can_trade(
    client: TradingClient, symbol: str, signal: str, max_position_pct: float = 0.3
):
    try:
        account = client.get_account()
        equity = float(account.equity)
        positions = client.get_all_positions()

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
    except Exception as e:
        logger.error(f"Risk check failed for {symbol}: {e}")
        return False, f"Risk check error: {e}"


def validate_order(client: TradingClient, symbol: str, side: str, qty: int):
    try:
        account = client.get_account()
        if not client.get_clock().is_open:
            return {"valid": False, "reason": "Market is closed"}
        trade = client.get_latest_trade(symbol)
        price = trade.price
        valid_buying_power = float(account.buying_power) >= qty * price
        if not valid_buying_power:
            return {"valid": False, "reason": "Insufficient buying power"}
        return {"valid": True, "reason": ""}
    except Exception as e:
        logger.error(f"Order validation failed for {symbol}: {e}")
        return {"valid": False, "reason": f"Validation error: {e}"}
