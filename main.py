import uvicorn
import json
import os
from fastapi import FastAPI
from core.logger_config import setup_logging, logger
from db.startup import db_startup
from api.routes.news import router as news_router
from api.routes.predict import router as predict_router
from api.routes.backtest import router as backtest_router
from jobs.model import start_model_scheduler, model_scheduler
from jobs.market import market_scheduler, update_market_db
from jobs.news import start_news_scheduler, news_scheduler

from ml.xgboost import XGBoostModel
from training.trainer import train, save_model, load_trained_model
from pipeline.market_data import update_market_data
from backtesting.engine import walk_forward

app = FastAPI()

MODELS = [
    ["MomentumFeatures", "Sentiment"],
    ["MomentumFeatures", "Sentiment", "MeanReversionFeatures"],
    ["MomentumFeatures", "MeanReversionFeatures"],
]


def load_best_params():
    path = os.path.join("models", "best_params.json")
    try:
        with open(path) as f:
            data = json.load(f)
        logger.info(f"Loaded best params: {data['params']}")
        return data["params"]
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        return {}


@app.on_event("startup")
async def startup():
    setup_logging()
    await db_startup()

    signal = "signal_5"
    symbol = "AAPL"

    logger.info("Updating market data")
    update_market_data()

    start_news_scheduler(app)
    start_model_scheduler(app)
    update_market_db(app)

    best_params = load_best_params()

    app.state.models = {}
    for features in MODELS:
        key = "+".join(f.replace("Features", "") for f in features)
        model = load_trained_model(features, signal, symbol)
        if model is None:
            logger.info(f"Training new model: {key}")
            model = XGBoostModel(**best_params)
            train(model, features, signal, symbol)
            save_model(model, features, signal, symbol)
        else:
            logger.info(f"Loaded model: {key}")
        app.state.models[key] = {"model": model, "features": features}

    primary = app.state.models["Momentum+Sentiment"]
    results = walk_forward(
        features=primary["features"],
        signal=signal,
        symbol=symbol,
        _model_params=best_params,
    )
    if results:
        print(results["metrics"])


@app.on_event("shutdown")
async def shutdown():
    market_scheduler.shutdown()
    news_scheduler.shutdown()
    model_scheduler.shutdown()


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(news_router)
app.include_router(predict_router)
app.include_router(backtest_router)
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
