import requests
from core.config import settings
from newsapi import NewsApiClient
from datetime import datetime, timedelta, timezone
from core.logger_config import logger


class NewsAPISource:
    def __init__(self, api_key):
        self.api_key = api_key
        self.newsapi = NewsApiClient(api_key=settings.newsapi_key)

    def fetch_raw_data(self, query):
        if not query:
            raise ValueError("No Query Input")
        if not self.newsapi:
            raise RuntimeError("No Newsapi Client Instance")
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=25)

        try:
            logger.info("Trying NewsAPI endpoint")
            response = self.newsapi.get_everything(
                q=query,
                from_param=start_date,
                to=end_date,
                language="en",
                sort_by="publishedAt",
                page_size=1,
            )
        except Exception as e:
            raise RuntimeError(f"NewsAPI request failed: {e}")

        if response.get("status") != "ok":
            raise RuntimeError(f"API error: {response}")
        articles = response.get("articles")
        return articles

    def normalise(self, record: dict, symbol: str):
        return {
            "symbol": symbol,
            "title": record.get("title"),
            "description": record.get("description"),
            "publishedAt": record.get("publishedAt"),
            "content": record.get("content"),
        }
