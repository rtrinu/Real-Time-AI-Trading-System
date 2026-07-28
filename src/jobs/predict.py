from datetime import datetime, date
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from training.trainer import ensemble_predict, save_prediction
from core.logger_config import logger
from broker.alpaca import execute_signal


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

    if result["signal"] != "hold":
        order = execute_signal(
            app.state.alpaca_client, symbol, result["signal"], result["confidence"]
        )
        logger.info(f"Order: {order}")
    else:
        logger.info("Hold signal — no trade")

    actions = {"buy": "Buy", "sell": "Sell", "hold": "Hold"}
    action = actions[result["signal"]]
    suggested = f"{action} {round(position_size * 100)}%" if position_size > 0 else "Hold"

    logger.info(
        f"Daily prediction: {symbol} → {suggested} (confidence={result['confidence']:.2f})"
    )


def start_predict_scheduler(app):
    predict_scheduler.add_job(
        daily_predict,
        CronTrigger(hour=16, minute=15, day_of_week="mon-fri"),
        args=[app],
        id="daily_predict",
        replace_existing=True,
    )
    predict_scheduler.start()
