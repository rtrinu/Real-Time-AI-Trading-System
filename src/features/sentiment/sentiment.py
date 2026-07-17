import pandas as pd


def sentiment_features(news):
    news_df = pd.DataFrame(news)
    news_df["publishedAt"] = pd.to_datetime(news_df["publishedAt"])

    news_df["timestamp"] = news_df["publishedAt"].dt.floor("1h")

    features = (
        news_df.groupby(["symbol", "timestamp"])
        .agg(
            sentiment_mean=("sentiment_score", "mean"),
            confidence_mean=("confidence", "mean"),
            headline_count=("title", "count"),
            positive_count=("label", lambda x: (x == "positive").sum()),
            neutral_count=("label", lambda x: (x == "neutral").sum()),
            negative_count=("label", lambda x: (x == "negative").sum()),
        )
        .reset_index()
    )

    return features
