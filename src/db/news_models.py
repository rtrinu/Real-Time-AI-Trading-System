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
