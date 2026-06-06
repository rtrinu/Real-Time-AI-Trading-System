import feedparser
from .base import BaseNewsSource
from datetime import datetime, timezone


class GoogleNewsStream(BaseNewsSource):
    def __init__(self):
        self.feeds = [
            ("US", "en"),
            ("GB", "en"),
            ("CA", "en"),
        ]

    def fetch(self, query: str):
        if not query:
            raise ValueError("Query is required")
        results = []

        for region, lang in self.feeds:
            url = (
                f"https://news.google.com/rss/search?"
                f"q={query}&hl={lang}&gl={region}&ceid={region}:{lang}"
            )
        feed = feedparser.parse(url)
        for entry in feed.entries:
            results.append(
                {
                    "title": entry.get("title"),
                    "url": entry.get("link"),
                    "published": entry.get("published"),
                    "source": f"google_news_{region}_{lang}",
                    "fetched_at": datetime.now(timezone=utc).isoformat(),
                }
            )
        return results
