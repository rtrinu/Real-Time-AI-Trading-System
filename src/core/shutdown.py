from core.logger_config import logger
from jobs.model import model_scheduler
from jobs.market import market_scheduler
from jobs.news import news_scheduler
from jobs.monitoring import monitoring_scheduler
from jobs.predict import predict_scheduler
from jobs.fill_poller import fill_poller_scheduler
from jobs.positions import position_scheduler

_shutting_down = False

SCHEDULERS = [
    ("market", market_scheduler),
    ("news", news_scheduler),
    ("model", model_scheduler),
    ("monitoring", monitoring_scheduler),
    ("predict", predict_scheduler),
    ("fill_poller", fill_poller_scheduler),
    ("position", position_scheduler),
]


def stop_all_schedulers():
    for name, sched in SCHEDULERS:
        try:
            if sched.running:
                sched.shutdown(wait=False)
                logger.info(f"{name} scheduler stopped")
        except Exception as e:
            logger.warning(f"{name} scheduler shutdown error: {e}")


def close_db():
    from db.create_engine import engine

    try:
        engine.dispose()
        logger.info("DB connections closed")
    except Exception as e:
        logger.warning(f"DB dispose error: {e}")


async def shutdown():
    global _shutting_down
    if _shutting_down:
        return
    _shutting_down = True

    logger.info("Shutting down — cancelling pending jobs")
    stop_all_schedulers()
    close_db()
