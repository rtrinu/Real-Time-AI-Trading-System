from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional


class TradeOrderBase(SQLModel):
    symbol: str = Field(index=True)
    timestamp: datetime = Field(index=True)


class TradeAudit(TradeOrderBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    source: str

    signal: str
    confidence: float
    position_size: float

    risk_check_passed: bool
    risk_check_reason: str
    validation_passed: bool
    validation_reason: str

    executed: bool
    order_id: Optional[str] = None
    order_side: Optional[str] = None
    order_qty: Optional[int] = None
    order_filled_qty: Optional[float] = None
    order_filled_avg_price: Optional[float] = None
    order_status: Optional[str] = None

    error_message: Optional[str] = None

    prediction_id: Optional[int] = None
