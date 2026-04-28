import asyncio
from ingestion.adapters.finnhub import FinnhubAdapter
from streaming.market_stream import MarketStream
from core.config import settings

stream = MarketStream()


async def handler(tick):
    await stream.publish(tick)


async def main():
    adapter = FinnhubAdapter(api_key=settings.finnhub_api)
    await adapter.connect()
    await adapter.subscribe(["AAPL", "TSLA"])
    adapter.start_stream(handler)


asyncio.run(main())
