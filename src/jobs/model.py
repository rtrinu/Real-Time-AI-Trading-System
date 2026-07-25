import os
from datetime import datetime, date
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from ml.xgboost import XGBoostModel
from training.trainer import train, save_model, load_trained_model, _feature_key
from core.logger_config import logger

model_scheduler = AsyncIOScheduler()

ENSEMBLE = [
    ["MomentumFeatures", "Sentiment"],
    ["MomentumFeatures", "Sentiment", "MeanReversionFeatures"],
    ["MomentumFeatures", "MeanReversionFeatures"],
]


def retrain_model(app):
    symbol = "AAPL"
    signal = "signal_5"

    for features in ENSEMBLE:
        key = _feature_key(features)
        model_path = f"models/{symbol}_{signal}_{key}.joblib"

        if os.path.exists(model_path):
            mtime = datetime.fromtimestamp(os.path.getmtime(model_path)).date()
            if mtime == date.today():
                logger.info(f"Model already trained today ({mtime}), skipping: {key}")
                continue

        model = XGBoostModel()
        train(model, features, signal, symbol)
        save_model(model, features, signal, symbol)

        ensemble_key = "+".join(f.replace("Features", "") for f in features)
        app.state.models[ensemble_key] = {"model": model, "features": features}
        logger.info(f"Model retrained: {ensemble_key}")

    logger.info("Ensemble retrained")


def start_model_scheduler(app):
    model_scheduler.add_job(
        retrain_model,
        CronTrigger(hour=18, minute=0),
        args=[app],
        id="retrain",
        replace_existing=True,
    )
    model_scheduler.start()
