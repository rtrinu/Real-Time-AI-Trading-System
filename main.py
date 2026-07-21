import uvicorn
from fastapi import FastAPI
from core.logger_config import setup_logging, logger
from db.startup import db_startup
from api.routes.news import router as news_router

# temp for testing
from db.crud.news_models import bulk_insert_newsapi
from pipeline.news_data import run_news_pipeline
from pipeline.market_data import run_yfinance_pipeline
from training.data_loader import load_training_data
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
    model = load_trained_model(features, signal, symbol)
    if model is None:
        logger.info("No saved model found. Creating new model")
        model = XGBoostModel()
        train(model, features, signal, symbol)
        save_model(model, features, signal, symbol)
    result = predict(model, features, signal, symbol)
    logger.info(result)


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(news_router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
