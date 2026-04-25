import json
import redis.asyncio as redis
from core.market_data import MarketTick


class MarketStream:
    def __init__(self):
        self.redis = redis.Redis(host="localhost", port=6379)

    async def publish(self, tick: MarketTick):
        await self.redis.xadd(
            "market_stream",
            {
                "symbol": tick.symbol,
                "timestamp": tick.timestamp,
                "price": tick.price,
                "volume": tick.volume or 0,
                "source": tick.source or "",
            },
        )
