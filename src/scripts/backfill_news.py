import time
import pandas as pd
from datetime import datetime, timedelta
from ingestion.news.finnhub import FinnhubNewsSource
from features.sentiment.finbert import FinBERTSentiment
from features.sentiment.sentiment import sentiment_features
from db.crud.general import bulk_insert
from db.news_models import FinnhubNews, Sentiment
from db.create_engine import get_session
from core.config import settings
from core.logger_config import logger


def chunk_dates(start_date: str, end_date: str, chunk_days: int = 30) -> list[tuple[str, str]]:
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    chunks = []
    current = start
    while current < end:
        chunk_end = min(current + timedelta(days=chunk_days), end)
        chunks.append((current.strftime("%Y-%m-%d"), chunk_end.strftime("%Y-%m-%d")))
        current = chunk_end + timedelta(days=1)
    return chunks


def fetch_chunk(finnhub_source: FinnhubNewsSource, symbol: str, from_date: str, to_date: str) -> list[dict]:
    raw = finnhub_source.fetch_raw_data(symbol, from_date, to_date)
    cleaned = [finnhub_source.normalise(r, symbol) for r in raw]
    for a in cleaned:
        a["source"] = "finnhub"
    deduplicated = finnhub_source.deduplicate_articles(cleaned)
    return deduplicated


def run_sentiment(articles: list[dict], model: FinBERTSentiment) -> list[dict]:
    if not articles:
        return []
    texts = [
        article["title"] + " " + (article["description"] or " ")
        for article in articles
    ]
    sentiments = model.predict(texts)
    enriched = []
    for article, sentiment in zip(articles, sentiments):
        article.update(model.to_score(sentiment))
        enriched.append(article)
    enriched = [a for a in enriched if a.get("title")]
    return enriched


def insert_to_db(finnhub_articles: list[dict], enriched: list[dict], session):
    if finnhub_articles:
        df = pd.DataFrame(finnhub_articles)
        df = df.drop(columns=["source"], errors="ignore")
        bulk_insert(df, FinnhubNews, session)
        logger.info(f"Inserted {len(finnhub_articles)} Finnhub articles")

    if enriched:
        sentiment_df = sentiment_features(enriched)
        bulk_insert(sentiment_df, Sentiment, session)
        logger.info(f"Inserted {len(sentiment_df)} sentiment feature rows")


def backfill(symbol: str = "AAPL", start_date: str = "2025-07-17", end_date: str = "2026-07-17", chunk_days: int = 30):
    logger.info(f"Starting backfill for {symbol} from {start_date} to {end_date}")
    session = get_session()
    model = FinBERTSentiment()
    finnhub_source = FinnhubNewsSource(settings.finnhub_api)

    chunks = chunk_dates(start_date, end_date, chunk_days)
    logger.info(f"Split into {len(chunks)} chunks")

    for i, (from_date, to_date) in enumerate(chunks):
        logger.info(f"Chunk {i + 1}/{len(chunks)}: {from_date} to {to_date}")

        raw_articles = fetch_chunk(finnhub_source, symbol, from_date, to_date)
        logger.info(f"Fetched {len(raw_articles)} articles")

        enriched = run_sentiment(raw_articles, model)
        logger.info(f"Enriched {len(enriched)} articles with sentiment")

        insert_to_db(raw_articles, enriched, session)

        if i < len(chunks) - 1:
            time.sleep(1)

    logger.info("Backfill complete")


if __name__ == "__main__":
    backfill()
