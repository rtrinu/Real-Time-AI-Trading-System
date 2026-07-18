import uvicorn
from fastapi import FastAPI
from core.logger_config import setup_logging
from db.startup import db_startup

# temp for testing
from db.crud.news_models import bulk_insert_newsapi
from pipeline.news_data import run_newsapi_pipeline
from pipeline.market_data import run_yfinance_pipeline
from training.data_loader import load_training_data

app = FastAPI()


@app.on_event("startup")
async def startup():
    setup_logging()
    await db_startup()
    load_training_data("AAPL", ["ReturnsFeatures", "Sentiment"], "signal_5")


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
