import pytest
from unittest.mock import MagicMock, patch
from broker.alpaca import create_client, execute_signal
from broker.risk import check_can_trade, validate_order


@pytest.fixture
def mock_client():
    client = MagicMock()
    account = MagicMock()
    account.equity = "10000"
    account.buying_power = "5000"
    client.get_account.return_value = account

    clock = MagicMock()
    clock.is_open = True
    client.get_clock.return_value = clock

    trade = MagicMock()
    trade.price = 50
    client.get_latest_trade.return_value = trade

    client.get_all_positions.return_value = []
    with patch("broker.alpaca.check_can_trade", return_value=(True, "")):
        yield client


class TestCreateClient:
    @patch("broker.alpaca.TradingClient")
    def test_creates_trading_client(self, mock_trading_client):
        mock_trading_client.return_value = "client_instance"
        result = create_client()
        mock_trading_client.assert_called_once()
        assert result == "client_instance"


class TestExecuteSignal:
    def test_returns_hold_signal(self, mock_client):
        result = execute_signal(mock_client, "AAPL", "hold", 0.7)
        assert result == {"executed": False, "reason": "hold signal"}

    def test_rejected_by_risk_check(self, mock_client):
        with patch("broker.alpaca.check_can_trade", return_value=(False, "risk fail")):
            result = execute_signal(mock_client, "AAPL", "buy", 0.7)
            assert result == {"executed": False, "reason": "risk fail"}

    def test_submits_market_order(self, mock_client):
        mock_order = MagicMock()
        mock_order.id = "order_123"
        mock_client.submit_order.return_value = mock_order

        result = execute_signal(mock_client, "AAPL", "buy", 0.7, max_shares=10)

        assert result["executed"] is True
        assert result["order_id"] == "order_123"
        assert result["qty"] == 7
        mock_client.submit_order.assert_called_once()

    def test_submits_sell_order(self, mock_client):
        mock_order = MagicMock()
        mock_order.id = "order_456"
        mock_client.submit_order.return_value = mock_order

        result = execute_signal(mock_client, "AAPL", "sell", 0.8, max_shares=10)

        assert result["executed"] is True
        assert result["qty"] == 8
        assert result["side"] == "sell"

    def test_qty_capped_at_max_shares(self, mock_client):
        mock_order = MagicMock()
        mock_order.id = "order_789"
        mock_client.submit_order.return_value = mock_order

        result = execute_signal(mock_client, "AAPL", "buy", 1.0, max_shares=5)

        assert result["qty"] == 5

    def test_qty_minimum_one(self, mock_client):
        mock_order = MagicMock()
        mock_order.id = "order_999"
        mock_client.submit_order.return_value = mock_order

        result = execute_signal(mock_client, "AAPL", "buy", 0.1, max_shares=10)

        assert result["qty"] == 1

    def test_returns_audit_id_when_session_provided(self, mock_client):
        from broker.alpaca import _create_audit
        mock_session = MagicMock()
        mock_audit = MagicMock()
        mock_audit.id = 42
        with patch("broker.alpaca._create_audit", return_value=mock_audit):
            result = execute_signal(
                mock_client, "AAPL", "hold", 0.7, session=mock_session, source="test"
            )
        assert result["audit_id"] == 42

    def test_creates_audit_on_successful_order(self, mock_client):
        mock_session = MagicMock()
        mock_audit = MagicMock()
        mock_audit.id = 99
        mock_order = MagicMock()
        mock_order.id = "order_audit_1"
        mock_order.status = "filled"
        mock_client.submit_order.return_value = mock_order
        with patch("broker.alpaca._create_audit", return_value=mock_audit), \
             patch("broker.alpaca._update_audit") as mock_update:
            result = execute_signal(
                mock_client, "AAPL", "buy", 0.7, max_shares=10,
                session=mock_session, source="test"
            )
        assert result["executed"] is True
        assert result["audit_id"] == 99
        mock_update.assert_called_once_with(
            mock_session, mock_audit, risk_check_passed=True, validation_passed=True,
            executed=True, order_id="order_audit_1", order_side="buy", order_qty=7,
            order_status="filled"
        )

    def test_creates_audit_on_risk_rejection(self, mock_client):
        mock_session = MagicMock()
        mock_audit = MagicMock()
        mock_audit.id = 88
        with patch("broker.alpaca._create_audit", return_value=mock_audit), \
             patch("broker.alpaca.check_can_trade", return_value=(False, "risk fail")), \
             patch("broker.alpaca._update_audit") as mock_update:
            result = execute_signal(
                mock_client, "AAPL", "buy", 0.7, session=mock_session, source="test"
            )
        assert result["executed"] is False
        assert result["reason"] == "risk fail"
        assert result["audit_id"] == 88
        mock_update.assert_called_once_with(
            mock_session, mock_audit, risk_check_passed=False,
            risk_check_reason="risk fail", executed=False
        )

    def test_creates_audit_on_order_error(self, mock_client):
        mock_session = MagicMock()
        mock_audit = MagicMock()
        mock_audit.id = 77
        mock_client.submit_order.side_effect = Exception("Connection failed")
        with patch("broker.alpaca._create_audit", return_value=mock_audit), \
             patch("broker.alpaca._update_audit") as mock_update:
            with pytest.raises(Exception, match="Connection failed"):
                execute_signal(
                    mock_client, "AAPL", "buy", 0.7, session=mock_session, source="test"
                )
        mock_update.assert_called_once_with(
            mock_session, mock_audit, risk_check_passed=True, validation_passed=True,
            executed=False, error_message="Connection failed"
        )


