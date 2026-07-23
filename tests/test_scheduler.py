import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock, PropertyMock
from datetime import datetime, date
from jobs.model import retrain_model, start_model_scheduler, model_scheduler
from jobs.market import update_market_db, market_scheduler
from jobs.news import update_news_data, start_news_scheduler, news_scheduler


@pytest.fixture
def mock_app():
    app = MagicMock()
    app.state = MagicMock()
    return app


class TestRetrainModel:
    @patch("jobs.model.train")
    @patch("jobs.model.save_model")
    @patch("os.path.exists", return_value=False)
    def test_trains_when_no_saved_model(self, mock_exists, mock_save, mock_train, mock_app):
        retrain_model(mock_app)
        mock_train.assert_called_once()
        mock_save.assert_called_once()
        assert mock_app.state.model is not None

    @patch("jobs.model.train")
    @patch("jobs.model.save_model")
    @patch("os.path.getmtime", return_value=1.0)
    @patch("os.path.exists", return_value=True)
    def test_skips_when_model_trained_today(self, mock_exists, mock_mtime, mock_save, mock_train, mock_app):
        with patch("jobs.model.datetime") as mock_dt:
            mock_dt.fromtimestamp.return_value.date.return_value = date.today()
            mock_dt.today.return_value = date.today()
            retrain_model(mock_app)
        mock_train.assert_not_called()
        mock_save.assert_not_called()

    @patch("jobs.model.train")
    @patch("jobs.model.save_model")
    @patch("os.path.getmtime", return_value=1.0)
    @patch("os.path.exists", return_value=True)
    def test_trains_when_model_from_yesterday(self, mock_exists, mock_mtime, mock_save, mock_train, mock_app):
        yesterday = date(2020, 1, 1)
        with patch("jobs.model.datetime") as mock_dt:
            mock_dt.fromtimestamp.return_value.date.return_value = yesterday
            retrain_model(mock_app)
        mock_train.assert_called_once()
        mock_save.assert_called_once()

    @patch("jobs.model.train")
    @patch("jobs.model.save_model")
    @patch("os.path.exists", return_value=False)
    def test_updates_app_state(self, mock_exists, mock_save, mock_train, mock_app):
        retrain_model(mock_app)
        assert mock_app.state.model is not None


class TestStartModelScheduler:
    def test_adds_job_and_starts(self, mock_app):
        with patch.object(model_scheduler, "add_job") as mock_add, \
             patch.object(model_scheduler, "start") as mock_start:
            start_model_scheduler(mock_app)
            mock_add.assert_called_once()
            mock_start.assert_called_once()

    def test_job_has_correct_id(self, mock_app):
        with patch.object(model_scheduler, "add_job") as mock_add, \
             patch.object(model_scheduler, "start"):
            start_model_scheduler(mock_app)
            call_kwargs = mock_add.call_args
            assert call_kwargs[1]["id"] == "retrain" or call_kwargs.kwargs.get("id") == "retrain"


class TestUpdateMarketDb:
    def test_adds_job_and_starts(self, mock_app):
        with patch.object(market_scheduler, "add_job") as mock_add, \
             patch.object(market_scheduler, "start") as mock_start:
            update_market_db(mock_app)
            mock_add.assert_called_once()
            mock_start.assert_called_once()

    def test_job_has_correct_id(self, mock_app):
        with patch.object(market_scheduler, "add_job") as mock_add, \
             patch.object(market_scheduler, "start"):
            update_market_db(mock_app)
            call_kwargs = mock_add.call_args
            assert call_kwargs[1]["id"] == "update_market" or call_kwargs.kwargs.get("id") == "update_market"

    def test_job_runs_weekdays_only(self, mock_app):
        with patch.object(market_scheduler, "add_job") as mock_add, \
             patch.object(market_scheduler, "start"):
            update_market_db(mock_app)
            trigger = mock_add.call_args[0][1]
            day_field = next(f for f in trigger.fields if str(f) != "*")
            assert str(day_field) == "mon-fri"


class TestUpdateNewsData:
    @patch("jobs.news.run_news_pipeline")
    def test_calls_pipeline_with_today(self, mock_pipeline):
        update_news_data()
        mock_pipeline.assert_called_once()
        args = mock_pipeline.call_args
        assert args[0][0] == "AAPL"
        assert args[0][1] == date.today().strftime("%Y-%m-%d")
        assert args[0][2] == date.today().strftime("%Y-%m-%d")

    @patch("jobs.news.run_news_pipeline", side_effect=Exception("API error"))
    def test_handles_exception_gracefully(self, mock_pipeline):
        update_news_data()
        mock_pipeline.assert_called_once()


class TestStartNewsScheduler:
    def test_adds_job_and_starts(self, mock_app):
        with patch.object(news_scheduler, "add_job") as mock_add, \
             patch.object(news_scheduler, "start") as mock_start:
            start_news_scheduler(mock_app)
            mock_add.assert_called_once()
            mock_start.assert_called_once()

    def test_job_has_correct_id(self, mock_app):
        with patch.object(news_scheduler, "add_job") as mock_add, \
             patch.object(news_scheduler, "start"):
            start_news_scheduler(mock_app)
            call_kwargs = mock_add.call_args
            assert call_kwargs[1]["id"] == "update_news" or call_kwargs.kwargs.get("id") == "update_news"

    def test_job_runs_weekdays_only(self, mock_app):
        with patch.object(news_scheduler, "add_job") as mock_add, \
             patch.object(news_scheduler, "start"):
            start_news_scheduler(mock_app)
            trigger = mock_add.call_args[0][1]
            day_field = next(f for f in trigger.fields if str(f) != "*")
            assert str(day_field) == "mon-fri"
