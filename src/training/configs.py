# configs.py
from db.market_models import ReturnsFeatures, MomentumFeatures, RegimeFeatures
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
    "MomentumFeatures": [
        "rsi_7",
        "rsi_14",
        "rsi_21",
        "ema_dist_20",
        "ema_dist_10_50",
        "rsi_slope",
        "roc_10",
        "macd",
        "macd_signal",
        "macd_hist",
    ],
}

TABLE_MAP = {
    "ReturnsFeatures": ReturnsFeatures,
    "Sentiment": Sentiment,
    "MomentumFeatures": MomentumFeatures,
    "RegimeFeatures": RegimeFeatures,
}


CALENDAR_FEATURES = [
    "day_of_week",
    "month",
    "quarter",
    "week_of_year",
    "is_month_end",
    "is_month_start",
    "is_friday",
    "is_monday",
]
