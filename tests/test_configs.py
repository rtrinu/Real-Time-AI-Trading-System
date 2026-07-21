import pytest
from training.configs import FEATURE_GROUPS, TABLE_MAP, CALENDAR_FEATURES
from db.market_models import ReturnsFeatures, RegimeFeatures
from db.news_models import Sentiment


class TestFeatureGroups:
    def test_returns_features_has_signal_5(self):
        assert "signal_5" in FEATURE_GROUPS["ReturnsFeatures"]

    def test_returns_features_has_key_columns(self):
        rf = FEATURE_GROUPS["ReturnsFeatures"]
        assert "log_ret_1" in rf
        assert "pct_ret_5" in rf
        assert "roll_cum_ret_20" in rf

    def test_sentiment_has_key_columns(self):
        s = FEATURE_GROUPS["Sentiment"]
        assert "sentiment_mean" in s
        assert "confidence_mean" in s
        assert "headline_count" in s
        assert "positive_count" in s
        assert "negative_count" in s

    def test_all_groups_are_lists(self):
        for group_name, cols in FEATURE_GROUPS.items():
            assert isinstance(cols, list), f"{group_name} should be a list"

    def test_no_duplicates_in_groups(self):
        for group_name, cols in FEATURE_GROUPS.items():
            assert len(cols) == len(set(cols)), f"{group_name} has duplicates"


class TestTableMap:
    def test_returns_features_maps_to_model(self):
        assert TABLE_MAP["ReturnsFeatures"] is ReturnsFeatures

    def test_sentiment_maps_to_model(self):
        assert TABLE_MAP["Sentiment"] is Sentiment

    def test_regime_maps_to_model(self):
        assert TABLE_MAP["RegimeFeatures"] is RegimeFeatures

    def test_all_values_are_sqlmodel_classes(self):
        for name, model in TABLE_MAP.items():
            assert hasattr(model, "__tablename__"), f"{name} should be a SQLModel table"


class TestCalendarFeatures:
    def test_is_list(self):
        assert isinstance(CALENDAR_FEATURES, list)

    def test_has_key_features(self):
        expected = [
            "day_of_week",
            "month",
            "quarter",
            "week_of_year",
            "is_month_end",
            "is_month_start",
            "is_friday",
            "is_monday",
        ]
        for col in expected:
            assert col in CALENDAR_FEATURES

    def test_no_duplicates(self):
        assert len(CALENDAR_FEATURES) == len(set(CALENDAR_FEATURES))
