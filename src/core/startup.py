from datetime import date
from sqlmodel import select

from core.logger_config import setup_logging, logger
from core.health import (
    wait_for,
    check_db_reachable,
    check_redis_reachable,
    check_alpaca_reachable,
)
from db.startup import db_startup
from db.create_engine import get_session
from db.market_models import OHLCV
from db.news_models import NewsAPI
from broker.alpaca import create_client
from pipeline.market_data import run_yfinance_pipeline
from pipeline.news_data import run_news_pipeline
from jobs.model import start_model_scheduler, retrain_model
from jobs.market import update_market_db
from jobs.news import start_news_scheduler
from jobs.monitoring import start_monitoring_scheduler
from jobs.predict import start_predict_scheduler
from jobs.fill_poller import start_fill_poller
from jobs.positions import start_position_scheduler


async def startup(app):
    setup_logging()

    await wait_for("Database", check_db_reachable)
    await wait_for("Redis", check_redis_reachable)
    await wait_for("Alpaca API", check_alpaca_reachable)

    await db_startup()
    app.state.alpaca_client = create_client()
    app.state.models = {}

    if settings.dev_mode:
        logger.info("DEV_MODE=true — skipping backfills, model retrain, and schedulers")
        return

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

    retrain_model(app)

    start_news_scheduler(app)
    start_model_scheduler(app)
    update_market_db(app)
    start_monitoring_scheduler(app)
    start_predict_scheduler(app)
    start_fill_poller(app)
    start_position_scheduler(app)
