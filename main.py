import uvicorn
from fastapi import FastAPI
from datetime import date
from sqlmodel import select

from core.logger_config import setup_logging, logger
from db.startup import db_startup
from db.create_engine import get_session
from db.market_models import OHLCV
from db.news_models import NewsAPI

from broker.alpaca import create_client

from pipeline.market_data import run_yfinance_pipeline
from pipeline.news_data import run_news_pipeline

from jobs.model import start_model_scheduler, model_scheduler
from jobs.market import market_scheduler, update_market_db
from jobs.news import start_news_scheduler, news_scheduler
from jobs.monitoring import start_monitoring_scheduler, monitoring_scheduler
from jobs.predict import start_predict_scheduler, predict_scheduler
from jobs.fill_poller import start_fill_poller, fill_poller_scheduler
from jobs.positions import start_position_scheduler, position_scheduler

from api.routes.news import router as news_router
from api.routes.predict import router as predict_router
from api.routes.backtest import router as backtest_router
from api.routes.monitoring import router as monitoring_router
from api.routes.trade import router as trade_router
from api.routes.portfolio import router as portfolio_router
from api.routes.orders import router as orders_router

app = FastAPI()


@app.on_event("startup")
async def startup():
    setup_logging()
    await db_startup()
    app.state.alpaca_client = create_client()
    app.state.models = {}

    session = get_session()
    ohlcv_empty = session.exec(select(OHLCV).limit(1)).first() is None
    news_empty = session.exec(select(NewsAPI).limit(1)).first() is None
    session.close()

    if ohlcv_empty:
        logger.info("Empty DB — backfilling 2 years of market data")
        try:
            run_yfinance_pipeline()
        except Exception as e:
            logger.warning(f"Market data seed failed: {e}")

    if news_empty:
        logger.info("Empty DB — backfilling news + sentiment")
        try:
            run_news_pipeline(symbol="AAPL", to_date=str(date.today()))
        except Exception as e:
            logger.warning(f"News seed failed: {e}")

    start_news_scheduler(app)
    start_model_scheduler(app)
    update_market_db(app)
    start_monitoring_scheduler(app)
    start_predict_scheduler(app)
    start_fill_poller(app)
    start_position_scheduler(app)


@app.on_event("shutdown")
async def shutdown():
    market_scheduler.shutdown()
    news_scheduler.shutdown()
    model_scheduler.shutdown()
    monitoring_scheduler.shutdown()
    predict_scheduler.shutdown()
    fill_poller_scheduler.shutdown()
    position_scheduler.shutdown()


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(news_router)
app.include_router(predict_router)
app.include_router(backtest_router)
app.include_router(monitoring_router)
app.include_router(trade_router)
app.include_router(portfolio_router)
app.include_router(orders_router)
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000)
