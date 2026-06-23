from ingestion.news.newsapi import NewsAPISource
from features.sentiment.finbert import FinBERTSentiment
from core.config import settings
from core.logger_config import logger


def run_newsapi_pipeline(symbol: str = "AAPL"):
    logger.info("Starting NewsAPI Pipeline")
    source = NewsAPISource(settings.newsapi_key)
    model = FinBERTSentiment()
    raw_data = source.fetch_raw_data(symbol)
    deduplicated = source.deduplicate_articles(raw_data)
    texts = [
        article["title"] + " " + (article["description"] or " ")
        for article in deduplicated
    ]
    sentiments = model.predict(texts)
