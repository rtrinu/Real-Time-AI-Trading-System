import pytest
from unittest.mock import patch, MagicMock
from jobs.fill_poller import poll_order_fills, start_fill_poller, fill_poller_scheduler


@pytest.fixture
def mock_app():
    app = MagicMock()
    app.state = MagicMock()
    app.state.alpaca_client = MagicMock()
    return app


@pytest.fixture
def mock_session():
    session = MagicMock()
    return session


class TestPollOrderFills:
    def test_returns_when_no_alpaca_client(self, mock_app):
        mock_app.state.alpaca_client = None
        with patch("jobs.fill_poller.get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session
            poll_order_fills(mock_app)
        mock_session.close.assert_called_once()

    def test_returns_when_no_unfilled_orders(self, mock_app, mock_session):
        mock_exec = MagicMock()
        mock_exec.all.return_value = []
        mock_session.exec.return_value = mock_exec
        with patch("jobs.fill_poller.get_session", return_value=mock_session):
            poll_order_fills(mock_app)
        mock_session.close.assert_called_once()

    def test_updates_audit_on_filled_order(self, mock_app, mock_session):
        mock_audit = MagicMock()
        mock_audit.order_id = "ord_123"
        mock_audit.order_filled_qty = None
        mock_order = MagicMock()
        mock_order.status = "filled"
        mock_order.filled_qty = "100"
        mock_order.filled_avg_price = "150.50"
        mock_session.exec.return_value.all.return_value = [mock_audit]
        mock_app.state.alpaca_client.get_order_by_id.return_value = mock_order
        with patch("jobs.fill_poller.get_session", return_value=mock_session):
            poll_order_fills(mock_app)
        assert mock_audit.order_filled_qty == 100.0
        assert mock_audit.order_filled_avg_price == 150.50
        assert mock_audit.order_status == "filled"
        mock_session.add.assert_called_once_with(mock_audit)
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

    def test_updates_audit_on_cancelled_order(self, mock_app, mock_session):
        mock_audit = MagicMock()
        mock_audit.order_id = "ord_456"
        mock_audit.order_filled_qty = None
        mock_order = MagicMock()
        mock_order.status = "canceled"
        mock_session.exec.return_value.all.return_value = [mock_audit]
        mock_app.state.alpaca_client.get_order_by_id.return_value = mock_order
        with patch("jobs.fill_poller.get_session", return_value=mock_session):
            poll_order_fills(mock_app)
        assert mock_audit.order_status == "canceled"
        mock_session.add.assert_called_once_with(mock_audit)

    def test_updates_audit_on_expired_order(self, mock_app, mock_session):
        mock_audit = MagicMock()
        mock_audit.order_id = "ord_789"
        mock_audit.order_filled_qty = None
        mock_order = MagicMock()
        mock_order.status = "expired"
        mock_session.exec.return_value.all.return_value = [mock_audit]
        mock_app.state.alpaca_client.get_order_by_id.return_value = mock_order
        with patch("jobs.fill_poller.get_session", return_value=mock_session):
            poll_order_fills(mock_app)
        assert mock_audit.order_status == "expired"

    def test_updates_audit_on_rejected_order(self, mock_app, mock_session):
        mock_audit = MagicMock()
        mock_audit.order_id = "ord_000"
        mock_audit.order_filled_qty = None
        mock_order = MagicMock()
        mock_order.status = "rejected"
        mock_session.exec.return_value.all.return_value = [mock_audit]
        mock_app.state.alpaca_client.get_order_by_id.return_value = mock_order
        with patch("jobs.fill_poller.get_session", return_value=mock_session):
            poll_order_fills(mock_app)
        assert mock_audit.order_status == "rejected"

    def test_skips_unfinished_status(self, mock_app, mock_session):
        mock_audit = MagicMock()
        mock_audit.order_id = "ord_111"
        mock_audit.order_filled_qty = None
        mock_order = MagicMock()
        mock_order.status = "new"
        mock_session.exec.return_value.all.return_value = [mock_audit]
        mock_app.state.alpaca_client.get_order_by_id.return_value = mock_order
        with patch("jobs.fill_poller.get_session", return_value=mock_session):
            poll_order_fills(mock_app)
        mock_session.add.assert_not_called()

    def test_continues_on_per_order_error(self, mock_app, mock_session):
        mock_audit_ok = MagicMock()
        mock_audit_ok.order_id = "ord_ok"
        mock_audit_ok.order_filled_qty = None
        mock_audit_fail = MagicMock()
        mock_audit_fail.order_id = "ord_fail"
        mock_audit_fail.order_filled_qty = None
        mock_session.exec.return_value.all.return_value = [mock_audit_fail, mock_audit_ok]
        mock_app.state.alpaca_client.get_order_by_id.side_effect = [
            Exception("API error"),
            MagicMock(status="filled", filled_qty="50", filled_avg_price="200"),
        ]
        with patch("jobs.fill_poller.get_session", return_value=mock_session):
            poll_order_fills(mock_app)
        assert mock_audit_ok.order_filled_qty == 50.0
        assert mock_audit_fail.order_filled_qty is None
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()


class TestStartFillPoller:
    def test_adds_job_and_starts(self, mock_app):
        with patch.object(fill_poller_scheduler, "add_job") as mock_add, \
             patch.object(fill_poller_scheduler, "start") as mock_start:
            start_fill_poller(mock_app)
            mock_add.assert_called_once()
            mock_start.assert_called_once()

    def test_job_has_correct_id(self, mock_app):
        with patch.object(fill_poller_scheduler, "add_job") as mock_add, \
             patch.object(fill_poller_scheduler, "start"):
            start_fill_poller(mock_app)
            kwargs = mock_add.call_args.kwargs
            assert kwargs["id"] == "fill_poller"
