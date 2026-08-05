from db.create_engine import check_db
from core.logger_config import setup_logging, logger
from alembic.config import Config
from alembic import command


async def db_startup():
    logger.info("Running startup checks")
    if not check_db():
        raise RuntimeError("Database Unavailable")
    logger.info("Database connection successfull")
    logger.info("Running migrations")
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    setup_logging()
