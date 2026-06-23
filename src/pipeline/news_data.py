from ingestion.news.newsapi import NewsAPISource
from core.config import settings


def run_newsapi_pipeline(symbol: str = "AAPL"):
    source = NewsAPISource(settings.newsapi_key)
    raw_data = source.fetch_raw_data(symbol)
    deduplicated = source.deduplicate_articles(raw_data)
