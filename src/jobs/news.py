from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pipeline.news_data import run_news_pipeline
from core.logger_config import logger
from datetime import date, timedelta


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


def start_news_scheduler(app):
    news_scheduler.add_job(
        update_news_data,
        CronTrigger(hour=17, minute=0),
        id="update_news",
        replace_existing=True,
    )
    news_scheduler.start()
