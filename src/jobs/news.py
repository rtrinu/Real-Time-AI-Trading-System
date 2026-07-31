from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pipeline.news_data import run_news_pipeline
from pipeline.news_data import fetch_finnhub_only
from core.logger_config import logger
from datetime import date


news_scheduler = AsyncIOScheduler()


def update_news_data():
    symbol = "AAPL"
    today = date.today()
    from_date = today.strftime("%Y-%m-%d")
    to_date = today.strftime("%Y-%m-%d")

    try:
        run_news_pipeline(symbol, from_date, to_date)
        logger.info(f"News data updated for {symbol} on {today}")
    except Exception as e:
        logger.warning(f"News update failed: {e}")


def update_news_frequent():
    symbol = "AAPL"
    try:
        fetch_finnhub_only(symbol)
        logger.info(f"Frequent news update completed for {symbol}")
    except Exception as e:
        logger.warning(f"Frequent news update failed: {e}")


def start_news_scheduler(app):
    news_scheduler.add_job(
        update_news_data,
        CronTrigger(hour=17, minute=0, timezone="US/Eastern"),
        id="update_news",
        replace_existing=True,
    )
    news_scheduler.add_job(
        update_news_frequent,
        CronTrigger(day_of_week="mon-fri", minute="*/15", timezone="US/Eastern"),
        id="update_news_frequent",
        replace_existing=True,
    )
    news_scheduler.start()
