import uvicorn
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
from backtesting.engine import VectorisedBacktest

app = FastAPI()

MODELS = [
    ["MomentumFeatures", "Sentiment"],
    ["MomentumFeatures", "Sentiment", "MeanReversionFeatures"],
    ["MomentumFeatures", "MeanReversionFeatures"],
]


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

    app.state.models = {}
    for features in MODELS:
        key = "+".join(f.replace("Features", "") for f in features)
        model = load_trained_model(features, signal, symbol)
        if model is None:
            logger.info(f"Training new model: {key}")
            model = XGBoostModel()
            train(model, features, signal, symbol)
            save_model(model, features, signal, symbol)
        else:
            logger.info(f"Loaded model: {key}")
        app.state.models[key] = {"model": model, "features": features}

    primary = app.state.models["Momentum+Sentiment"]
    bt = VectorisedBacktest(
        model=primary["model"],
        symbol=symbol,
        features=primary["features"],
        signal=signal,
        save_charts=True,
    )
    results = bt.run()
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
