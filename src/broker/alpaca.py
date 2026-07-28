from datetime import datetime, timezone
from core.config import settings
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from broker.risk import check_can_trade, validate_order
from db.trades import TradeAudit


def create_client() -> TradingClient:
    client = TradingClient(
        api_key=settings.alpaca_api_key,
        secret_key=settings.alpaca_secret_key,
        paper=settings.alpaca_paper,
    )
    return client


def _create_audit(session, symbol, signal, confidence, position_size, source):
    audit = TradeAudit(
        symbol=symbol,
        timestamp=datetime.now(timezone.utc),
        source=source,
        signal=signal,
        confidence=confidence,
        position_size=position_size,
        risk_check_passed=False,
        risk_check_reason="",
        validation_passed=False,
        validation_reason="",
        executed=False,
    )
    session.add(audit)
    session.commit()
    session.refresh(audit)
    return audit


def _update_audit(session, audit, **kwargs):
    for k, v in kwargs.items():
        setattr(audit, k, v)
    session.add(audit)
    session.commit()


def execute_signal(client, symbol, signal, confidence, max_shares: int = 10, session=None, source="manual"):
    audit = _create_audit(session, symbol, signal, confidence, position_size=confidence, source=source) if session else None

    result = {"executed": False}

    if signal == "hold":
        result["reason"] = "hold signal"
        if audit:
            _update_audit(session, audit, risk_check_reason="hold signal", executed=False)
            result["audit_id"] = audit.id
        return result

    can_trade, reason = check_can_trade(client, symbol, signal)
    if not can_trade:
        result["reason"] = reason
        if audit:
            _update_audit(session, audit, risk_check_passed=False, risk_check_reason=reason, executed=False)
            result["audit_id"] = audit.id
        return result
    if audit:
        audit.risk_check_passed = True

    side = OrderSide.BUY if signal == "buy" else OrderSide.SELL
    qty = max(1, min(max_shares, int(confidence * max_shares)))

    validation = validate_order(client, symbol, side, qty)
    if not validation["valid"]:
        result["reason"] = validation["reason"]
        if audit:
            _update_audit(session, audit, risk_check_passed=True, validation_passed=False, validation_reason=validation["reason"], executed=False)
            result["audit_id"] = audit.id
        return result
    if audit:
        audit.validation_passed = True

    try:
        order = client.submit_order(
            MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=side,
                time_in_force=TimeInForce.DAY,
            )
        )
        if audit:
            _update_audit(session, audit, risk_check_passed=True, validation_passed=True, executed=True,
                         order_id=order.id, order_side=side.value, order_qty=qty,
                         order_status=str(order.status) if hasattr(order, "status") else None)
        result.update({"executed": True, "order_id": order.id, "qty": qty, "side": side.value})
        if audit:
            result["audit_id"] = audit.id
        return result
    except Exception as e:
        if audit:
            _update_audit(session, audit, risk_check_passed=True, validation_passed=True, executed=False, error_message=str(e))
        raise
