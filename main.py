import uvicorn
from fastapi import FastAPI
from core.logger_config import setup_logging, logger
from db.startup import db_startup
from api.routes.news import router as news_router
from api.routes.predict import router as predict_router
from jobs.model import start_model_scheduler, model_scheduler
from jobs.market import market_scheduler, update_market_db
from jobs.news import start_news_scheduler, news_scheduler

# temp for testing
from pipeline.market_data import run_yfinance_pipeline
from ml.xgboost import XGBoostModel
from training.trainer import train, predict, save_model, load_trained_model


app = FastAPI()


@app.on_event("startup")
async def startup():
    setup_logging()
    await db_startup()
    features = ["ReturnsFeatures", "Sentiment"]
    signal = "signal_5"
    symbol = "AAPL"
    logger.info("Loading saved model")
    update_market_db(app)
    start_news_scheduler(app)
    start_model_scheduler(app)
    model = load_trained_model(features, signal, symbol)
    if model is None:
        logger.info("No saved model found. Creating new model")
        model = XGBoostModel()
        train(model, features, signal, symbol)
        save_model(model, features, signal, symbol)
    app.state.model = model


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
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
