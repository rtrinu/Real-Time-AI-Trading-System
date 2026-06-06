from .base import BaseMarketAdapter
import websockets
import asyncio
import json


class FinnhubAdapter(BaseMarketAdapter):
    def __init__(self, api_key):
        self.api_key = api_key
        self.ws = None
        self._running = False
        self._stream_task = None

    async def connect(self):
        if not self.api_key:
            raise ValueError("Missing API Key")
        url = f"wss://ws.finnhub.io?token={self.api_key}"
        try:
            self.ws = await websockets.connect(url)
            print("Connection Successful")
        except Exception as e:
            print("Failed to connect: {e}")

    async def subscribe(self, symbols):
        if not self.ws:
            raise RuntimeError("Not Connected")
        for s in symbols:
            await self.ws.send(json.dumps({"type": "subscribe", "symbol": s}))
            print(f"Subscribed: {s}")

    def start_stream(self, callback):
        if not self.ws:
            raise RuntimeError("Not Connected")
        self._stream_task = asyncio.create_task(self.stream(callback))
        print("Stream Started")

    async def stream(self, callback):
        self._running = True

        try:
            async for msg in self.ws:

                if not self._running:
                    break

                data = json.loads(msg)
                print(data)

                if data.get("type") != "trade":
                    continue

                if not self._ready.is_set():
                    self._ready.set()

                for t in data.get("data", []):
                    tick = MarketTick(
                        symbol=t["s"],
                        timestamp=t["t"] / 1000,
                        price=t["p"],
                        volume=t.get("v"),
                        source="finnhub",
                    )

                    await callback(tick)

        except asyncio.CancelledError:
            pass

        except Exception as e:
            print(f"[STREAM ERROR] {e}")

    async def disconnect(self):
        pass
