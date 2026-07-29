from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import MarketOrderRequest
from db.create_engine import get_session
from broker.alpaca import _create_audit, _update_audit
from core.logger_config import logger

TAKE_PROFIT_PCT = 5.0
STOP_LOSS_PCT = -3.0

position_scheduler = AsyncIOScheduler()


def manage_positions(app):
    client = getattr(app.state, "alpaca_client", None)
    if not client:
        return

    try:
        positions = client.get_all_positions()
    except Exception as e:
        logger.error(f"Failed to fetch positions: {e}")
        return

    for pos in positions:
        try:
            symbol = pos.symbol
            qty = float(pos.qty)
            if qty == 0:
                continue

            plpc = float(pos.unrealized_plpc) * 100
            direction = "long" if qty > 0 else "short"

            action = None
            if plpc >= TAKE_PROFIT_PCT:
                action = "take_profit"
            elif plpc <= STOP_LOSS_PCT:
                action = "stop_loss"

            if not action:
                continue

            close_signal = "sell" if direction == "long" else "buy"
            close_qty = abs(int(qty))
            close_side = OrderSide.SELL if close_signal == "sell" else OrderSide.BUY

            session = get_session()
            audit = _create_audit(
                session,
                symbol,
                close_signal,
                confidence=1.0,
                position_size=1.0,
                source="position_manager",
            )

            try:
                order = client.submit_order(
                    MarketOrderRequest(
                        symbol=symbol,
                        qty=close_qty,
                        side=close_side,
                        time_in_force=TimeInForce.DAY,
                    )
                )
                _update_audit(
                    session,
                    audit,
                    risk_check_passed=True,
                    validation_passed=True,
                    executed=True,
                    order_id=order.id,
                    order_side=close_side.value,
                    order_qty=close_qty,
                    order_status=(
                        str(order.status) if hasattr(order, "status") else None
                    ),
                )
                logger.info(
                    f"Position {action}: closed {close_qty} {symbol} ({direction}, P&L={plpc:+.1f}%)"
                )
            except Exception as e:
                _update_audit(
                    session,
                    audit,
                    risk_check_passed=True,
                    validation_passed=True,
                    executed=False,
                    error_message=str(e),
                )
                logger.error(f"Failed to close {symbol} position: {e}")

            session.close()
        except Exception as e:
            logger.error(f"Error processing position {pos.symbol}: {e}")
            continue


def start_position_scheduler(app):
    if not position_scheduler.get_job("position_manager"):
        position_scheduler.add_job(
            manage_positions,
            CronTrigger(
                day_of_week="mon-fri", hour=15, minute=50, timezone="US/Eastern"
            ),
            args=[app],
            id="position_manager",
            replace_existing=True,
        )
        position_scheduler.start()
