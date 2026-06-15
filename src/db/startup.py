from db.create_engine import check_db
from core.logger_config import logger


async def db_startup():
    logger.info("Running startup checks")
    if not check_db():
        raise RuntimeError("Database Unavailable")
    logger.info("Database connection successfull")
