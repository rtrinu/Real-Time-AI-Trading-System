from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Annotated, Optional


class NewsDataBase(SQLModel):
    symbol: str = Field(index=True)
    timestamp: datetime = Field(index=True)


class NewsAPI(NewsDataBase, table=True):
    __tablename__ = "NewsAPI"
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    sentiment_score: Optional[float]
