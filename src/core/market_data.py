from dataclasses import dataclass
from typing import Optional


@dataclass
class Tick:
    symbol: str
    timestamp: float
    price: float
    volume: float


@dataclass
class Candle:
    symbol: str
    timestamp: float
    open: float
    high: float
    low: float
    close: float
    volume: Optional[float] = None
    source: Optional[str] = None
