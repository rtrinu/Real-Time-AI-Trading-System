from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional


class PredictionBase(SQLModel):
    symbol: str = Field(index=True)
    timestamp: datetime = Field(index=True)


class Prediction(PredictionBase, table=True):
    __tablename__ = "signal_5_predictions"
    id: Optional[int] = Field(default=None, primary_key=True)
    predicted_signal: Optional[str] = None
    confidence: Optional[float] = None
    position_size: Optional[float] = None
    actual_signal: Optional[str] = None
    actual_return: Optional[float] = None
    is_correct: Optional[bool] = None
    evaluated_at: Optional[datetime] = None