class TestCheckCanTrade:
    def test_allows_trade_when_no_position(self, mock_client):
        mock_client.get_all_positions.return_value = []
        can_trade, reason = check_can_trade(mock_client, "AAPL", "buy")
        assert can_trade is True

    def test_rejects_buy_when_already_long(self, mock_client):
        account = MagicMock()
        account.equity = "10000"
        mock_client.get_account.return_value = account
        pos = MagicMock()
        pos.symbol = "AAPL"
        pos.qty = "10"
        pos.market_value = "5000"
        mock_client.get_all_positions.return_value = [pos]

        can_trade, reason = check_can_trade(mock_client, "AAPL", "buy")
        assert can_trade is False
        assert "long" in reason

    def test_rejects_sell_when_already_short(self, mock_client):
        account = MagicMock()
        account.equity = "10000"
        mock_client.get_account.return_value = account
        pos = MagicMock()
        pos.symbol = "AAPL"
        pos.qty = "-10"
        pos.market_value = "5000"
        mock_client.get_all_positions.return_value = [pos]

        can_trade, reason = check_can_trade(mock_client, "AAPL", "sell")
        assert can_trade is False
        assert "short" in reason

    def test_allows_buy_when_short_or_no_position(self, mock_client):
        account = MagicMock()
        account.equity = "100000"
        mock_client.get_account.return_value = account
        pos = MagicMock()
        pos.symbol = "AAPL"
        pos.qty = "-10"
        pos.market_value = "5000"
        mock_client.get_all_positions.return_value = [pos]

        can_trade, reason = check_can_trade(mock_client, "AAPL", "buy")
        assert can_trade is True

    def test_rejects_when_position_exceeds_max_pct(self, mock_client):
        account = MagicMock()
        account.equity = "10000"
        mock_client.get_account.return_value = account
        pos = MagicMock()
        pos.symbol = "AAPL"
        pos.qty = "10"
        pos.market_value = "9000"
        mock_client.get_all_positions.return_value = [pos]

        can_trade, reason = check_can_trade(mock_client, "AAPL", "sell", max_position_pct=0.3)
        assert can_trade is False
        assert "exceeds max" in reason

    def test_ignores_other_symbols(self, mock_client):
        account = MagicMock()
        account.equity = "100000"
        mock_client.get_account.return_value = account
        pos = MagicMock()
        pos.symbol = "MSFT"
        pos.qty = "10"
        pos.market_value = "5000"
        mock_client.get_all_positions.return_value = [pos]

        can_trade, reason = check_can_trade(mock_client, "AAPL", "buy")
        assert can_trade is True

    def test_handles_api_error_gracefully(self, mock_client):
        mock_client.get_account.side_effect = Exception("API down")
        can_trade, reason = check_can_trade(mock_client, "AAPL", "buy")
        assert can_trade is False
        assert "API down" in reason


class TestValidateOrder:
    def test_rejects_when_market_closed(self, mock_client):
        clock = MagicMock()
        clock.is_open = False
        mock_client.get_clock.return_value = clock

        result = validate_order(mock_client, "AAPL", "buy", 10)
        assert result["valid"] is False
        assert "closed" in result["reason"]

    def test_rejects_insufficient_buying_power(self, mock_client):
        clock = MagicMock()
        clock.is_open = True
        mock_client.get_clock.return_value = clock

        account = MagicMock()
        account.buying_power = "100"
        mock_client.get_account.return_value = account

        trade = MagicMock()
        trade.price = 20
        mock_client.get_latest_trade.return_value = trade

        result = validate_order(mock_client, "AAPL", "buy", 10)
        assert result["valid"] is False
        assert "buying power" in result["reason"]

    def test_validates_successfully(self, mock_client):
        clock = MagicMock()
        clock.is_open = True
        mock_client.get_clock.return_value = clock

        account = MagicMock()
        account.buying_power = "1000"
        mock_client.get_account.return_value = account

        trade = MagicMock()
        trade.price = 20
        mock_client.get_latest_trade.return_value = trade

        result = validate_order(mock_client, "AAPL", "buy", 10)
        assert result["valid"] is True

    def test_handles_api_error_gracefully(self, mock_client):
        mock_client.get_account.side_effect = Exception("API down")
        result = validate_order(mock_client, "AAPL", "buy", 10)
        assert result["valid"] is False
        assert "API down" in result["reason"]
