from abc import ABC, abstractmethod
from typing import Callable
from core.market_data import MarketTick


class BaseMarketAdapter(ABC):
    def __init__(self):
        self.ws = None
        self._stream_task = None
        self._running = False

    @abstractmethod
    async def connect(self):
        pass

    @abstractmethod
    async def subscribe(self, symbols: list[str]):
        pass

    @abstractmethod
    async def stream(self, callback: Callable[[MarketTick], None]):
        pass

    @abstractmethod
    async def disconnect(self):
        pass
