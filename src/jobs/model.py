import os
from datetime import datetime, date
from core.config import settings
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from ml.xgboost import XGBoostModel
from training.trainer import train, save_model
from core.logger_config import logger

model_scheduler = AsyncIOScheduler()


def retrain_model(app):
    symbol = "AAPL"
    signal = "signal_5"
    model_path = f"models/{symbol}_{signal}.joblib"

    if os.path.exists(model_path):
        mtime = datetime.fromtimestamp(os.path.getmtime(model_path)).date()
        if mtime == date.today():
            logger.info(f"Model already trained today ({mtime}), skipping")
            return
    model = XGBoostModel()
    train(model, ["ReturnsFeatures", "Sentiment"], signal, symbol)
    save_model(model, ["ReturnsFeatures", "Sentiment"], signal, symbol)
    app.state.model = model
    logger.info("Model retrained and saved")


def start_model_scheduler(app):
    model_scheduler.add_job(
        retrain_model,
        CronTrigger(hour=18, minute=0),
        args=[app],
        id="retrain",
        replace_existing=True,
    )
    model_scheduler.start()
