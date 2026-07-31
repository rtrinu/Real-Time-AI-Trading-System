from datetime import datetime, date
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from training.trainer import ensemble_predict, save_prediction
from core.logger_config import logger
from core.notifications import notify
from broker.alpaca import execute_signal
from db.create_engine import get_session


predict_scheduler = AsyncIOScheduler()


def daily_predict(app, symbol="AAPL", signal="signal_5"):
    models = app.state.models
    result = ensemble_predict(models, signal, symbol)

    position_size = result["confidence"] if result["signal"] != "hold" else 0.0

    save_prediction(
        symbol=symbol,
        signal=result["signal"],
        confidence=result["confidence"],
        position_size=position_size,
    )

    session = get_session()
    if result["signal"] != "hold":
        order = execute_signal(
            app.state.alpaca_client,
            symbol,
            result["signal"],
            result["confidence"],
            session=session,
            source="scheduler",
        )
        logger.info(f"Order: {order}")
        if order.get("executed"):
            notify(
                f"📈 **{symbol} {result['signal'].upper()}** "
                f"{order.get('qty', '?')} shares "
                f"(confidence={result['confidence']:.0%})"
            )
        else:
            notify(f"⏸️ **{symbol} skipped** — {order.get('reason', 'unknown')}")
    else:
        logger.info("Hold signal — no trade")
        notify(f"⏸️ **{symbol} HOLD** " f"(confidence={result['confidence']:.0%})")
    session.close()

    actions = {"buy": "Buy", "sell": "Sell", "hold": "Hold"}
    action = actions[result["signal"]]
    suggested = (
        f"{action} {round(position_size * 100)}%" if position_size > 0 else "Hold"
    )

    logger.info(
        f"Daily prediction: {symbol} → {suggested} (confidence={result['confidence']:.2f})"
    )


def start_predict_scheduler(app):
    predict_scheduler.add_job(
        daily_predict,
        CronTrigger(hour=9, minute=35, day_of_week="mon-fri", timezone="US/Eastern"),
        args=[app],
        id="daily_predict",
        replace_existing=True,
    )
    predict_scheduler.start()
