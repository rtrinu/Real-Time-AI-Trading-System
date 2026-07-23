from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pipeline.market_data import update_market_data

market_scheduler = AsyncIOScheduler()


def update_market_db(app):
    market_scheduler.add_job(
        update_market_data,
        CronTrigger(day_of_week="mon-fri", hour=16, minute=39),
        id="update_market",
        replace_existing=True,
    )
    market_scheduler.start()
