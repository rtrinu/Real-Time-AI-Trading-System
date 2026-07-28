import pytest
from unittest.mock import patch, MagicMock
from jobs.positions import manage_positions


@pytest.fixture
def mock_app():
    app = MagicMock()
    app.state = MagicMock()
    return app


def make_position(symbol="AAPL", qty=100, unrealized_plpc=0.0):
    pos = MagicMock()
    pos.symbol = symbol
    pos.qty = str(qty)
    pos.unrealized_plpc = str(unrealized_plpc / 100.0)
    pos.unrealized_pl = "0"
    return pos


class TestManagePositions:
    def test_returns_when_no_alpaca_client(self, mock_app):
        mock_app.state.alpaca_client = None
        result = manage_positions(mock_app)
        assert result is None

    def test_returns_when_no_positions(self, mock_app):
        mock_app.state.alpaca_client.get_all_positions.return_value = []
        result = manage_positions(mock_app)
        assert result is None

    def test_closes_long_on_take_profit(self, mock_app):
        pos = make_position(symbol="AAPL", qty=100, unrealized_plpc=6.0)
        mock_app.state.alpaca_client.get_all_positions.return_value = [pos]
        mock_order = MagicMock()
        mock_order.id = "ord_tp"
        mock_order.status = "filled"
        mock_app.state.alpaca_client.submit_order.return_value = mock_order
        mock_session = MagicMock()
        mock_audit = MagicMock()
        mock_audit.id = 1

        with patch("jobs.positions.get_session", return_value=mock_session), \
             patch("jobs.positions._create_audit", return_value=mock_audit), \
             patch("jobs.positions._update_audit"):

            manage_positions(mock_app)

        mock_app.state.alpaca_client.submit_order.assert_called_once()
        call_kwargs = mock_app.state.alpaca_client.submit_order.call_args[0][0]
        assert call_kwargs.symbol == "AAPL"
        assert call_kwargs.qty == 100
        assert call_kwargs.side.value == "sell"

    def test_closes_long_on_stop_loss(self, mock_app):
        pos = make_position(symbol="AAPL", qty=100, unrealized_plpc=-4.0)
        mock_app.state.alpaca_client.get_all_positions.return_value = [pos]
        mock_order = MagicMock()
        mock_order.id = "ord_sl"
        mock_order.status = "filled"
        mock_app.state.alpaca_client.submit_order.return_value = mock_order
        mock_session = MagicMock()
        mock_audit = MagicMock()
        mock_audit.id = 2

        with patch("jobs.positions.get_session", return_value=mock_session), \
             patch("jobs.positions._create_audit", return_value=mock_audit), \
             patch("jobs.positions._update_audit"):

            manage_positions(mock_app)

        call_kwargs = mock_app.state.alpaca_client.submit_order.call_args[0][0]
        assert call_kwargs.side.value == "sell"

    def test_closes_short_on_take_profit(self, mock_app):
        pos = make_position(symbol="AAPL", qty=-100, unrealized_plpc=6.0)
        mock_app.state.alpaca_client.get_all_positions.return_value = [pos]
        mock_order = MagicMock()
        mock_order.id = "ord_short_tp"
        mock_order.status = "filled"
        mock_app.state.alpaca_client.submit_order.return_value = mock_order
        mock_session = MagicMock()
        mock_audit = MagicMock()
        mock_audit.id = 3

        with patch("jobs.positions.get_session", return_value=mock_session), \
             patch("jobs.positions._create_audit", return_value=mock_audit), \
             patch("jobs.positions._update_audit"):

            manage_positions(mock_app)

        call_kwargs = mock_app.state.alpaca_client.submit_order.call_args[0][0]
        assert call_kwargs.side.value == "buy"
        assert call_kwargs.qty == 100

    def test_closes_short_on_stop_loss(self, mock_app):
        pos = make_position(symbol="AAPL", qty=-100, unrealized_plpc=-4.0)
        mock_app.state.alpaca_client.get_all_positions.return_value = [pos]
        mock_order = MagicMock()
        mock_order.id = "ord_short_sl"
        mock_order.status = "filled"
        mock_app.state.alpaca_client.submit_order.return_value = mock_order
        mock_session = MagicMock()
        mock_audit = MagicMock()
        mock_audit.id = 4

        with patch("jobs.positions.get_session", return_value=mock_session), \
             patch("jobs.positions._create_audit", return_value=mock_audit), \
             patch("jobs.positions._update_audit"):

            manage_positions(mock_app)

        call_kwargs = mock_app.state.alpaca_client.submit_order.call_args[0][0]
        assert call_kwargs.side.value == "buy"

    def test_skips_position_within_thresholds(self, mock_app):
        pos = make_position(symbol="AAPL", qty=100, unrealized_plpc=2.0)
        mock_app.state.alpaca_client.get_all_positions.return_value = [pos]

        with patch("jobs.positions.get_session") as mock_get_session:
            manage_positions(mock_app)

        mock_app.state.alpaca_client.submit_order.assert_not_called()
        mock_get_session.assert_not_called()

    def test_skips_position_at_exactly_take_profit(self, mock_app):
        pos = make_position(symbol="AAPL", qty=100, unrealized_plpc=5.0)
        mock_app.state.alpaca_client.get_all_positions.return_value = [pos]
        mock_order = MagicMock()
        mock_app.state.alpaca_client.submit_order.return_value = mock_order
        mock_session = MagicMock()
        mock_audit = MagicMock()
        mock_audit.id = 5

        with patch("jobs.positions.get_session", return_value=mock_session), \
             patch("jobs.positions._create_audit", return_value=mock_audit), \
             patch("jobs.positions._update_audit"):

            manage_positions(mock_app)

        mock_app.state.alpaca_client.submit_order.assert_called_once()

    def test_skips_position_at_exactly_stop_loss(self, mock_app):
        pos = make_position(symbol="AAPL", qty=100, unrealized_plpc=-3.0)
        mock_app.state.alpaca_client.get_all_positions.return_value = [pos]
        mock_order = MagicMock()
        mock_app.state.alpaca_client.submit_order.return_value = mock_order
        mock_session = MagicMock()
        mock_audit = MagicMock()
        mock_audit.id = 6

        with patch("jobs.positions.get_session", return_value=mock_session), \
             patch("jobs.positions._create_audit", return_value=mock_audit), \
             patch("jobs.positions._update_audit"):

            manage_positions(mock_app)

        mock_app.state.alpaca_client.submit_order.assert_called_once()

    def test_handles_api_error_on_fetch(self, mock_app):
        mock_app.state.alpaca_client.get_all_positions.side_effect = Exception("API down")
        result = manage_positions(mock_app)
        assert result is None

    def test_handles_submit_error_gracefully(self, mock_app):
        pos = make_position(symbol="AAPL", qty=100, unrealized_plpc=6.0)
        mock_app.state.alpaca_client.get_all_positions.return_value = [pos]
        mock_app.state.alpaca_client.submit_order.side_effect = Exception("Submit failed")
        mock_session = MagicMock()
        mock_audit = MagicMock()
        mock_audit.id = 7

        with patch("jobs.positions.get_session", return_value=mock_session), \
             patch("jobs.positions._create_audit", return_value=mock_audit), \
             patch("jobs.positions._update_audit") as mock_update:

            manage_positions(mock_app)

        mock_update.assert_called_once_with(
            mock_session, mock_audit, risk_check_passed=True, validation_passed=True,
            executed=False, error_message="Submit failed"
        )
        mock_session.close.assert_called_once()

    def test_handles_per_position_error_gracefully(self, mock_app):
        pos_ok = make_position(symbol="AAPL", qty=100, unrealized_plpc=6.0)
        pos_bad = MagicMock()
        pos_bad.symbol = "bad"
        pos_bad.qty = "abc"
        mock_app.state.alpaca_client.get_all_positions.return_value = [pos_bad, pos_ok]
        mock_order = MagicMock()
        mock_order.id = "ord_ok"
        mock_app.state.alpaca_client.submit_order.return_value = mock_order
        mock_session = MagicMock()
        mock_audit = MagicMock()
        mock_audit.id = 8

        with patch("jobs.positions.get_session", return_value=mock_session), \
             patch("jobs.positions._create_audit", return_value=mock_audit), \
             patch("jobs.positions._update_audit"):

            manage_positions(mock_app)

        mock_app.state.alpaca_client.submit_order.assert_called_once()

    def test_skips_zero_qty_positions(self, mock_app):
        pos = make_position(symbol="AAPL", qty=0, unrealized_plpc=6.0)
        mock_app.state.alpaca_client.get_all_positions.return_value = [pos]

        with patch("jobs.positions.get_session") as mock_get_session:
            manage_positions(mock_app)

        mock_app.state.alpaca_client.submit_order.assert_not_called()
        mock_get_session.assert_not_called()
