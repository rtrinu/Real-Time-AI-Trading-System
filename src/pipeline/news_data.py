from ingestion.news.newsapi import NewsAPISource
from ingestion.news.finnhub import FinnhubNewsSource
from features.sentiment.finbert import FinBERTSentiment
from core.config import settings
from core.logger_config import logger
from db.crud.news_models import bulk_insert_newsapi
from db.crud.general import bulk_insert
from features.sentiment.sentiment import sentiment_features
from db.news_models import Sentiment, FinnhubNews
from db.create_engine import get_session
import pandas as pd


def run_news_pipeline(
    symbol: str = "AAPL", from_date: str = "2025-09-24", to_date: str = "2026-06-15"
):
    logger.info("Starting News Pipeline")
    session = get_session()
    enriched = []
    model = FinBERTSentiment()

    newsapi_source = NewsAPISource(settings.newsapi_key)
    finnhub_source = FinnhubNewsSource(settings.finnhub_api)

    newsapi_raw = newsapi_source.fetch_raw_data(symbol)
    finnhub_raw = finnhub_source.fetch_raw_data(symbol, from_date, to_date)

    newsapi_cleaned = [newsapi_source.normalise(r, symbol) for r in newsapi_raw]
    for a in newsapi_cleaned:
        a["source"] = "newsapi"

    finnhub_cleaned = [finnhub_source.normalise(r, symbol) for r in finnhub_raw]
    for a in finnhub_cleaned:
        a["source"] = "finnhub"

    all_articles = newsapi_cleaned + finnhub_cleaned
    deduplicated = newsapi_source.deduplicate_articles(all_articles)

    texts = [
        article["title"] + " " + (article["description"] or " ")
        for article in deduplicated
    ]
    sentiments = model.predict(texts)
    for article, sentiment in zip(deduplicated, sentiments):
        article.update(model.to_score(sentiment))
        enriched.append(article)

    enriched = [newsapi_source.clean_article(a) for a in enriched]
    enriched = [a for a in enriched if a is not None]

    newsapi_articles = [a for a in enriched if a["source"] == "newsapi"]
    finnhub_articles = [a for a in enriched if a["source"] == "finnhub"]

    for a in newsapi_articles:
        a.pop("source", None)
    for a in finnhub_articles:
        a.pop("source", None)

    bulk_insert_newsapi(newsapi_articles)
    bulk_insert(pd.DataFrame(finnhub_articles), FinnhubNews, session)
    sentiment_features_df = sentiment_features(enriched)
    bulk_insert(sentiment_features_df, Sentiment, session)
