from ingestion.news.newsapi import NewsAPISource
from features.sentiment.finbert import FinBERTSentiment
from core.config import settings
from core.logger_config import logger
from db.crud.news_models import bulk_insert_newsapi
from db.crud.general import bulk_insert
from features.sentiment.sentiment import sentiment_features
from db.news_models import Sentiment
from db.create_engine import get_session


def run_newsapi_pipeline(symbol: str = "AAPL"):
    logger.info("Starting NewsAPI Pipeline")
    session = get_session()
    enriched = []
    source = NewsAPISource(settings.newsapi_key)
    model = FinBERTSentiment()
    raw_data = source.fetch_raw_data(symbol)
    cleaned = [source.normalise(r, symbol) for r in raw_data]
    deduplicated = source.deduplicate_articles(cleaned)
    texts = [
        article["title"] + " " + (article["description"] or " ")
        for article in deduplicated
    ]
    sentiments = model.predict(texts)
    for article, sentiment in zip(deduplicated, sentiments):
        article.update(model.to_score(sentiment))
        enriched.append(article)
    enriched = [source.clean_article(a) for a in enriched]
    enriched = [a for a in enriched if a is not None]
    logger.info(type(enriched))
    bulk_insert_newsapi(enriched)
    sentiment_features_df = sentiment_features(enriched)
    logger.info(sentiment_features_df.head())
    bulk_insert(sentiment_features_df, Sentiment, session)
