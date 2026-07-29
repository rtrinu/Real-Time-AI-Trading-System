import os
import json
from datetime import datetime, date
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from ml.xgboost import XGBoostModel
from training.trainer import train, save_model, load_trained_model, _feature_key
from training.configs import ENSEMBLE
from core.logger_config import logger
from core.notifications import notify

model_scheduler = AsyncIOScheduler()


def load_best_params():
    path = os.path.join("models", "best_params.json")
    try:
        with open(path) as f:
            return json.load(f)["params"]
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        return {}


def retrain_model(app):
    try:
        symbol = "AAPL"
        signal = "signal_5"
        best_params = load_best_params()

        for features in ENSEMBLE:
            try:
                model = load_trained_model(features, signal, symbol)
                if model is not None:
                    model_path = (
                        f"models/{symbol}_{signal}_{_feature_key(features)}.joblib"
                    )
                    mtime = datetime.fromtimestamp(os.path.getmtime(model_path)).date()
                    if mtime == date.today():
                        logger.info(f"Model already trained today, skipping")
                        ensemble_key = "+".join(
                            f.replace("Features", "") for f in features
                        )
                        app.state.models[ensemble_key] = {
                            "model": model,
                            "features": features,
                        }
                        continue

                model = XGBoostModel(**best_params)
                train(model, features, signal, symbol)
                save_model(model, features, signal, symbol)

                ensemble_key = "+".join(f.replace("Features", "") for f in features)
                app.state.models[ensemble_key] = {"model": model, "features": features}
                logger.info(f"Model retrained: {ensemble_key}")
            except Exception as e:
                logger.error(f"Failed to retrain {features}: {e}")
                notify(f"❌ **Retrain failed** ({features}): {e}")
                continue

        logger.info("Ensemble retrained")
    except Exception as e:
        logger.error(f"Model retraining failed: {e}")
        notify(f"❌ **Model retraining failed**: {e}")


def start_model_scheduler(app):
    model_scheduler.add_job(
        retrain_model,
        CronTrigger(hour=18, minute=0, timezone="US/Eastern"),
        args=[app],
        id="retrain",
        replace_existing=True,
    )
    model_scheduler.start()
