from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from db.create_engine import get_session
from db.trades import TradeAudit
from sqlmodel import select, col
from core.logger_config import logger

fill_poller_scheduler = AsyncIOScheduler()


def poll_order_fills(app):
    session = get_session()
    client = getattr(app.state, "alpaca_client", None)
    if not client:
        session.close()
        return

    unfilled = session.exec(
        select(TradeAudit).where(
            TradeAudit.executed == True,
            TradeAudit.order_id != None,
            TradeAudit.order_filled_qty == None,
        )
    ).all()

    if not unfilled:
        session.close()
        return

    logger.info(f"Polling fills for {len(unfilled)} orders")

    for audit in unfilled:
        try:
            order = client.get_order_by_id(audit.order_id)
            if order.status == "filled":
                audit.order_filled_qty = float(order.filled_qty)
                audit.order_filled_avg_price = float(order.filled_avg_price)
                audit.order_status = order.status
                session.add(audit)
                logger.info(
                    f"Order {audit.order_id} filled: {order.filled_qty} @ {order.filled_avg_price}"
                )
            elif order.status in ("canceled", "expired", "rejected"):
                audit.order_status = order.status
                session.add(audit)
        except Exception as e:
            logger.error(f"Failed to poll order {audit.order_id}: {e}")

    session.commit()
    session.close()


def start_fill_poller(app):
    fill_poller_scheduler.add_job(
        poll_order_fills,
        CronTrigger(hour="16-19", minute="0,15,30,45", day_of_week="mon-fri"),
        args=[app],
        id="fill_poller",
        replace_existing=True,
    )
    fill_poller_scheduler.start()
