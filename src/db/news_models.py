from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Annotated, Optional


class NewsDataBase(SQLModel):
    symbol: str = Field(index=True)


class NewsAPI(NewsDataBase, table=True):
    __tablename__ = "NewsAPI"
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    description: str = ""
    content: str
    publishedAt: Optional[datetime]
    sentiment_score: Optional[float]
    confidence: Optional[float]
    label: Optional[str]


class Sentiment(NewsDataBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: Optional[datetime]
    sentiment_mean: Optional[float]
    confidence_mean: Optional[float]
    headline_count: Optional[int]
    positive_count: Optional[int]
    negative_count: Optional[int]
    neutral_count: Optional[int]
