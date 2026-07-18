# configs.py
from db.market_models import ReturnsFeatures
from db.news_models import Sentiment

FEATURE_GROUPS = {
    "ReturnsFeatures": [
        "log_ret_1",
        "log_ret_5",
        "log_ret_10",
        "log_ret_20",
        "pct_ret_1",
        "pct_ret_5",
        "pct_ret_10",
        "pct_ret_20",
        "roll_cum_ret_20",
        "roll_mean_ret_20",
        "roll_ret_z_20",
        "signal_5",
    ],
    "Sentiment": [
        "sentiment_mean",
        "confidence_mean",
        "headline_count",
        "positive_count",
        "negative_count",
    ],
}

TABLE_MAP = {
    "ReturnsFeatures": ReturnsFeatures,
    "Sentiment": Sentiment,
}
