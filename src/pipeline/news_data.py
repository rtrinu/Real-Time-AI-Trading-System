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
from datetime import datetime, timedelta, timezone
from sqlmodel import select, func


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


def fetch_finnhub_only(symbol: str = "AAPL"):
    logger.info(f"Starting frequent Finnhub news fetch for {symbol}")
    session = get_session()

    result = session.exec(
        select(func.max(FinnhubNews.publishedAt))
    ).first()
    if result:
        last_fetched = result
        logger.info(f"Last fetched article: {last_fetched}")
    else:
        last_fetched = datetime.now(timezone.utc) - timedelta(days=1)
        logger.info("No previous articles found, fetching last 24 hours")

    from_date = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    to_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    finnhub_source = FinnhubNewsSource(settings.finnhub_api)
    finnhub_raw = finnhub_source.fetch_raw_data(symbol, from_date, to_date)

    if not finnhub_raw:
        logger.info("No new articles from Finnhub")
        return

    finnhub_cleaned = [finnhub_source.normalise(r, symbol) for r in finnhub_raw]

    existing_titles = session.exec(
        select(FinnhubNews.title)
    ).all()
    existing_hashes = set()
    for title in existing_titles:
        h = finnhub_source.article_hash(title)
        existing_hashes.add(h)

    unique_articles = []
    for article in finnhub_cleaned:
        h = finnhub_source.article_hash(article["title"])
        if h not in existing_hashes:
            if article["publishedAt"] > last_fetched:
                unique_articles.append(article)
                existing_hashes.add(h)

    if not unique_articles:
        logger.info("No new unique articles to insert")
        return

    logger.info(f"Found {len(unique_articles)} new unique articles")

    model = FinBERTSentiment()
    texts = [
        article["title"] + " " + (article["description"] or " ")
        for article in unique_articles
    ]
    sentiments = model.predict(texts)
    for article, sentiment in zip(unique_articles, sentiments):
        article.update(model.to_score(sentiment))

    enriched = [finnhub_source.clean_article(a) for a in unique_articles if a]
    enriched = [a for a in enriched if a is not None]

    bulk_insert(pd.DataFrame(enriched), FinnhubNews, session)
    logger.info(f"Inserted {len(enriched)} new articles for {symbol}")

    sentiment_features_df = sentiment_features(enriched)
    bulk_insert(sentiment_features_df, Sentiment, session)
    logger.info("Sentiment features updated")
