from core.config import settings
import finnhub
import pandas as pd
from datetime import datetime, timezone
import hashlib
from core.logger_config import logger


class FinnhubNewsSource:
    def __init__(self, api_key):
        self.api_key = api_key
        self.finnhub_client = finnhub.Client(api_key=self.api_key)

    def fetch_raw_data(self, symbol: str, from_date: str, to_date: str) -> list[dict]:
        logger.info("Trying FinnHub endpoint")
        news = self.finnhub_client.company_news(symbol, from_date, to_date)
        return news

    def normalise(self, record: dict, symbol: str):
        return {
            "symbol": symbol,
            "title": record.get("headline"),
            "description": record.get("summary"),
            "publishedAt": datetime.fromtimestamp(
                record.get("datetime"), tz=timezone.utc
            ),
        }

    def article_hash(self, title: str):
        return hashlib.md5(title.lower().strip().encode()).hexdigest()

    def deduplicate_articles(self, raw_data: list[dict]):
        seen = set()
        filtered = []
        for data in raw_data:
            h = self.article_hash(data["title"])
            if h not in seen:
                seen.add(h)
                filtered.append(data)
        return filtered

    def clean_articles(self, a: dict):
        if not a.get("description"):
            a["description"] = a.get("summary", "")[:200]
        if not a["description"]:
            return None
        return a
