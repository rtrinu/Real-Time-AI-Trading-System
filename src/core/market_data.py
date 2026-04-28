from dataclasses import dataclass
from typing import Optional


@dataclass
class MarketTick:
    symbol: str
    timestampe: float
    price: float
    volume: Optional[float]
    bid: Optional[float] = None
    ask: Optional[float] = None
    source: Optional[str] = None
