import asyncio
import time

from core.config import settings
from core.logger_config import logger
from db.create_engine import check_db
from broker.alpaca import create_client


async def wait_for(
    description: str,
    check_fn,
    timeout: int = 90,
    interval: int = 3,
):
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        try:
            result = await check_fn()
            if result:
                logger.info(f"{description} — ready")
                return
        except Exception as e:
            logger.warning(f"{description} — not ready: {e}")
        await asyncio.sleep(interval)
    raise RuntimeError(f"{description} — timed out after {timeout}s")


async def check_db_reachable():
    return await asyncio.to_thread(check_db)


async def check_redis_reachable():
    import redis.asyncio as aioredis

    client = aioredis.from_url(settings.redis_url)
    try:
        await client.ping()
        return True
    finally:
        await client.aclose()


async def check_alpaca_reachable():
    client = create_client()
    account = client.get_account()
    return account.status == "ACTIVE"
