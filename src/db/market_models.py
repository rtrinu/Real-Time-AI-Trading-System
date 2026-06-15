from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional


class MarketDataBase(SQLModel):
    symbol: str = Field(index=True)
    timestamp: datetime = Field(index=True)


class OHLCV(MarketDataBase, table=True):
    __tablename__ = "OHLCV"
    id: Optional[int] = Field(default=None, primary_key=True)
    open: float
    high: float
    low: float
    close: float
    volume: Optional[float] = None
    source: Optional[str] = None
